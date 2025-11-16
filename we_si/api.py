"""
Flask API for WeSi website analysis.
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
import os
import io

from we_si.models import (
    init_db, User, Subscription, SiteAnalysis, PageAnalysis,
    APIKey, JobStatus, SubscriptionTier
)
from we_si.storage.secrets import SecretManager, store_api_key, get_api_key, delete_api_key, list_api_key_services
from we_si.tasks import analyze_website_task, generate_report_task, celery_app
from we_si.ai.assistant import AIAssistant, store_conversation, load_conversation
from we_si.reports.html_report import HTMLReportGenerator
from we_si.reports.text_report import TextReportGenerator

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///wesi.db')

# Initialize database
engine, Session = init_db(DATABASE_URL)

# Initialize secret manager
try:
    secret_manager = SecretManager()
except ValueError as e:
    print(f"Warning: Secret manager not initialized: {e}")
    secret_manager = None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """
    Start a new website analysis job.
    
    Request JSON:
        {
            "user_id": 1,
            "base_url": "https://example.com",
            "max_pages": 50,  // optional, defaults to subscription limit
            "max_depth": 3    // optional, defaults to subscription limit
        }
    
    Returns:
        {
            "job_id": "task-id",
            "site_analysis_id": 123,
            "status": "pending"
        }
    """
    data = request.get_json()
    
    if not data or 'user_id' not in data or 'base_url' not in data:
        return jsonify({'error': 'user_id and base_url are required'}), 400
    
    user_id = data['user_id']
    base_url = data['base_url'].strip()
    
    session = Session()
    try:
        # Get user and subscription
        user = session.query(User).get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        subscription = user.subscription
        if not subscription:
            # Create default free subscription
            subscription = Subscription(
                user_id=user_id,
                tier=SubscriptionTier.FREE,
                **Subscription.get_tier_limits(SubscriptionTier.FREE)
            )
            session.add(subscription)
            session.commit()
        
        # Get limits
        limits = Subscription.get_tier_limits(subscription.tier)
        max_pages = data.get('max_pages', limits['max_pages_per_run'])
        max_depth = data.get('max_depth', limits['max_depth'])
        
        # Enforce subscription limits
        max_pages = min(max_pages, limits['max_pages_per_run'])
        max_depth = min(max_depth, limits['max_depth'])
        
        # Check monthly analysis limit
        # Count analyses this month
        from sqlalchemy import func, extract
        current_month = datetime.utcnow().month
        current_year = datetime.utcnow().year
        
        analyses_this_month = session.query(func.count(SiteAnalysis.id)).filter(
            SiteAnalysis.user_id == user_id,
            extract('month', SiteAnalysis.created_at) == current_month,
            extract('year', SiteAnalysis.created_at) == current_year
        ).scalar()
        
        if analyses_this_month >= limits['max_analyses_per_month']:
            return jsonify({
                'error': f'Monthly analysis limit reached ({limits["max_analyses_per_month"]} analyses per month)',
                'upgrade_required': True
            }), 429
        
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        domain = parsed.netloc
        
        # Create site analysis record
        site_analysis = SiteAnalysis(
            user_id=user_id,
            base_url=base_url,
            domain=domain,
            status=JobStatus.PENDING,
            progress=0.0
        )
        session.add(site_analysis)
        session.commit()
        
        # Start async task
        task = analyze_website_task.apply_async(
            args=[site_analysis.id, base_url, user_id, max_pages, max_depth]
        )
        
        return jsonify({
            'job_id': task.id,
            'site_analysis_id': site_analysis.id,
            'status': 'pending',
            'limits': {
                'max_pages': max_pages,
                'max_depth': max_depth
            }
        }), 202
    
    finally:
        session.close()


@app.route('/api/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Get the status of an analysis job.
    
    Returns:
        {
            "job_id": "task-id",
            "status": "pending|running|completed|failed",
            "progress": 45.5,
            "current_step": "Analyzing page 23/50",
            "result": {...}  // only when completed
        }
    """
    task = celery_app.AsyncResult(job_id)
    
    response = {
        'job_id': job_id,
        'status': task.state.lower()
    }
    
    if task.state == 'PENDING':
        response['progress'] = 0
        response['current_step'] = 'Queued'
    elif task.state == 'PROGRESS':
        meta = task.info
        response['progress'] = meta.get('progress', 0)
        response['current_step'] = meta.get('status', 'Processing...')
        if 'current_url' in meta:
            response['current_url'] = meta['current_url']
    elif task.state == 'SUCCESS':
        response['progress'] = 100
        response['current_step'] = 'Completed'
        response['result'] = task.result
    elif task.state == 'FAILURE':
        response['progress'] = 0
        response['current_step'] = 'Failed'
        response['error'] = str(task.info)
    
    return jsonify(response)


@app.route('/api/analysis/<int:site_analysis_id>', methods=['GET'])
def get_analysis(site_analysis_id):
    """
    Get analysis results.
    
    Returns:
        Full analysis data including metadata, summary, insights, and pages
    """
    session = Session()
    try:
        site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if not site_analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Get pages
        pages = session.query(PageAnalysis).filter_by(
            site_analysis_id=site_analysis_id
        ).all()
        
        return jsonify({
            'id': site_analysis.id,
            'base_url': site_analysis.base_url,
            'domain': site_analysis.domain,
            'status': site_analysis.status.value,
            'progress': site_analysis.progress,
            'pages_crawled': site_analysis.pages_crawled,
            'pages_analyzed': site_analysis.pages_analyzed,
            'created_at': site_analysis.created_at.isoformat() if site_analysis.created_at else None,
            'completed_at': site_analysis.completed_at.isoformat() if site_analysis.completed_at else None,
            'summary': site_analysis.summary,
            'insights': site_analysis.insights,
            'pages': [
                {
                    'id': page.id,
                    'url': page.url,
                    'status_code': page.status_code,
                    'depth': page.depth,
                    'load_time': page.load_time,
                    'analysis_data': page.analysis_data
                }
                for page in pages
            ]
        })
    
    finally:
        session.close()


@app.route('/api/analysis/<int:site_analysis_id>/report/<report_type>', methods=['GET'])
def get_report(site_analysis_id, report_type):
    """
    Generate and download a report.
    
    Args:
        site_analysis_id: Site analysis ID
        report_type: 'html', 'text', or 'json'
    """
    session = Session()
    try:
        site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if not site_analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        if site_analysis.status != JobStatus.COMPLETED:
            return jsonify({'error': 'Analysis not completed yet'}), 400
        
        # Get pages
        pages = session.query(PageAnalysis).filter_by(
            site_analysis_id=site_analysis_id
        ).all()
        
        # Build analysis data
        analysis_data = {
            'metadata': {
                'base_url': site_analysis.base_url,
                'domain': site_analysis.domain,
                'analysis_date': site_analysis.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'pages_crawled': site_analysis.pages_crawled
            },
            'summary': site_analysis.summary or {},
            'insights': site_analysis.insights or {},
            'pages': [page.analysis_data for page in pages if page.analysis_data]
        }
        
        # Generate report
        if report_type == 'html':
            generator = HTMLReportGenerator()
            content = generator.generate(analysis_data)
            return send_file(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/html',
                as_attachment=True,
                download_name=f'{site_analysis.domain}_report.html'
            )
        elif report_type == 'text':
            generator = TextReportGenerator()
            content = generator.generate(analysis_data)
            return send_file(
                io.BytesIO(content.encode('utf-8')),
                mimetype='text/plain',
                as_attachment=True,
                download_name=f'{site_analysis.domain}_report.txt'
            )
        elif report_type == 'json':
            return jsonify(analysis_data)
        else:
            return jsonify({'error': f'Unknown report type: {report_type}'}), 400
    
    finally:
        session.close()


@app.route('/api/user/<int:user_id>/analyses', methods=['GET'])
def list_user_analyses(user_id):
    """List all analyses for a user."""
    session = Session()
    try:
        analyses = session.query(SiteAnalysis).filter_by(user_id=user_id).order_by(
            SiteAnalysis.created_at.desc()
        ).all()
        
        return jsonify({
            'analyses': [
                {
                    'id': a.id,
                    'domain': a.domain,
                    'base_url': a.base_url,
                    'status': a.status.value,
                    'progress': a.progress,
                    'pages_analyzed': a.pages_analyzed,
                    'created_at': a.created_at.isoformat() if a.created_at else None,
                    'completed_at': a.completed_at.isoformat() if a.completed_at else None
                }
                for a in analyses
            ]
        })
    
    finally:
        session.close()


@app.route('/api/user/<int:user_id>/api-keys', methods=['GET'])
def list_user_api_keys(user_id):
    """List services with stored API keys (keys not returned)."""
    if not secret_manager:
        return jsonify({'error': 'Secret manager not configured'}), 500
    
    session = Session()
    try:
        services = list_api_key_services(session, user_id)
        return jsonify({'services': services})
    finally:
        session.close()


@app.route('/api/user/<int:user_id>/api-keys', methods=['POST'])
def add_user_api_key(user_id):
    """
    Add or update an API key for a user.
    
    Request JSON:
        {
            "service": "openai",
            "api_key": "sk-..."
        }
    """
    if not secret_manager:
        return jsonify({'error': 'Secret manager not configured'}), 500
    
    data = request.get_json()
    if not data or 'service' not in data or 'api_key' not in data:
        return jsonify({'error': 'service and api_key are required'}), 400
    
    service = data['service']
    api_key = data['api_key']
    
    session = Session()
    try:
        store_api_key(session, user_id, service, api_key, secret_manager)
        return jsonify({'message': f'API key for {service} stored successfully'}), 201
    finally:
        session.close()


@app.route('/api/user/<int:user_id>/api-keys/<service>', methods=['DELETE'])
def delete_user_api_key(user_id, service):
    """Delete an API key for a user."""
    if not secret_manager:
        return jsonify({'error': 'Secret manager not configured'}), 500
    
    session = Session()
    try:
        deleted = delete_api_key(session, user_id, service)
        if deleted:
            return jsonify({'message': f'API key for {service} deleted'}), 200
        else:
            return jsonify({'error': 'API key not found'}), 404
    finally:
        session.close()


@app.route('/api/analysis/<int:site_analysis_id>/assistant/chat', methods=['POST'])
def chat_with_assistant(site_analysis_id):
    """
    Chat with AI assistant about site analysis.
    
    Request JSON:
        {
            "user_id": 1,
            "message": "How can I improve my SEO?",
            "conversation_id": 123  // optional, for continuing conversation
        }
    """
    data = request.get_json()
    if not data or 'user_id' not in data or 'message' not in data:
        return jsonify({'error': 'user_id and message are required'}), 400
    
    user_id = data['user_id']
    message = data['message']
    conversation_id = data.get('conversation_id')
    
    session = Session()
    try:
        # Get site analysis
        site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if not site_analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        if site_analysis.user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if site_analysis.status != JobStatus.COMPLETED:
            return jsonify({'error': 'Analysis not completed yet'}), 400
        
        # Check if user has subscription that includes AI
        subscription = session.query(Subscription).filter_by(user_id=user_id).first()
        if not subscription:
            return jsonify({'error': 'No subscription found'}), 403
        
        limits = Subscription.get_tier_limits(subscription.tier)
        if not limits.get('include_ai_assistant'):
            return jsonify({'error': 'AI assistant not available for your subscription tier'}), 403
        
        # Get API key
        api_key = get_api_key(session, user_id, 'openai', secret_manager)
        if not api_key:
            # Use server key if available
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                return jsonify({'error': 'No OpenAI API key configured'}), 400
        
        # Load conversation history
        from we_si.ai.assistant import load_conversation
        conversation_history = []
        if conversation_id:
            conversation_history = load_conversation(session, conversation_id)
        
        # Get pages for context
        pages = session.query(PageAnalysis).filter_by(
            site_analysis_id=site_analysis_id
        ).all()
        
        # Build analysis data for context
        analysis_data = {
            'metadata': {
                'base_url': site_analysis.base_url,
                'domain': site_analysis.domain,
                'analysis_date': site_analysis.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'pages_crawled': site_analysis.pages_crawled
            },
            'summary': site_analysis.summary or {},
            'insights': site_analysis.insights or {},
            'pages': [page.analysis_data for page in pages if page.analysis_data]
        }
        
        # Initialize assistant and chat
        assistant = AIAssistant(api_key)
        result = assistant.chat(message, conversation_history, analysis_data)
        
        # Store conversation
        from we_si.ai.assistant import store_conversation
        new_conv_id = store_conversation(
            session,
            site_analysis_id,
            result['conversation_history']
        )
        
        return jsonify({
            'response': result['response'],
            'conversation_id': new_conv_id,
            'usage': result.get('usage', {})
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        session.close()


@app.route('/api/user/<int:user_id>/subscription', methods=['GET'])
def get_user_subscription(user_id):
    """Get user's subscription details."""
    session = Session()
    try:
        subscription = session.query(Subscription).filter_by(user_id=user_id).first()
        if not subscription:
            return jsonify({'error': 'No subscription found'}), 404
        
        limits = Subscription.get_tier_limits(subscription.tier)
        
        return jsonify({
            'tier': subscription.tier.value,
            'limits': limits,
            'created_at': subscription.created_at.isoformat() if subscription.created_at else None
        })
    
    finally:
        session.close()


if __name__ == '__main__':
    # Use debug mode only in development, controlled by environment variable
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

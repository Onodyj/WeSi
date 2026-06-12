#!/usr/bin/env python3
"""
Example usage of WeSi 2.0 API and features.
This demonstrates the new asynchronous analysis and AI assistant capabilities.
"""
import time
import requests
from we_si.models import init_db, User, Subscription, SubscriptionTier
from we_si.storage.secrets import SecretManager, store_api_key


def setup_demo_user():
    """Create a demo user with subscription."""
    engine, Session = init_db()
    session = Session()
    
    try:
        # Check if demo user exists
        user = session.query(User).filter_by(email='demo@example.com').first()
        
        if not user:
            # Create demo user
            import hashlib
            password_hash = hashlib.sha256('demo123'.encode()).hexdigest()
            
            user = User(
                email='demo@example.com',
                username='demo',
                password_hash=password_hash
            )
            session.add(user)
            session.flush()
            
            # Get tier limits
            limits = Subscription.get_tier_limits(SubscriptionTier.STANDARD)
            
            # Create subscription - only use database columns
            subscription = Subscription(
                user_id=user.id,
                tier=SubscriptionTier.STANDARD,
                max_pages_per_run=limits['max_pages_per_run'],
                max_pages_stored=limits['max_pages_stored'],
                max_analyses_per_month=limits['max_analyses_per_month']
            )
            session.add(subscription)
            session.commit()
            
            print(f"✅ Created demo user with ID: {user.id}")
        else:
            print(f"✅ Demo user already exists with ID: {user.id}")
        
        return user.id
    
    finally:
        session.close()


def example_1_basic_analysis():
    """Example 1: Basic website analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Website Analysis")
    print("="*70)
    
    user_id = setup_demo_user()
    
    # Start analysis
    print("\n1. Starting analysis...")
    response = requests.post('http://localhost:5000/api/analyze', json={
        'user_id': user_id,
        'base_url': 'https://example.com',
        'max_pages': 5
    })
    
    if response.status_code == 202:
        data = response.json()
        job_id = data['job_id']
        site_analysis_id = data['site_analysis_id']
        
        print(f"✅ Analysis started")
        print(f"   Job ID: {job_id}")
        print(f"   Site Analysis ID: {site_analysis_id}")
        
        # Poll for status
        print("\n2. Monitoring progress...")
        while True:
            status_response = requests.get(f'http://localhost:5000/api/status/{job_id}')
            status_data = status_response.json()
            
            status = status_data['status']
            progress = status_data.get('progress', 0)
            current_step = status_data.get('current_step', 'Unknown')
            
            print(f"   Status: {status} | Progress: {progress:.1f}% | {current_step}")
            
            if status in ['success', 'failure']:
                break
            
            time.sleep(2)
        
        if status == 'success':
            print("\n✅ Analysis completed!")
            
            # Get results
            print("\n3. Fetching results...")
            results_response = requests.get(f'http://localhost:5000/api/analysis/{site_analysis_id}')
            results = results_response.json()
            
            print(f"\nResults Summary:")
            print(f"   Pages Analyzed: {results['pages_analyzed']}")
            print(f"   Domain: {results['domain']}")
            
            # Download HTML report
            print("\n4. Downloading HTML report...")
            report_response = requests.get(
                f'http://localhost:5000/api/analysis/{site_analysis_id}/report/html'
            )
            
            if report_response.status_code == 200:
                with open(f'/tmp/report_{site_analysis_id}.html', 'wb') as f:
                    f.write(report_response.content)
                print(f"✅ Report saved to /tmp/report_{site_analysis_id}.html")
    else:
        print(f"❌ Failed to start analysis: {response.status_code}")
        print(response.json())


def example_2_ai_assistant():
    """Example 2: Using AI Assistant."""
    print("\n" + "="*70)
    print("EXAMPLE 2: AI Assistant Integration")
    print("="*70)
    
    user_id = setup_demo_user()
    
    # Note: This requires a completed analysis
    # For demo purposes, use a site_analysis_id from a previous run
    site_analysis_id = 1  # Replace with actual ID
    
    print("\n1. Chatting with AI Assistant...")
    print("   (Requires OpenAI API key to be configured)")
    
    # Example chat
    try:
        response = requests.post(
            f'http://localhost:5000/api/analysis/{site_analysis_id}/assistant/chat',
            json={
                'user_id': user_id,
                'message': 'What are the top 3 things I should fix first?'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n   Assistant Response:")
            print(f"   {data['response']}")
            print(f"\n   Conversation ID: {data['conversation_id']}")
        else:
            print(f"   ⚠️ Assistant not available: {response.json().get('error')}")
    except requests.exceptions.ConnectionError:
        print("   ⚠️ API server not running. Start with: python we_si/api.py")


def example_3_api_key_management():
    """Example 3: Managing API keys."""
    print("\n" + "="*70)
    print("EXAMPLE 3: API Key Management")
    print("="*70)
    
    user_id = setup_demo_user()
    
    print("\n1. Adding OpenAI API key...")
    try:
        response = requests.post(
            f'http://localhost:5000/api/user/{user_id}/api-keys',
            json={
                'service': 'openai',
                'api_key': 'sk-demo-key-not-real'
            }
        )
        
        if response.status_code in [200, 201]:
            print("✅ API key stored securely (encrypted)")
        else:
            print(f"⚠️ {response.json().get('error')}")
    except requests.exceptions.ConnectionError:
        print("⚠️ API server not running")
    
    print("\n2. Listing stored API keys...")
    try:
        response = requests.get(f'http://localhost:5000/api/user/{user_id}/api-keys')
        
        if response.status_code == 200:
            services = response.json()['services']
            print(f"✅ Services with keys stored: {services}")
        else:
            print(f"⚠️ {response.json().get('error')}")
    except requests.exceptions.ConnectionError:
        print("⚠️ API server not running")


def example_4_standalone_modules():
    """Example 4: Using modules standalone (without API)."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Using Modules Standalone")
    print("="*70)
    
    print("\n1. Using Crawler directly...")
    from we_si.crawler import WebsiteCrawler
    
    # This would actually crawl - commented out for demo
    # crawler = WebsiteCrawler('https://example.com', max_pages=3)
    # pages = crawler.crawl()
    print("   ✅ Crawler can be used independently")
    
    print("\n2. Using Analyzer directly...")
    from we_si.analyzer import PageAnalyzer
    
    analyzer = PageAnalyzer()
    
    sample_html = '''
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
    </head>
    <body>
        <h1>Hello World</h1>
        <p>This is a test page.</p>
    </body>
    </html>
    '''
    
    analysis = analyzer.analyze_page('https://example.com', sample_html)
    print(f"   ✅ Analyzed page")
    print(f"      Title: {analysis['seo']['title']}")
    print(f"      Word Count: {analysis['seo']['word_count']}")
    print(f"      H1 Count: {analysis['headings']['h1_count']}")
    
    print("\n3. Generating reports directly...")
    from we_si.reports.html_report import HTMLReportGenerator
    from we_si.reports.text_report import TextReportGenerator
    
    test_data = {
        'metadata': {
            'base_url': 'https://example.com',
            'domain': 'example.com',
            'analysis_date': '2024-01-01',
            'pages_crawled': 3
        },
        'summary': {
            'total_pages_analyzed': 3,
            'total_images': 5,
            'images_without_alt': 1,
            'total_internal_links': 10,
            'total_external_links': 2,
            'broken_links_found': 0,
            'avg_word_count': 350
        },
        'insights': {
            'critical': [],
            'warnings': ['1 image without alt text'],
            'recommendations': ['Add more external links'],
            'positive': ['Good content depth']
        },
        'pages': [analysis]
    }
    
    html_gen = HTMLReportGenerator()
    html_report = html_gen.generate(test_data)
    
    text_gen = TextReportGenerator()
    text_report = text_gen.generate(test_data)
    
    print(f"   ✅ Generated HTML report ({len(html_report)} bytes)")
    print(f"   ✅ Generated text report ({len(text_report)} bytes)")


def example_5_encryption():
    """Example 5: Encryption utilities."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Secure Key Storage")
    print("="*70)
    
    from we_si.storage.secrets import SecretManager
    
    print("\n1. Generating encryption key...")
    key = SecretManager.generate_key()
    print(f"   ✅ Generated key: {key[:20]}...")
    
    print("\n2. Encrypting data...")
    manager = SecretManager(key)
    
    secret = "sk-super-secret-api-key-12345"
    encrypted = manager.encrypt(secret)
    print(f"   ✅ Encrypted: {encrypted[:40]}...")
    
    print("\n3. Decrypting data...")
    decrypted = manager.decrypt(encrypted)
    print(f"   ✅ Decrypted: {decrypted[:20]}...")
    print(f"   ✅ Match: {secret == decrypted}")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("WeSi 2.0 - Feature Demonstration")
    print("="*70)
    print("\nThis script demonstrates the new features in WeSi 2.0")
    print("Some examples require the API server and Celery to be running.")
    print("\nTo start the full stack:")
    print("  1. Start Redis: redis-server")
    print("  2. Start Celery: celery -A we_si.tasks worker --loglevel=info")
    print("  3. Start API: python we_si/api.py")
    
    # Run standalone examples that don't need API
    example_4_standalone_modules()
    example_5_encryption()
    
    # API-based examples (will show warnings if API not running)
    example_3_api_key_management()
    
    # These would run actual analysis - commented out for demo
    # example_1_basic_analysis()
    # example_2_ai_assistant()
    
    print("\n" + "="*70)
    print("Demo Complete!")
    print("="*70)


if __name__ == '__main__':
    main()

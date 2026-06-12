"""
Celery tasks for asynchronous site analysis processing.
"""
from celery import Celery
from datetime import datetime
import time
from typing import Dict, Any

# Initialize Celery
celery_app = Celery(
    'wesi',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@celery_app.task(bind=True)
def analyze_website_task(self, site_analysis_id: int, base_url: str, user_id: int, max_pages: int = 50, max_depth: int = 3):
    """
    Asynchronous task to crawl and analyze a website.
    
    Args:
        self: Celery task instance (for progress updates)
        site_analysis_id: Database ID of SiteAnalysis record
        base_url: Website URL to analyze
        user_id: User ID
        max_pages: Maximum pages to crawl
        max_depth: Maximum crawl depth
        
    Returns:
        Dictionary with analysis results
    """
    from we_si.models import init_db, SiteAnalysis, PageAnalysis, JobStatus
    from we_si.crawler import WebsiteCrawler
    from we_si.analyzer import PageAnalyzer
    from urllib.parse import urlparse
    
    # Initialize database
    engine, Session = init_db()
    session = Session()
    
    try:
        # Get site analysis record
        site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if not site_analysis:
            raise ValueError(f"SiteAnalysis {site_analysis_id} not found")
        
        # Update status to running
        site_analysis.status = JobStatus.RUNNING
        site_analysis.started_at = datetime.utcnow()
        session.commit()
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting crawler...'})
        
        # Initialize crawler
        crawler = WebsiteCrawler(
            base_url=base_url,
            max_pages=max_pages,
            max_depth=max_depth,
            rate_limit=0.5
        )
        
        # Crawl website with progress callback
        def progress_callback(current, total, url):
            progress = (current / total) * 50  # First 50% for crawling
            site_analysis.progress = progress
            site_analysis.pages_crawled = current
            session.commit()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': progress,
                    'status': f'Crawling page {current}/{total}',
                    'current_url': url
                }
            )
        
        crawled_pages = crawler.crawl(progress_callback=progress_callback)
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Analyzing pages...'})
        
        # Initialize analyzer
        analyzer = PageAnalyzer()
        
        # Analyze each page
        analyzed_pages = []
        total_pages = len(crawled_pages)
        
        for idx, page_data in enumerate(crawled_pages, 1):
            url = page_data['url']
            content = page_data.get('content', '')
            status_code = page_data.get('status_code', 0)
            depth = page_data.get('depth', 0)
            
            if content:
                # Analyze page
                start_time = time.time()
                analysis = analyzer.analyze_page(url, content, start_time)
                analysis['status_code'] = status_code
                analysis['depth'] = depth
                
                # Store in database
                page_analysis = PageAnalysis(
                    site_analysis_id=site_analysis_id,
                    url=url,
                    status_code=status_code,
                    depth=depth,
                    load_time=analysis.get('load_time', 0),
                    analysis_data=analysis
                )
                session.add(page_analysis)
                
                analyzed_pages.append(analysis)
            else:
                # Store failed page
                page_analysis = PageAnalysis(
                    site_analysis_id=site_analysis_id,
                    url=url,
                    status_code=status_code,
                    depth=depth,
                    analysis_data={'error': page_data.get('error', 'Failed to fetch')}
                )
                session.add(page_analysis)
            
            # Update progress
            progress = 50 + (idx / total_pages) * 45  # 50-95% for analysis
            site_analysis.progress = progress
            site_analysis.pages_analyzed = idx
            session.commit()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': progress,
                    'status': f'Analyzing page {idx}/{total_pages}',
                    'current_url': url
                }
            )
        
        # Generate insights
        self.update_state(state='PROGRESS', meta={'progress': 95, 'status': 'Generating insights...'})
        
        insights = generate_insights(analyzed_pages)
        summary = generate_summary(analyzed_pages)
        
        # Update site analysis with results
        site_analysis.status = JobStatus.COMPLETED
        site_analysis.completed_at = datetime.utcnow()
        site_analysis.progress = 100
        site_analysis.summary = summary
        site_analysis.insights = insights
        session.commit()
        
        result = {
            'status': 'completed',
            'site_analysis_id': site_analysis_id,
            'summary': summary,
            'insights': insights,
            'pages_analyzed': len(analyzed_pages)
        }
        
        return result
        
    except Exception as e:
        # Mark as failed
        site_analysis.status = JobStatus.FAILED
        site_analysis.error_message = str(e)
        site_analysis.completed_at = datetime.utcnow()
        session.commit()
        
        raise
    
    finally:
        session.close()


def generate_insights(analyzed_pages: list) -> Dict:
    """Generate insights from analyzed pages."""
    insights = {
        'critical': [],
        'warnings': [],
        'recommendations': [],
        'positive': []
    }
    
    if not analyzed_pages:
        return insights
    
    total_pages = len(analyzed_pages)
    
    # SEO insights
    pages_without_title = sum(1 for p in analyzed_pages 
                             if not p.get('seo', {}).get('has_title'))
    if pages_without_title > 0:
        insights['critical'].append(
            f"{pages_without_title} page(s) missing title tags. "
            "Add unique, descriptive titles to all pages."
        )
    
    pages_without_description = sum(1 for p in analyzed_pages 
                                   if not p.get('seo', {}).get('has_meta_description'))
    if pages_without_description > 0:
        insights['warnings'].append(
            f"{pages_without_description} page(s) missing meta descriptions. "
            "Add compelling descriptions (150-160 characters)."
        )
    
    # Heading insights
    pages_multiple_h1 = sum(1 for p in analyzed_pages 
                           if p.get('headings', {}).get('has_multiple_h1'))
    if pages_multiple_h1 > 0:
        insights['warnings'].append(
            f"{pages_multiple_h1} page(s) have multiple H1 tags. "
            "Use only one H1 per page."
        )
    
    pages_no_h1 = sum(1 for p in analyzed_pages 
                     if p.get('headings', {}).get('h1_count', 0) == 0)
    if pages_no_h1 > 0:
        insights['warnings'].append(
            f"{pages_no_h1} page(s) missing H1 tags. "
            "Add a primary H1 heading to each page."
        )
    
    # Image insights
    total_images = sum(p.get('images', {}).get('count', 0) for p in analyzed_pages)
    missing_alt = sum(p.get('images', {}).get('missing_alt_count', 0) for p in analyzed_pages)
    if missing_alt > 0:
        insights['warnings'].append(
            f"{missing_alt} out of {total_images} images missing alt text. "
            "Add descriptive alt text for accessibility."
        )
    
    # Content insights
    avg_word_count = sum(p.get('seo', {}).get('word_count', 0) 
                        for p in analyzed_pages) / total_pages if total_pages > 0 else 0
    if avg_word_count < 300:
        insights['recommendations'].append(
            f"Average page word count is {int(avg_word_count)}. "
            "Consider adding more quality content (aim for 300+ words)."
        )
    else:
        insights['positive'].append(
            f"Good content depth with average {int(avg_word_count)} words per page."
        )
    
    # Accessibility insights
    pages_with_good_accessibility = sum(
        1 for p in analyzed_pages 
        if p.get('accessibility', {}).get('score', 0) >= 80
    )
    if pages_with_good_accessibility > total_pages * 0.8:
        insights['positive'].append(
            f"{pages_with_good_accessibility} out of {total_pages} pages have good accessibility scores."
        )
    
    return insights


def generate_summary(analyzed_pages: list) -> Dict:
    """Generate summary statistics from analyzed pages."""
    if not analyzed_pages:
        return {}
    
    total_pages = len(analyzed_pages)
    total_images = sum(p.get('images', {}).get('count', 0) for p in analyzed_pages)
    images_without_alt = sum(p.get('images', {}).get('missing_alt_count', 0) for p in analyzed_pages)
    total_internal_links = sum(p.get('links', {}).get('total_internal', 0) for p in analyzed_pages)
    total_external_links = sum(p.get('links', {}).get('total_external', 0) for p in analyzed_pages)
    avg_word_count = int(sum(p.get('seo', {}).get('word_count', 0) 
                            for p in analyzed_pages) / total_pages) if total_pages > 0 else 0
    
    return {
        'total_pages_analyzed': total_pages,
        'total_images': total_images,
        'images_without_alt': images_without_alt,
        'total_internal_links': total_internal_links,
        'total_external_links': total_external_links,
        'broken_links_found': 0,  # Would need separate link checking
        'avg_word_count': avg_word_count
    }


@celery_app.task
def generate_report_task(site_analysis_id: int, report_type: str = 'html'):
    """
    Generate a report for a site analysis.
    
    Args:
        site_analysis_id: Database ID of SiteAnalysis record
        report_type: Type of report ('html', 'text', 'google_docs')
        
    Returns:
        Report content or document ID
    """
    from we_si.models import init_db, SiteAnalysis, PageAnalysis
    from we_si.reports.html_report import HTMLReportGenerator
    from we_si.reports.text_report import TextReportGenerator
    from we_si.reports.gdoc_report import GoogleDocsReportGenerator
    
    engine, Session = init_db()
    session = Session()
    
    try:
        # Get site analysis
        site_analysis = session.query(SiteAnalysis).get(site_analysis_id)
        if not site_analysis:
            raise ValueError(f"SiteAnalysis {site_analysis_id} not found")
        
        # Get pages
        pages = session.query(PageAnalysis).filter_by(site_analysis_id=site_analysis_id).all()
        
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
            return generator.generate(analysis_data)
        elif report_type == 'text':
            generator = TextReportGenerator()
            return generator.generate(analysis_data)
        elif report_type == 'google_docs':
            generator = GoogleDocsReportGenerator()
            doc_id = generator.generate(analysis_data)
            return generator.get_document_url(doc_id)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    finally:
        session.close()

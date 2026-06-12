"""
HTML report generator for website analysis.
"""
from typing import Dict, List, Any
from datetime import datetime


class HTMLReportGenerator:
    """Generates styled HTML reports from analysis data."""
    
    def __init__(self):
        """Initialize the HTML report generator."""
        self.styles = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 10px;
                margin-bottom: 30px;
            }
            .header h1 {
                margin: 0 0 10px 0;
                font-size: 2.5em;
            }
            .header .subtitle {
                opacity: 0.9;
                font-size: 1.1em;
            }
            .summary-box {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .executive-summary {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-value {
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }
            .insights-section {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .insight-group {
                margin: 25px 0;
            }
            .insight-group h3 {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 15px;
            }
            .insight-item {
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid;
            }
            .critical { background: #fee; border-left-color: #dc3545; }
            .warning { background: #fff3cd; border-left-color: #ffc107; }
            .recommendation { background: #e7f3ff; border-left-color: #0d6efd; }
            .positive { background: #d4edda; border-left-color: #28a745; }
            .priority-badge {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: bold;
                margin-left: 10px;
            }
            .priority-critical { background: #dc3545; color: white; }
            .priority-high { background: #ffc107; color: #333; }
            .priority-medium { background: #0d6efd; color: white; }
            .page-section {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .page-header {
                border-bottom: 2px solid #667eea;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }
            .page-url {
                color: #667eea;
                font-weight: bold;
                word-break: break-all;
            }
            .section-title {
                color: #667eea;
                font-size: 1.3em;
                margin: 25px 0 15px 0;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
            }
            .metadata-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin: 15px 0;
            }
            .metadata-item {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
            }
            .metadata-label {
                font-weight: bold;
                color: #666;
                font-size: 0.9em;
            }
            .metadata-value {
                margin-top: 5px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background: #f8f9fa;
                font-weight: bold;
            }
            .platform-help {
                background: #e7f3ff;
                padding: 15px;
                border-radius: 5px;
                margin-top: 10px;
                font-size: 0.95em;
            }
            .cms-badge {
                display: inline-block;
                background: #28a745;
                color: white;
                padding: 5px 15px;
                border-radius: 15px;
                font-size: 0.9em;
                font-weight: bold;
            }
            @media print {
                body { background: white; }
                .page-section { box-shadow: none; border: 1px solid #ddd; }
            }
        </style>
        """
    
    def generate(self, analysis_data: Dict, include_pages: bool = True) -> str:
        """
        Generate HTML report from analysis data.
        
        Args:
            analysis_data: Complete analysis data dictionary
            include_pages: Whether to include individual page details
            
        Returns:
            HTML string
        """
        metadata = analysis_data.get('metadata', {})
        summary = analysis_data.get('summary', {})
        insights = analysis_data.get('insights', {})
        pages = analysis_data.get('pages', [])
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'<title>Website Analysis Report - {metadata.get("domain", "Unknown")}</title>',
            self.styles,
            '</head>',
            '<body>',
            self._generate_header(metadata),
            self._generate_executive_summary(summary, insights),
            self._generate_statistics(summary),
            self._generate_insights(insights),
        ]
        
        if include_pages and pages:
            html_parts.append(self._generate_pages_section(pages))
        
        html_parts.extend([
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def _generate_header(self, metadata: Dict) -> str:
        """Generate header section."""
        domain = metadata.get('domain', 'Unknown')
        base_url = metadata.get('base_url', '')
        analysis_date = metadata.get('analysis_date', 'Unknown')
        pages_crawled = metadata.get('pages_crawled', 0)
        
        return f'''
        <div class="header">
            <h1>Website Analysis Report</h1>
            <div class="subtitle">{domain}</div>
            <div style="margin-top: 15px; font-size: 0.95em;">
                <div>URL: {base_url}</div>
                <div>Analysis Date: {analysis_date}</div>
                <div>Pages Crawled: {pages_crawled}</div>
            </div>
        </div>
        '''
    
    def _generate_executive_summary(self, summary: Dict, insights: Dict) -> str:
        """Generate executive summary with key findings."""
        critical = insights.get('critical', [])
        warnings = insights.get('warnings', [])
        recommendations = insights.get('recommendations', [])
        
        priority_items = []
        
        # Add critical issues
        for item in critical[:3]:  # Top 3 critical
            priority_items.append(f'<li><strong>🔴 Critical:</strong> {item}</li>')
        
        # Add warnings
        for item in warnings[:2]:  # Top 2 warnings
            priority_items.append(f'<li><strong>⚠️ Warning:</strong> {item}</li>')
        
        # Add recommendations
        for item in recommendations[:2]:  # Top 2 recommendations
            priority_items.append(f'<li><strong>💡 Recommendation:</strong> {item}</li>')
        
        priority_html = ''.join(priority_items) if priority_items else '<li>No issues found - great job!</li>'
        
        return f'''
        <div class="summary-box">
            <h2>Executive Summary</h2>
            <div class="executive-summary">
                <h3>Prioritized Action Items</h3>
                <ul>
                    {priority_html}
                </ul>
            </div>
        </div>
        '''
    
    def _generate_statistics(self, summary: Dict) -> str:
        """Generate statistics cards."""
        stats = [
            ('Pages Analyzed', summary.get('total_pages_analyzed', 0)),
            ('Total Images', summary.get('total_images', 0)),
            ('Images w/o Alt', summary.get('images_without_alt', 0)),
            ('Internal Links', summary.get('total_internal_links', 0)),
            ('External Links', summary.get('total_external_links', 0)),
            ('Broken Links', summary.get('broken_links_found', 0)),
            ('Avg Word Count', summary.get('avg_word_count', 0)),
        ]
        
        cards_html = []
        for label, value in stats:
            cards_html.append(f'''
            <div class="stat-card">
                <div class="stat-value">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
            ''')
        
        return f'''
        <div class="summary-box">
            <h2>Key Statistics</h2>
            <div class="stats-grid">
                {''.join(cards_html)}
            </div>
        </div>
        '''
    
    def _generate_insights(self, insights: Dict) -> str:
        """Generate insights section."""
        sections = []
        
        # Critical issues
        if insights.get('critical'):
            items = '\n'.join([f'<div class="insight-item critical">{item}</div>' 
                             for item in insights['critical']])
            sections.append(f'''
            <div class="insight-group">
                <h3>🔴 Critical Issues</h3>
                {items}
            </div>
            ''')
        
        # Warnings
        if insights.get('warnings'):
            items = '\n'.join([f'<div class="insight-item warning">{item}</div>' 
                             for item in insights['warnings']])
            sections.append(f'''
            <div class="insight-group">
                <h3>⚠️ Warnings</h3>
                {items}
            </div>
            ''')
        
        # Recommendations
        if insights.get('recommendations'):
            items = '\n'.join([f'<div class="insight-item recommendation">{item}</div>' 
                             for item in insights['recommendations']])
            sections.append(f'''
            <div class="insight-group">
                <h3>💡 Recommendations</h3>
                {items}
            </div>
            ''')
        
        # Positive findings
        if insights.get('positive'):
            items = '\n'.join([f'<div class="insight-item positive">{item}</div>' 
                             for item in insights['positive']])
            sections.append(f'''
            <div class="insight-group">
                <h3>✅ Positive Findings</h3>
                {items}
            </div>
            ''')
        
        return f'''
        <div class="insights-section">
            <h2>Detailed Insights</h2>
            {''.join(sections)}
        </div>
        '''
    
    def _generate_pages_section(self, pages: List[Dict]) -> str:
        """Generate individual page analysis sections."""
        pages_html = []
        
        for idx, page in enumerate(pages, 1):
            pages_html.append(self._generate_page_detail(page, idx))
        
        return '\n'.join(pages_html)
    
    def _generate_page_detail(self, page: Dict, index: int) -> str:
        """Generate detail section for a single page."""
        url = page.get('url', 'Unknown')
        status_code = page.get('status_code', 0)
        
        # CMS detection
        cms = page.get('cms', {})
        cms_badge = ''
        if cms.get('detected'):
            cms_name = cms['detected'][0].title()
            cms_badge = f'<span class="cms-badge">{cms_name} Detected</span>'
        
        # SEO data
        seo = page.get('seo', {})
        
        # Suggestions
        suggestions = page.get('suggestions', [])
        suggestions_html = self._generate_suggestions_html(suggestions)
        
        return f'''
        <div class="page-section">
            <div class="page-header">
                <h2>Page {index}</h2>
                <div class="page-url">{url}</div>
                <div style="margin-top: 10px;">
                    <span>Status: {status_code}</span>
                    {cms_badge}
                </div>
            </div>
            
            <div class="section-title">SEO Overview</div>
            <div class="metadata-grid">
                <div class="metadata-item">
                    <div class="metadata-label">Title</div>
                    <div class="metadata-value">{seo.get('title', 'Not set')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Title Length</div>
                    <div class="metadata-value">{seo.get('title_length', 0)} chars 
                        {'✅' if seo.get('title_optimal') else '⚠️'}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Meta Description</div>
                    <div class="metadata-value">{seo.get('meta_description', 'Not set')[:100]}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Description Length</div>
                    <div class="metadata-value">{seo.get('meta_description_length', 0)} chars 
                        {'✅' if seo.get('description_optimal') else '⚠️'}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Word Count</div>
                    <div class="metadata-value">{seo.get('word_count', 0)}</div>
                </div>
            </div>
            
            {suggestions_html}
        </div>
        '''
    
    def _generate_suggestions_html(self, suggestions: List[Dict]) -> str:
        """Generate HTML for suggestions."""
        if not suggestions:
            return '<div class="section-title">✅ No issues found!</div>'
        
        html_parts = ['<div class="section-title">Actionable Suggestions</div>']
        
        for sugg in suggestions:
            priority = sugg.get('priority', 'medium')
            category = sugg.get('category', 'general')
            issue = sugg.get('issue', '')
            suggestion = sugg.get('suggestion', '')
            plain_language = sugg.get('plain_language', '')
            platform_help = sugg.get('platform_help', '')
            
            priority_class = f'priority-{priority}'
            priority_label = priority.upper()
            
            platform_html = ''
            if platform_help:
                platform_html = f'<div class="platform-help"><strong>How to fix:</strong> {platform_help}</div>'
            
            html_parts.append(f'''
            <div class="insight-item {priority}" style="margin: 15px 0;">
                <div>
                    <strong>{issue}</strong>
                    <span class="priority-badge {priority_class}">{priority_label}</span>
                </div>
                <div style="margin-top: 10px;">{suggestion}</div>
                <div style="margin-top: 8px; color: #666; font-style: italic;">{plain_language}</div>
                {platform_html}
            </div>
            ''')
        
        return '\n'.join(html_parts)

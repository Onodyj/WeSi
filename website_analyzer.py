#!/usr/bin/env python3
"""
WeSi - Website Analyzer
Comprehensive tool to map and analyze websites for SEO, structure, and content insights.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import Counter
import json
import re
from typing import Dict, List, Set, Tuple
import argparse
from datetime import datetime


class WebsiteAnalyzer:
    """Analyzes websites for structure, SEO, and content quality."""
    
    def __init__(self, base_url: str, max_depth: int = 3, timeout: int = 10):
        """
        Initialize the website analyzer.
        
        Args:
            base_url: The starting URL to analyze
            max_depth: Maximum depth for crawling (default: 3)
            timeout: Request timeout in seconds (default: 10)
        """
        self.base_url = base_url
        self.max_depth = max_depth
        self.timeout = timeout
        self.domain = urlparse(base_url).netloc
        self.visited_urls: Set[str] = set()
        self.results = {
            'pages': [],
            'summary': {},
            'recommendations': []
        }
        
    def fetch_page(self, url: str) -> Tuple[str, int]:
        """
        Fetch a page and return its content and status code.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (html_content, status_code)
        """
        try:
            headers = {
                'User-Agent': 'WeSi Website Analyzer Bot/1.0'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            return response.text, response.status_code
        except requests.exceptions.RequestException as e:
            return None, 0
    
    def analyze_heading_hierarchy(self, soup: BeautifulSoup) -> Dict:
        """Analyze heading structure and hierarchy."""
        headings = {f'h{i}': [] for i in range(1, 7)}
        hierarchy_issues = []
        
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text(strip=True)
                headings[f'h{i}'].append(text)
        
        # Check for h1 presence
        if len(headings['h1']) == 0:
            hierarchy_issues.append("Missing H1 heading")
        elif len(headings['h1']) > 1:
            hierarchy_issues.append(f"Multiple H1 headings found ({len(headings['h1'])})")
        
        # Check for hierarchy skips
        previous_level = 0
        for i in range(1, 7):
            if headings[f'h{i}']:
                if i - previous_level > 1 and previous_level > 0:
                    hierarchy_issues.append(f"Heading hierarchy skip: H{previous_level} to H{i}")
                previous_level = i
        
        return {
            'headings': headings,
            'counts': {key: len(val) for key, val in headings.items()},
            'issues': hierarchy_issues
        }
    
    def extract_images(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Extract all images with metadata."""
        images = []
        
        for idx, img in enumerate(soup.find_all('img')):
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            # Resolve relative URLs
            full_src = urljoin(page_url, src) if src else ''
            
            # Determine placement context
            parent = img.parent
            placement = 'body'
            if parent:
                if parent.name in ['header', 'nav']:
                    placement = 'header'
                elif parent.name == 'footer':
                    placement = 'footer'
                elif parent.name in ['aside', 'section']:
                    placement = parent.name
            
            images.append({
                'src': full_src,
                'alt': alt,
                'has_alt': bool(alt),
                'placement': placement,
                'position': idx + 1
            })
        
        return images
    
    def extract_links(self, soup: BeautifulSoup, page_url: str) -> Dict:
        """Extract and classify all links."""
        internal_links = []
        external_links = []
        broken_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Resolve relative URLs
            full_url = urljoin(page_url, href)
            parsed = urlparse(full_url)
            
            link_data = {
                'url': full_url,
                'text': text,
                'has_text': bool(text)
            }
            
            # Skip non-http(s) links
            if not parsed.scheme or parsed.scheme not in ['http', 'https']:
                continue
            
            # Classify as internal or external
            if parsed.netloc == self.domain or not parsed.netloc:
                internal_links.append(link_data)
            else:
                external_links.append(link_data)
        
        return {
            'internal': internal_links,
            'external': external_links,
            'internal_count': len(internal_links),
            'external_count': len(external_links)
        }
    
    def check_broken_links(self, links: List[str]) -> List[Dict]:
        """Check if links are broken."""
        broken = []
        checked = set()
        
        for link in links[:50]:  # Limit checking to avoid too many requests
            if link in checked:
                continue
            checked.add(link)
            
            try:
                response = requests.head(link, timeout=5, allow_redirects=True)
                if response.status_code >= 400:
                    broken.append({
                        'url': link,
                        'status_code': response.status_code
                    })
            except requests.exceptions.RequestException:
                broken.append({
                    'url': link,
                    'status_code': 0,
                    'error': 'Connection failed'
                })
        
        return broken
    
    def analyze_seo(self, soup: BeautifulSoup, url: str) -> Dict:
        """Perform comprehensive SEO analysis."""
        seo_data = {
            'title': '',
            'title_length': 0,
            'meta_description': '',
            'meta_description_length': 0,
            'meta_keywords': '',
            'og_tags': {},
            'twitter_tags': {},
            'canonical': '',
            'robots': '',
            'issues': []
        }
        
        # Title tag
        title = soup.find('title')
        if title:
            seo_data['title'] = title.get_text(strip=True)
            seo_data['title_length'] = len(seo_data['title'])
            
            if seo_data['title_length'] == 0:
                seo_data['issues'].append("Empty title tag")
            elif seo_data['title_length'] < 30:
                seo_data['issues'].append("Title tag too short (< 30 characters)")
            elif seo_data['title_length'] > 60:
                seo_data['issues'].append("Title tag too long (> 60 characters)")
        else:
            seo_data['issues'].append("Missing title tag")
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            seo_data['meta_description'] = meta_desc.get('content', '')
            seo_data['meta_description_length'] = len(seo_data['meta_description'])
            
            if seo_data['meta_description_length'] == 0:
                seo_data['issues'].append("Empty meta description")
            elif seo_data['meta_description_length'] < 120:
                seo_data['issues'].append("Meta description too short (< 120 characters)")
            elif seo_data['meta_description_length'] > 160:
                seo_data['issues'].append("Meta description too long (> 160 characters)")
        else:
            seo_data['issues'].append("Missing meta description")
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            seo_data['meta_keywords'] = meta_keywords.get('content', '')
        
        # Open Graph tags
        for og_tag in soup.find_all('meta', attrs={'property': re.compile(r'^og:')}):
            prop = og_tag.get('property', '')
            content = og_tag.get('content', '')
            seo_data['og_tags'][prop] = content
        
        # Twitter Card tags
        for twitter_tag in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            name = twitter_tag.get('name', '')
            content = twitter_tag.get('content', '')
            seo_data['twitter_tags'][name] = content
        
        # Canonical URL
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            seo_data['canonical'] = canonical.get('href', '')
        
        # Robots meta tag
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots:
            seo_data['robots'] = robots.get('content', '')
        
        return seo_data
    
    def analyze_content(self, soup: BeautifulSoup) -> Dict:
        """Analyze page content and keyword density."""
        # Extract body text
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Calculate keyword density
        word_count = len(words)
        word_freq = Counter(words)
        
        # Get top keywords
        top_keywords = word_freq.most_common(20)
        
        # Calculate density
        keyword_density = {}
        for word, count in top_keywords:
            density = (count / word_count * 100) if word_count > 0 else 0
            keyword_density[word] = {
                'count': count,
                'density': round(density, 2)
            }
        
        return {
            'word_count': word_count,
            'keyword_density': keyword_density,
            'top_keywords': [kw[0] for kw in top_keywords[:10]]
        }
    
    def analyze_layout_structure(self, soup: BeautifulSoup) -> Dict:
        """Analyze HTML5 semantic structure."""
        structure = {
            'has_header': bool(soup.find('header')),
            'has_nav': bool(soup.find('nav')),
            'has_main': bool(soup.find('main')),
            'has_footer': bool(soup.find('footer')),
            'has_aside': bool(soup.find('aside')),
            'sections': len(soup.find_all('section')),
            'articles': len(soup.find_all('article')),
            'issues': []
        }
        
        if not structure['has_header']:
            structure['issues'].append("Missing <header> element")
        if not structure['has_nav']:
            structure['issues'].append("Missing <nav> element")
        if not structure['has_main']:
            structure['issues'].append("Missing <main> element")
        if not structure['has_footer']:
            structure['issues'].append("Missing <footer> element")
        
        return structure
    
    def analyze_page(self, url: str) -> Dict:
        """Perform comprehensive analysis of a single page."""
        print(f"Analyzing: {url}")
        
        html, status_code = self.fetch_page(url)
        
        if not html or status_code == 0:
            return {
                'url': url,
                'status': 'error',
                'status_code': status_code,
                'error': 'Failed to fetch page'
            }
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Perform all analyses
        page_data = {
            'url': url,
            'status': 'success',
            'status_code': status_code,
            'heading_hierarchy': self.analyze_heading_hierarchy(soup),
            'images': self.extract_images(soup, url),
            'links': self.extract_links(soup, url),
            'seo': self.analyze_seo(soup, url),
            'content': self.analyze_content(soup),
            'structure': self.analyze_layout_structure(soup)
        }
        
        # Check for broken links
        all_links = [link['url'] for link in page_data['links']['internal']] + \
                    [link['url'] for link in page_data['links']['external']]
        page_data['broken_links'] = self.check_broken_links(all_links)
        
        return page_data
    
    def generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        if not self.results['pages']:
            return recommendations
        
        # Aggregate issues across all pages
        total_pages = len(self.results['pages'])
        pages_without_h1 = 0
        pages_with_multiple_h1 = 0
        images_without_alt = 0
        total_images = 0
        total_broken_links = 0
        pages_without_meta_desc = 0
        
        for page in self.results['pages']:
            if page['status'] != 'success':
                continue
            
            # H1 issues
            h1_issues = [i for i in page['heading_hierarchy']['issues'] if 'H1' in i]
            if any('Missing H1' in i for i in h1_issues):
                pages_without_h1 += 1
            if any('Multiple H1' in i for i in h1_issues):
                pages_with_multiple_h1 += 1
            
            # Image alt texts
            for img in page['images']:
                total_images += 1
                if not img['has_alt']:
                    images_without_alt += 1
            
            # Broken links
            total_broken_links += len(page['broken_links'])
            
            # SEO issues
            if 'Missing meta description' in page['seo']['issues']:
                pages_without_meta_desc += 1
        
        # Generate specific recommendations
        if pages_without_h1 > 0:
            recommendations.append(
                f"Add H1 headings to {pages_without_h1} page(s) for better SEO and accessibility."
            )
        
        if pages_with_multiple_h1 > 0:
            recommendations.append(
                f"Reduce to one H1 heading per page on {pages_with_multiple_h1} page(s)."
            )
        
        if total_images > 0 and images_without_alt > 0:
            pct = (images_without_alt / total_images * 100)
            recommendations.append(
                f"Add alt text to {images_without_alt} images ({pct:.1f}% of total) for accessibility and SEO."
            )
        
        if total_broken_links > 0:
            recommendations.append(
                f"Fix {total_broken_links} broken link(s) to improve user experience and SEO."
            )
        
        if pages_without_meta_desc > 0:
            recommendations.append(
                f"Add meta descriptions to {pages_without_meta_desc} page(s) to improve search result click-through rates."
            )
        
        # General recommendations
        recommendations.append(
            "Ensure all pages have unique, descriptive title tags (50-60 characters)."
        )
        recommendations.append(
            "Use semantic HTML5 elements (header, nav, main, footer) for better structure."
        )
        recommendations.append(
            "Maintain a clear heading hierarchy (H1-H6) without skipping levels."
        )
        recommendations.append(
            "Optimize images with compression and appropriate formats (WebP when possible)."
        )
        recommendations.append(
            "Implement internal linking strategy to improve site navigation and SEO."
        )
        
        return recommendations
    
    def analyze(self) -> Dict:
        """Run the complete website analysis."""
        print(f"Starting analysis of {self.base_url}")
        
        # Analyze the main page
        main_page = self.analyze_page(self.base_url)
        self.results['pages'].append(main_page)
        
        # Generate summary
        if main_page['status'] == 'success':
            self.results['summary'] = {
                'total_pages_analyzed': 1,
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'total_images': len(main_page['images']),
                'images_without_alt': sum(1 for img in main_page['images'] if not img['has_alt']),
                'internal_links': main_page['links']['internal_count'],
                'external_links': main_page['links']['external_count'],
                'broken_links': len(main_page['broken_links']),
                'word_count': main_page['content']['word_count'],
                'seo_score': self.calculate_seo_score(main_page)
            }
        
        # Generate recommendations
        self.results['recommendations'] = self.generate_recommendations()
        
        return self.results
    
    def calculate_seo_score(self, page: Dict) -> int:
        """Calculate a simple SEO score (0-100) based on best practices."""
        score = 100
        
        # Title issues
        if not page['seo']['title']:
            score -= 15
        elif page['seo']['title_length'] < 30 or page['seo']['title_length'] > 60:
            score -= 5
        
        # Meta description issues
        if not page['seo']['meta_description']:
            score -= 15
        elif page['seo']['meta_description_length'] < 120 or page['seo']['meta_description_length'] > 160:
            score -= 5
        
        # H1 issues
        h1_count = page['heading_hierarchy']['counts']['h1']
        if h1_count == 0:
            score -= 10
        elif h1_count > 1:
            score -= 5
        
        # Image alt text
        if page['images']:
            alt_ratio = sum(1 for img in page['images'] if img['has_alt']) / len(page['images'])
            if alt_ratio < 0.5:
                score -= 10
            elif alt_ratio < 0.8:
                score -= 5
        
        # Broken links
        if page['broken_links']:
            score -= min(len(page['broken_links']) * 5, 20)
        
        # Structure
        if not page['structure']['has_main']:
            score -= 5
        
        return max(0, score)
    
    def save_report(self, filename: str = 'website_analysis_report.json'):
        """Save the analysis report to a JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to {filename}")


def main():
    """Main entry point for the website analyzer."""
    parser = argparse.ArgumentParser(
        description='WeSi - Comprehensive Website Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python website_analyzer.py https://example.com
  python website_analyzer.py https://example.com --output my_report.json
  python website_analyzer.py https://example.com --timeout 20
        """
    )
    parser.add_argument('url', help='Website URL to analyze')
    parser.add_argument('-o', '--output', default='website_analysis_report.json',
                        help='Output JSON file (default: website_analysis_report.json)')
    parser.add_argument('-d', '--max-depth', type=int, default=3,
                        help='Maximum crawl depth (default: 3)')
    parser.add_argument('-t', '--timeout', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')
    
    args = parser.parse_args()
    
    # Create analyzer and run analysis
    analyzer = WebsiteAnalyzer(args.url, max_depth=args.max_depth, timeout=args.timeout)
    results = analyzer.analyze()
    
    # Save report
    analyzer.save_report(args.output)
    
    # Print summary
    print("\n" + "="*50)
    print("ANALYSIS SUMMARY")
    print("="*50)
    
    if results['summary']:
        summary = results['summary']
        print(f"Total Pages Analyzed: {summary['total_pages_analyzed']}")
        print(f"Total Images: {summary['total_images']}")
        print(f"Images Without Alt: {summary['images_without_alt']}")
        print(f"Internal Links: {summary['internal_links']}")
        print(f"External Links: {summary['external_links']}")
        print(f"Broken Links: {summary['broken_links']}")
        print(f"Word Count: {summary['word_count']}")
        print(f"SEO Score: {summary['seo_score']}/100")
    
    print("\n" + "="*50)
    print("RECOMMENDATIONS")
    print("="*50)
    for idx, rec in enumerate(results['recommendations'], 1):
        print(f"{idx}. {rec}")
    
    print("\n" + "="*50)
    print(f"Full report saved to: {args.output}")
    print("="*50)


if __name__ == '__main__':
    main()

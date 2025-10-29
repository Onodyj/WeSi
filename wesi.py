#!/usr/bin/env python3
"""
WeSi - Website Analyzer
A comprehensive tool to map and analyze website structure, content, and SEO.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import Counter, defaultdict
import json
import re
import sys
from typing import Dict, List, Set, Tuple, Any
import time


class WebsiteAnalyzer:
    """Comprehensive website analyzer for structure, content, and SEO analysis."""
    
    def __init__(self, base_url: str, max_pages: int = 50, timeout: int = 10):
        """
        Initialize the website analyzer.
        
        Args:
            base_url: The base URL of the website to analyze
            max_pages: Maximum number of pages to crawl (default: 50)
            timeout: Request timeout in seconds (default: 10)
        """
        # Validate URL before proceeding
        if not self.validate_url(base_url):
            raise ValueError(f"Invalid URL: {base_url}. Please provide a valid HTTP or HTTPS URL.")
        
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        
        if not self.domain:
            raise ValueError(f"Could not extract domain from URL: {base_url}")
        
        self.max_pages = max_pages
        self.timeout = timeout
        self.visited_urls: Set[str] = set()
        self.pages_data: List[Dict] = []
        self.broken_links: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WeSi-Bot/1.0 (Website Analyzer)'
        })
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate if a URL is properly formatted.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if the URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except Exception:
            return False
    
    def is_internal_url(self, url: str) -> bool:
        """Check if a URL is internal to the base domain."""
        parsed = urlparse(url)
        return parsed.netloc == self.domain or parsed.netloc == ''
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.rstrip('/')
    
    def fetch_page(self, url: str) -> Tuple[str, int]:
        """
        Fetch a page and return its content and status code.
        
        Returns:
            Tuple of (content, status_code)
        """
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            return response.text, response.status_code
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}", file=sys.stderr)
            return "", 0
    
    def extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract all visible text content from the page."""
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def analyze_headings(self, soup: BeautifulSoup) -> Dict:
        """Analyze heading hierarchy (H1-H6)."""
        headings = {f'h{i}': [] for i in range(1, 7)}
        
        for i in range(1, 7):
            tag_name = f'h{i}'
            for heading in soup.find_all(tag_name):
                headings[tag_name].append({
                    'text': heading.get_text(strip=True),
                    'id': heading.get('id', ''),
                    'class': heading.get('class', [])
                })
        
        return {
            'hierarchy': headings,
            'counts': {k: len(v) for k, v in headings.items()},
            'h1_count': len(headings['h1']),
            'has_multiple_h1': len(headings['h1']) > 1
        }
    
    def analyze_images(self, soup: BeautifulSoup, page_url: str) -> List[Dict]:
        """Analyze all images on the page."""
        images = []
        
        for idx, img in enumerate(soup.find_all('img')):
            src = img.get('src', '')
            absolute_src = urljoin(page_url, src) if src else ''
            
            # Determine image placement context
            parent = img.parent
            placement_context = parent.name if parent else 'unknown'
            
            # Check if image is in specific sections
            in_header = bool(img.find_parent('header'))
            in_footer = bool(img.find_parent('footer'))
            in_nav = bool(img.find_parent('nav'))
            in_article = bool(img.find_parent('article'))
            
            images.append({
                'index': idx,
                'src': src,
                'absolute_src': absolute_src,
                'alt': img.get('alt', ''),
                'has_alt': bool(img.get('alt')),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', ''),
                'placement_parent': placement_context,
                'in_header': in_header,
                'in_footer': in_footer,
                'in_nav': in_nav,
                'in_article': in_article,
                'loading': img.get('loading', ''),
                'classes': img.get('class', [])
            })
        
        return images
    
    def extract_links(self, soup: BeautifulSoup, page_url: str) -> Dict:
        """Extract and classify all links."""
        internal_links = []
        external_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            absolute_url = urljoin(page_url, href)
            link_data = {
                'text': link.get_text(strip=True),
                'href': href,
                'absolute_url': absolute_url,
                'title': link.get('title', ''),
                'rel': link.get('rel', []),
                'target': link.get('target', '')
            }
            
            if self.is_internal_url(absolute_url):
                internal_links.append(link_data)
            else:
                external_links.append(link_data)
        
        return {
            'internal': internal_links,
            'external': external_links,
            'total_internal': len(internal_links),
            'total_external': len(external_links),
            'total': len(internal_links) + len(external_links)
        }
    
    def check_broken_links(self, links: List[Dict], source_url: str) -> List[Dict]:
        """Check for broken links."""
        broken = []
        
        for link in links:
            url = link['absolute_url']
            try:
                response = self.session.head(url, timeout=5, allow_redirects=True)
                if response.status_code >= 400:
                    broken.append({
                        'url': url,
                        'status_code': response.status_code,
                        'text': link['text'],
                        'source_page': source_url
                    })
            except requests.RequestException:
                broken.append({
                    'url': url,
                    'status_code': 0,
                    'text': link['text'],
                    'source_page': source_url,
                    'error': 'Connection failed'
                })
        
        return broken
    
    def analyze_seo(self, soup: BeautifulSoup, text_content: str) -> Dict:
        """Perform comprehensive SEO analysis."""
        # Title tag
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        # Meta tags
        meta_description = ''
        meta_keywords = ''
        meta_robots = ''
        meta_tags = {}
        
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if name == 'description':
                meta_description = content
            elif name == 'keywords':
                meta_keywords = content
            elif name == 'robots':
                meta_robots = content
            
            # Store all meta tags
            key = name or property_attr
            if key:
                meta_tags[key] = content
        
        # Open Graph tags
        og_tags = {meta.get('property', '').replace('og:', ''): meta.get('content', '')
                   for meta in soup.find_all('meta', property=re.compile(r'^og:'))}
        
        # Twitter Card tags
        twitter_tags = {meta.get('name', '').replace('twitter:', ''): meta.get('content', '')
                       for meta in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})}
        
        # Keyword density analysis
        words = re.findall(r'\b\w+\b', text_content.lower())
        word_count = len(words)
        word_freq = Counter(words)
        
        # Remove common stop words for better keyword analysis
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                      'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
                      'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        
        keywords = {word: count for word, count in word_freq.most_common(20) 
                   if word not in stop_words and len(word) > 2}
        
        # Calculate keyword density
        keyword_density = {word: round((count / word_count) * 100, 2) 
                          for word, count in keywords.items()} if word_count > 0 else {}
        
        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        canonical_url = canonical.get('href', '') if canonical else ''
        
        # Language
        html_tag = soup.find('html')
        lang = html_tag.get('lang', '') if html_tag else ''
        
        return {
            'title': title,
            'title_length': len(title),
            'meta_description': meta_description,
            'meta_description_length': len(meta_description),
            'meta_keywords': meta_keywords,
            'meta_robots': meta_robots,
            'canonical_url': canonical_url,
            'language': lang,
            'all_meta_tags': meta_tags,
            'open_graph': og_tags,
            'twitter_card': twitter_tags,
            'word_count': word_count,
            'top_keywords': keywords,
            'keyword_density': keyword_density,
            'has_title': bool(title),
            'has_meta_description': bool(meta_description),
            'title_optimal': 50 <= len(title) <= 60,
            'description_optimal': 150 <= len(meta_description) <= 160
        }
    
    def analyze_structure(self, soup: BeautifulSoup) -> Dict:
        """Analyze the HTML structure and layout."""
        structure = {
            'has_header': bool(soup.find('header')),
            'has_footer': bool(soup.find('footer')),
            'has_nav': bool(soup.find('nav')),
            'has_main': bool(soup.find('main')),
            'has_article': bool(soup.find('article')),
            'has_aside': bool(soup.find('aside')),
            'nav_count': len(soup.find_all('nav')),
            'article_count': len(soup.find_all('article')),
            'section_count': len(soup.find_all('section')),
            'div_count': len(soup.find_all('div')),
            'form_count': len(soup.find_all('form')),
            'table_count': len(soup.find_all('table')),
            'list_count': len(soup.find_all(['ul', 'ol'])),
        }
        
        # Check for semantic HTML5 elements
        semantic_elements = ['header', 'footer', 'nav', 'main', 'article', 
                            'aside', 'section', 'figure', 'figcaption']
        structure['semantic_elements_used'] = [elem for elem in semantic_elements 
                                               if soup.find(elem)]
        
        return structure
    
    def _create_empty_page_data(self, url: str, error_msg: str = 'Failed to fetch page', status_code: int = 0) -> Dict:
        """
        Create an empty page data structure for failed page fetches.
        
        Args:
            url: The URL that failed
            error_msg: The error message to include
            status_code: HTTP status code (0 for connection failures)
            
        Returns:
            A dictionary with empty/default values for all expected fields
        """
        return {
            'url': url,
            'error': error_msg,
            'status_code': status_code,
            'text_length': 0,
            'structure': {
                'has_header': False,
                'has_footer': False,
                'has_nav': False,
                'has_main': False,
                'has_article': False,
                'has_aside': False,
                'nav_count': 0,
                'article_count': 0,
                'section_count': 0,
                'div_count': 0,
                'form_count': 0,
                'table_count': 0,
                'list_count': 0,
                'semantic_elements_used': []
            },
            'headings': {
                'hierarchy': {f'h{i}': [] for i in range(1, 7)},
                'counts': {f'h{i}': 0 for i in range(1, 7)},
                'h1_count': 0,
                'has_multiple_h1': False
            },
            'images': {
                'count': 0,
                'images': [],
                'missing_alt': [],
                'missing_alt_count': 0
            },
            'links': {
                'internal': [],
                'external': [],
                'total_internal': 0,
                'total_external': 0,
                'total': 0
            },
            'broken_links': [],
            'seo': {
                'title': '',
                'title_length': 0,
                'meta_description': '',
                'meta_description_length': 0,
                'meta_keywords': '',
                'meta_robots': '',
                'canonical_url': '',
                'language': '',
                'all_meta_tags': {},
                'open_graph': {},
                'twitter_card': {},
                'word_count': 0,
                'top_keywords': {},
                'keyword_density': {},
                'has_title': False,
                'has_meta_description': False,
                'title_optimal': False,
                'description_optimal': False
            }
        }
    
    def analyze_page(self, url: str, verbose: bool = True) -> Dict:
        """
        Perform comprehensive analysis of a single page.
        
        Args:
            url: The URL to analyze
            verbose: If True, print status message (default: True)
        """
        if verbose:
            print(f"Analyzing: {url}")
        
        content, status_code = self.fetch_page(url)
        if status_code == 0 or not content:
            # Return a consistent structure even when fetch fails
            return self._create_empty_page_data(url, 'Failed to fetch page', status_code)
        
        soup = BeautifulSoup(content, 'lxml')
        text_content = self.extract_text_content(soup)
        
        # Perform all analyses
        headings = self.analyze_headings(soup)
        images = self.analyze_images(soup, url)
        links = self.extract_links(soup, url)
        seo = self.analyze_seo(soup, text_content)
        structure = self.analyze_structure(soup)
        
        # Check for broken links (sample only to avoid too many requests)
        all_links = links['internal'] + links['external']
        sample_size = min(10, len(all_links))
        broken = self.check_broken_links(all_links[:sample_size], url) if all_links else []
        
        return {
            'url': url,
            'status_code': status_code,
            'text_length': len(text_content),
            'structure': structure,
            'headings': headings,
            'images': {
                'count': len(images),
                'images': images,
                'missing_alt': [img for img in images if not img['has_alt']],
                'missing_alt_count': sum(1 for img in images if not img['has_alt'])
            },
            'links': links,
            'broken_links': broken,
            'seo': seo
        }
    
    def crawl(self):
        """Crawl the website starting from the base URL."""
        to_visit = [self.base_url]
        
        while to_visit and len(self.visited_urls) < self.max_pages:
            url = to_visit.pop(0)
            normalized = self.normalize_url(url)
            
            if normalized in self.visited_urls:
                continue
            
            self.visited_urls.add(normalized)
            
            # Show progress with truncated URL if needed
            progress = f"[{len(self.visited_urls)}/{self.max_pages}]"
            display_url = f"{normalized[:80]}..." if len(normalized) > 80 else normalized
            print(f"{progress} Analyzing: {display_url}")
            
            try:
                page_data = self.analyze_page(normalized, verbose=False)
                self.pages_data.append(page_data)
                
                # Only add internal links if page was successfully fetched
                if not page_data.get('error') and 'links' in page_data and 'internal' in page_data['links']:
                    for link in page_data['links']['internal']:
                        link_url = self.normalize_url(link['absolute_url'])
                        if link_url not in self.visited_urls and link_url not in to_visit:
                            to_visit.append(link_url)
            except Exception as e:
                print(f"  ⚠️  Error analyzing page: {e}")
                # Use helper method for consistent error structure
                error_data = self._create_empty_page_data(normalized, str(e), 0)
                self.pages_data.append(error_data)
            
            # Be nice to the server
            time.sleep(0.5)
        
        print(f"\nCrawl complete! Analyzed {len(self.visited_urls)} page(s).")
    
    def generate_insights(self) -> Dict:
        """Generate actionable insights from the analysis."""
        if not self.pages_data:
            return {'error': 'No pages analyzed'}
        
        insights = {
            'critical': [],
            'warnings': [],
            'recommendations': [],
            'positive': []
        }
        
        # Analyze collected data for insights
        total_pages = len(self.pages_data)
        
        # SEO insights
        pages_without_title = sum(1 for p in self.pages_data 
                                 if 'seo' in p and not p['seo'].get('has_title'))
        if pages_without_title > 0:
            insights['critical'].append(
                f"{pages_without_title} page(s) missing title tags. "
                "Add unique, descriptive titles to all pages."
            )
        
        pages_without_description = sum(1 for p in self.pages_data 
                                       if 'seo' in p and not p['seo'].get('has_meta_description'))
        if pages_without_description > 0:
            insights['warnings'].append(
                f"{pages_without_description} page(s) missing meta descriptions. "
                "Add compelling descriptions (150-160 characters) to improve click-through rates."
            )
        
        # Heading hierarchy insights
        pages_multiple_h1 = sum(1 for p in self.pages_data 
                               if 'headings' in p and p['headings'].get('has_multiple_h1'))
        if pages_multiple_h1 > 0:
            insights['warnings'].append(
                f"{pages_multiple_h1} page(s) have multiple H1 tags. "
                "Use only one H1 per page for better SEO."
            )
        
        pages_no_h1 = sum(1 for p in self.pages_data 
                         if 'headings' in p and p['headings']['counts']['h1'] == 0)
        if pages_no_h1 > 0:
            insights['warnings'].append(
                f"{pages_no_h1} page(s) missing H1 tags. "
                "Add a primary H1 heading to each page."
            )
        
        # Image insights
        total_images = sum(p.get('images', {}).get('count', 0) for p in self.pages_data)
        missing_alt = sum(p.get('images', {}).get('missing_alt_count', 0) for p in self.pages_data)
        if missing_alt > 0:
            insights['warnings'].append(
                f"{missing_alt} out of {total_images} images missing alt text. "
                "Add descriptive alt text for accessibility and SEO."
            )
        
        # Link insights
        total_broken = sum(len(p.get('broken_links', [])) for p in self.pages_data)
        if total_broken > 0:
            insights['critical'].append(
                f"Found {total_broken} potentially broken link(s). "
                "Fix or remove broken links to improve user experience and SEO."
            )
        
        # Structure insights
        pages_no_semantic = sum(1 for p in self.pages_data 
                               if 'structure' in p and 
                               len(p['structure'].get('semantic_elements_used', [])) < 3)
        if pages_no_semantic > 0:
            insights['recommendations'].append(
                f"{pages_no_semantic} page(s) use limited semantic HTML5 elements. "
                "Use elements like <header>, <nav>, <main>, <article> for better structure."
            )
        
        # Content insights
        avg_word_count = sum(p.get('seo', {}).get('word_count', 0) 
                            for p in self.pages_data) / total_pages if total_pages > 0 else 0
        if avg_word_count < 300:
            insights['recommendations'].append(
                f"Average page word count is {int(avg_word_count)}. "
                "Consider adding more quality content (aim for 300+ words per page)."
            )
        else:
            insights['positive'].append(
                f"Good content depth with average {int(avg_word_count)} words per page."
            )
        
        # External links
        avg_external = sum(p.get('links', {}).get('total_external', 0) 
                          for p in self.pages_data) / total_pages if total_pages > 0 else 0
        if avg_external < 2:
            insights['recommendations'].append(
                "Consider adding more authoritative external links to improve content credibility."
            )
        
        return insights
    
    def generate_report(self) -> Dict:
        """Generate comprehensive JSON report with insights."""
        insights = self.generate_insights()
        
        # Calculate summary statistics
        summary = {
            'total_pages_analyzed': len(self.pages_data),
            'total_images': sum(p.get('images', {}).get('count', 0) for p in self.pages_data),
            'images_without_alt': sum(p.get('images', {}).get('missing_alt_count', 0) 
                                     for p in self.pages_data),
            'total_internal_links': sum(p.get('links', {}).get('total_internal', 0) 
                                       for p in self.pages_data),
            'total_external_links': sum(p.get('links', {}).get('total_external', 0) 
                                       for p in self.pages_data),
            'broken_links_found': sum(len(p.get('broken_links', [])) for p in self.pages_data),
            'avg_word_count': int(sum(p.get('seo', {}).get('word_count', 0) 
                                     for p in self.pages_data) / len(self.pages_data)) 
                             if self.pages_data else 0,
        }
        
        report = {
            'metadata': {
                'base_url': self.base_url,
                'domain': self.domain,
                'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'pages_crawled': len(self.visited_urls)
            },
            'summary': summary,
            'insights': insights,
            'pages': self.pages_data
        }
        
        return report
    
    def save_report(self, filename: str = 'website_analysis.json'):
        """Save the analysis report to a JSON file."""
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to: {filename}")
        return filename


def main():
    """Main entry point for the CLI."""
    if len(sys.argv) < 2:
        print("Usage: python wesi.py <website_url> [max_pages] [output_file]")
        print("\nExample:")
        print("  python wesi.py https://example.com 10 report.json")
        print("\nOptions:")
        print("  website_url  - The URL of the website to analyze (required)")
        print("  max_pages    - Maximum number of pages to crawl (default: 50)")
        print("  output_file  - Output JSON file name (default: website_analysis.json)")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Validate max_pages argument
    try:
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        if max_pages <= 0:
            print("Error: max_pages must be a positive integer")
            sys.exit(1)
    except ValueError:
        print(f"Error: max_pages must be an integer, got '{sys.argv[2]}'")
        sys.exit(1)
    
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'website_analysis.json'
    
    print(f"Starting analysis of {url}")
    print(f"Maximum pages to crawl: {max_pages}\n")
    
    try:
        analyzer = WebsiteAnalyzer(url, max_pages=max_pages)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error initializing analyzer: {e}")
        sys.exit(1)
    
    try:
        analyzer.crawl()
    except Exception as e:
        print(f"\nError during crawling: {e}")
        print("Attempting to generate report with collected data...")
    
    if not analyzer.pages_data:
        print("\nError: No pages were successfully analyzed. Please check the URL and try again.")
        sys.exit(1)
    
    report = analyzer.generate_report()
    
    # Display insights
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE - INSIGHTS")
    print("="*70)
    
    insights = report['insights']
    
    if insights.get('critical'):
        print("\n🔴 CRITICAL ISSUES:")
        for insight in insights['critical']:
            print(f"  - {insight}")
    
    if insights.get('warnings'):
        print("\n⚠️  WARNINGS:")
        for insight in insights['warnings']:
            print(f"  - {insight}")
    
    if insights.get('recommendations'):
        print("\n💡 RECOMMENDATIONS:")
        for insight in insights['recommendations']:
            print(f"  - {insight}")
    
    if insights.get('positive'):
        print("\n✅ POSITIVE FINDINGS:")
        for insight in insights['positive']:
            print(f"  - {insight}")
    
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    summary = report['summary']
    print(f"Pages analyzed: {summary['total_pages_analyzed']}")
    print(f"Total images: {summary['total_images']}")
    print(f"Images without alt text: {summary['images_without_alt']}")
    print(f"Internal links: {summary['total_internal_links']}")
    print(f"External links: {summary['total_external_links']}")
    print(f"Broken links: {summary['broken_links_found']}")
    print(f"Average word count: {summary['avg_word_count']}")
    
    analyzer.save_report(output_file)
    print(f"\n✅ Full detailed report saved to: {output_file}")


if __name__ == '__main__':
    main()

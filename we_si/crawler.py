"""
Enhanced website crawler with robots.txt support and rate limiting.
"""
import time
import re
from typing import Set, List, Dict, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
import requests


class WebsiteCrawler:
    """
    Enhanced website crawler that respects robots.txt, implements rate limiting,
    and supports subscription-based page limits.
    """
    
    def __init__(
        self,
        base_url: str,
        max_pages: int = 50,
        max_depth: int = 3,
        timeout: int = 10,
        rate_limit: float = 0.5,
        user_agent: str = 'WeSi-Bot/2.0 (Website Analyzer)'
    ):
        """
        Initialize the crawler.
        
        Args:
            base_url: The base URL to start crawling from
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum depth to crawl from base URL
            timeout: Request timeout in seconds
            rate_limit: Delay between requests in seconds
            user_agent: User agent string for requests
        """
        self.base_url = base_url.rstrip('/')
        parsed = urlparse(base_url)
        self.domain = parsed.netloc
        self.scheme = parsed.scheme
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.user_agent = user_agent
        
        self.visited_urls: Set[str] = set()
        self.robots_parser: Optional[RobotFileParser] = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Initialize robots.txt parser
        self._init_robots_parser()
    
    def _init_robots_parser(self):
        """Initialize and load robots.txt parser."""
        robots_url = f"{self.scheme}://{self.domain}/robots.txt"
        self.robots_parser = RobotFileParser()
        self.robots_parser.set_url(robots_url)
        
        try:
            self.robots_parser.read()
        except Exception as e:
            print(f"Warning: Could not read robots.txt from {robots_url}: {e}")
            # If we can't read robots.txt, we'll assume all URLs are allowed
            self.robots_parser = None
    
    def can_fetch(self, url: str) -> bool:
        """
        Check if the URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            
        Returns:
            True if the URL can be fetched, False otherwise
        """
        if self.robots_parser is None:
            return True
        
        try:
            return self.robots_parser.can_fetch(self.user_agent, url)
        except Exception:
            # If there's an error checking, assume it's allowed
            return True
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments, trailing slashes, and standardizing format.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL string
        """
        parsed = urlparse(url)
        
        # Remove fragment
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),  # Lowercase domain
            parsed.path.rstrip('/') or '/',  # Remove trailing slash except for root
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        
        return normalized
    
    def is_internal_url(self, url: str) -> bool:
        """
        Check if a URL is internal to the base domain.
        
        Args:
            url: URL to check
            
        Returns:
            True if the URL is internal, False otherwise
        """
        parsed = urlparse(url)
        return parsed.netloc == self.domain or parsed.netloc == ''
    
    def is_valid_url(self, url: str) -> bool:
        """
        Check if a URL is valid for crawling.
        
        Args:
            url: URL to validate
            
        Returns:
            True if the URL is valid, False otherwise
        """
        if not url:
            return False
        
        # Skip non-HTTP(S) URLs
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https', ''):
            return False
        
        # Skip common non-HTML resources
        excluded_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
            '.css', '.js', '.json', '.xml', '.zip', '.tar', '.gz',
            '.mp4', '.avi', '.mov', '.mp3', '.wav', '.doc', '.docx',
            '.xls', '.xlsx', '.ppt', '.pptx'
        }
        
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in excluded_extensions):
            return False
        
        return True
    
    def extract_links(self, html: str, page_url: str) -> List[str]:
        """
        Extract all links from HTML content.
        
        Args:
            html: HTML content
            page_url: URL of the page (for resolving relative links)
            
        Returns:
            List of absolute URLs
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            
            # Skip invalid hrefs
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(page_url, href)
            
            # Validate and normalize
            if self.is_valid_url(absolute_url) and self.is_internal_url(absolute_url):
                normalized = self.normalize_url(absolute_url)
                links.append(normalized)
        
        return links
    
    def fetch_page(self, url: str) -> tuple[str, int]:
        """
        Fetch a page and return its content and status code.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (content, status_code)
        """
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            return response.text, response.status_code
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return "", 0
    
    def crawl(self, progress_callback=None) -> List[Dict]:
        """
        Crawl the website starting from the base URL.
        
        Args:
            progress_callback: Optional callback function(current, total, url) for progress updates
            
        Returns:
            List of dictionaries containing URL and HTML content for each crawled page
        """
        # Queue contains tuples of (url, depth)
        to_visit = [(self.base_url, 0)]
        crawled_pages = []
        
        while to_visit and len(self.visited_urls) < self.max_pages:
            url, depth = to_visit.pop(0)
            normalized = self.normalize_url(url)
            
            # Skip if already visited
            if normalized in self.visited_urls:
                continue
            
            # Skip if beyond max depth
            if depth > self.max_depth:
                continue
            
            # Check robots.txt
            if not self.can_fetch(normalized):
                print(f"Skipping {normalized} (disallowed by robots.txt)")
                continue
            
            # Mark as visited
            self.visited_urls.add(normalized)
            
            # Fetch the page
            if progress_callback:
                progress_callback(len(self.visited_urls), self.max_pages, normalized)
            
            content, status_code = self.fetch_page(normalized)
            
            if status_code == 0 or not content:
                crawled_pages.append({
                    'url': normalized,
                    'content': '',
                    'status_code': status_code,
                    'depth': depth,
                    'error': 'Failed to fetch'
                })
            else:
                crawled_pages.append({
                    'url': normalized,
                    'content': content,
                    'status_code': status_code,
                    'depth': depth
                })
                
                # Extract and queue internal links
                links = self.extract_links(content, normalized)
                for link in links:
                    if link not in self.visited_urls and not any(l[0] == link for l in to_visit):
                        to_visit.append((link, depth + 1))
            
            # Rate limiting
            time.sleep(self.rate_limit)
        
        return crawled_pages

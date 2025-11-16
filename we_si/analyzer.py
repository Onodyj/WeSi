"""
Enhanced page analyzer with CMS detection and detailed extraction.
"""
import re
import time
from typing import Dict, List, Any
from collections import Counter
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class PageAnalyzer:
    """
    Enhanced page analyzer that extracts comprehensive metadata,
    detects CMS/page builders, and provides actionable suggestions.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.cms_patterns = {
            'wordpress': {
                'meta_generator': r'WordPress',
                'scripts': ['/wp-content/', '/wp-includes/'],
                'classes': ['wp-', 'wordpress']
            },
            'squarespace': {
                'meta_generator': r'Squarespace',
                'scripts': ['/universal/scripts-compressed/'],
                'classes': ['sqs-', 'squarespace']
            },
            'wix': {
                'meta_generator': r'Wix\.com',
                'scripts': ['parastorage.com', 'wixstatic.com'],
                'classes': ['wix-']
            },
            'shopify': {
                'meta_generator': r'Shopify',
                'scripts': ['/cdn.shopify.com'],
                'classes': ['shopify-']
            },
            'joomla': {
                'meta_generator': r'Joomla',
                'scripts': ['/media/system/js/'],
                'classes': ['joomla']
            },
            'drupal': {
                'meta_generator': r'Drupal',
                'scripts': ['/misc/drupal.js'],
                'classes': ['drupal']
            }
        }
    
    def detect_cms(self, soup: BeautifulSoup, html: str) -> Dict[str, Any]:
        """
        Detect CMS or page builder being used.
        
        Args:
            soup: BeautifulSoup object of the page
            html: Raw HTML content
            
        Returns:
            Dictionary with CMS detection results
        """
        detected = []
        confidence_scores = {}
        
        for cms_name, patterns in self.cms_patterns.items():
            score = 0
            
            # Check meta generator
            meta_gen = soup.find('meta', attrs={'name': 'generator'})
            if meta_gen:
                content = meta_gen.get('content', '')
                if re.search(patterns['meta_generator'], content, re.IGNORECASE):
                    score += 3
            
            # Check scripts
            for script in soup.find_all('script', src=True):
                src = script.get('src', '')
                if any(pattern in src for pattern in patterns['scripts']):
                    score += 2
                    break
            
            # Check class names
            for class_pattern in patterns['classes']:
                if class_pattern in html:
                    score += 1
                    break
            
            if score > 0:
                confidence_scores[cms_name] = score
                if score >= 3:
                    detected.append(cms_name)
        
        # Sort by confidence
        sorted_cms = sorted(confidence_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'detected': detected,
            'probable': sorted_cms[0][0] if sorted_cms else None,
            'confidence_scores': dict(sorted_cms),
            'all_scores': confidence_scores
        }
    
    def extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract JSON-LD structured data.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of structured data objects
        """
        import json
        structured_data = []
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except (json.JSONDecodeError, AttributeError):
                pass
        
        return structured_data
    
    def analyze_accessibility(self, soup: BeautifulSoup, images: Dict) -> Dict:
        """
        Analyze accessibility features.
        
        Args:
            soup: BeautifulSoup object
            images: Dictionary with image data (has 'images' list)
            
        Returns:
            Accessibility analysis results
        """
        issues = []
        warnings = []
        good_practices = []
        
        # Check images - handle both dict with 'images' key and list of images
        if isinstance(images, dict):
            images_list = images.get('images', [])
        else:
            images_list = images
        
        images_without_alt = sum(1 for img in images_list if not img.get('has_alt', True))
        if images_without_alt > 0:
            issues.append(f"{images_without_alt} image(s) missing alt text")
        elif images_list:
            good_practices.append("All images have alt text")
        
        # Check form labels
        forms = soup.find_all('form')
        for form in forms:
            inputs = form.find_all(['input', 'textarea', 'select'])
            for inp in inputs:
                inp_id = inp.get('id')
                if inp_id:
                    label = soup.find('label', attrs={'for': inp_id})
                    if not label:
                        warnings.append(f"Form input without associated label")
                        break
        
        # Check heading hierarchy
        headings = []
        for i in range(1, 7):
            for h in soup.find_all(f'h{i}'):
                headings.append(i)
        
        if headings:
            # Check for skipped levels
            for i in range(len(headings) - 1):
                if headings[i + 1] - headings[i] > 1:
                    warnings.append("Heading hierarchy skips levels")
                    break
        
        # Check for ARIA landmarks
        has_main = bool(soup.find('main')) or bool(soup.find(attrs={'role': 'main'}))
        has_nav = bool(soup.find('nav')) or bool(soup.find(attrs={'role': 'navigation'}))
        
        if has_main and has_nav:
            good_practices.append("Page uses semantic landmarks")
        else:
            warnings.append("Consider using semantic landmarks (main, nav)")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'good_practices': good_practices,
            'score': max(0, 100 - (len(issues) * 20) - (len(warnings) * 10))
        }
    
    def generate_suggestions(self, analysis: Dict, cms: Dict) -> List[Dict]:
        """
        Generate plain-language, actionable suggestions.
        
        Args:
            analysis: Page analysis data
            cms: CMS detection data
            
        Returns:
            List of suggestion dictionaries with priority and platform-specific guidance
        """
        suggestions = []
        detected_cms = cms.get('probable')
        
        # SEO suggestions
        seo = analysis.get('seo', {})
        if not seo.get('has_title'):
            suggestion = {
                'priority': 'critical',
                'category': 'seo',
                'issue': 'Missing page title',
                'suggestion': 'Add a unique, descriptive title to this page (50-60 characters recommended)',
                'plain_language': 'Your page needs a title that appears in search results and browser tabs.'
            }
            
            if detected_cms == 'squarespace':
                suggestion['platform_help'] = 'In Squarespace: Go to the page settings → SEO → Page Title'
            elif detected_cms == 'wordpress':
                suggestion['platform_help'] = 'In WordPress: Edit the page → look for SEO settings or use Yoast SEO plugin'
            elif detected_cms == 'wix':
                suggestion['platform_help'] = 'In Wix: Page Settings → SEO Basics → Page Title'
            
            suggestions.append(suggestion)
        
        if not seo.get('has_meta_description'):
            suggestion = {
                'priority': 'high',
                'category': 'seo',
                'issue': 'Missing meta description',
                'suggestion': 'Add a compelling meta description (150-160 characters) that summarizes the page',
                'plain_language': 'This is the preview text people see in search results. Make it engaging!'
            }
            
            if detected_cms == 'squarespace':
                suggestion['platform_help'] = 'In Squarespace: Page settings → SEO → Description'
            elif detected_cms == 'wordpress':
                suggestion['platform_help'] = 'In WordPress: Edit page → Meta Description field (usually in SEO plugin)'
            elif detected_cms == 'wix':
                suggestion['platform_help'] = 'In Wix: Page Settings → SEO Basics → Meta Description'
            
            suggestions.append(suggestion)
        
        # Heading suggestions
        headings = analysis.get('headings', {})
        if headings.get('h1_count', 0) == 0:
            suggestions.append({
                'priority': 'high',
                'category': 'content',
                'issue': 'Missing H1 heading',
                'suggestion': 'Add a main heading (H1) that describes the page topic',
                'plain_language': 'Every page should have one main heading - it helps both readers and search engines understand your page.'
            })
        elif headings.get('h1_count', 0) > 1:
            suggestions.append({
                'priority': 'medium',
                'category': 'content',
                'issue': 'Multiple H1 headings',
                'suggestion': 'Use only one H1 heading per page; convert others to H2 or H3',
                'plain_language': 'Having multiple main headings confuses search engines. Choose one main heading and make others subheadings.'
            })
        
        # Image suggestions
        images = analysis.get('images', {})
        missing_alt = images.get('missing_alt_count', 0)
        if missing_alt > 0:
            suggestion = {
                'priority': 'high',
                'category': 'accessibility',
                'issue': f'{missing_alt} image(s) without alt text',
                'suggestion': 'Add descriptive alt text to all images',
                'plain_language': 'Alt text helps visually impaired users and improves SEO. Describe what the image shows.'
            }
            
            if detected_cms == 'squarespace':
                suggestion['platform_help'] = 'In Squarespace: Click image → Edit → Filename & Alt Text'
            elif detected_cms == 'wordpress':
                suggestion['platform_help'] = 'In WordPress: Click image → Alt Text field'
            elif detected_cms == 'wix':
                suggestion['platform_help'] = 'In Wix: Click image → Settings → Alt Text'
            
            suggestions.append(suggestion)
        
        # Content suggestions
        word_count = seo.get('word_count', 0)
        if word_count < 300:
            suggestions.append({
                'priority': 'medium',
                'category': 'content',
                'issue': 'Thin content',
                'suggestion': f'Current word count is {word_count}. Aim for at least 300 words of quality content',
                'plain_language': 'Search engines prefer pages with substantial, helpful content. Add more valuable information for your visitors.'
            })
        
        # Performance suggestion
        if analysis.get('load_time', 0) > 3:
            suggestions.append({
                'priority': 'medium',
                'category': 'performance',
                'issue': 'Slow page load time',
                'suggestion': f'Page took {analysis.get("load_time", 0):.2f} seconds to load. Optimize images and reduce file sizes',
                'plain_language': 'Slow pages frustrate visitors and hurt search rankings. Compress images and minimize code.'
            })
        
        return suggestions
    
    def analyze_page(self, url: str, html: str, start_time: float = None) -> Dict:
        """
        Perform comprehensive analysis of a page.
        
        Args:
            url: Page URL
            html: HTML content
            start_time: Optional start time for load time calculation
            
        Returns:
            Dictionary containing complete page analysis
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Calculate load time if start_time provided
        load_time = time.time() - start_time if start_time else 0
        
        # Extract basic data
        text_content = self._extract_text_content(soup)
        headings = self._analyze_headings(soup)
        images = self._analyze_images(soup, url)
        links = self._extract_links(soup, url)
        seo = self._analyze_seo(soup, text_content)
        structure = self._analyze_structure(soup)
        
        # Enhanced features
        cms = self.detect_cms(soup, html)
        structured_data = self.extract_structured_data(soup)
        accessibility = self.analyze_accessibility(soup, images)
        
        # Canonical tag
        canonical = soup.find('link', rel='canonical')
        canonical_url = canonical.get('href', '') if canonical else ''
        
        # Combine all analysis
        analysis = {
            'url': url,
            'load_time': load_time,
            'text_length': len(text_content),
            'structure': structure,
            'headings': headings,
            'images': images,
            'links': links,
            'seo': {
                **seo,
                'canonical_url': canonical_url
            },
            'cms': cms,
            'structured_data': structured_data,
            'accessibility': accessibility
        }
        
        # Generate suggestions
        analysis['suggestions'] = self.generate_suggestions(analysis, cms)
        
        return analysis
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract all visible text content."""
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _analyze_headings(self, soup: BeautifulSoup) -> Dict:
        """Analyze heading hierarchy."""
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
    
    def _analyze_images(self, soup: BeautifulSoup, page_url: str) -> Dict:
        """Analyze all images on the page."""
        images = []
        
        for idx, img in enumerate(soup.find_all('img')):
            src = img.get('src', '')
            absolute_src = urljoin(page_url, src) if src else ''
            
            parent = img.parent
            placement_context = parent.name if parent else 'unknown'
            
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
        
        return {
            'count': len(images),
            'images': images,
            'missing_alt': [img for img in images if not img['has_alt']],
            'missing_alt_count': sum(1 for img in images if not img['has_alt'])
        }
    
    def _extract_links(self, soup: BeautifulSoup, page_url: str) -> Dict:
        """Extract and classify all links."""
        internal_links = []
        external_links = []
        
        parsed_base = urlparse(page_url)
        base_domain = parsed_base.netloc
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            absolute_url = urljoin(page_url, href)
            parsed_link = urlparse(absolute_url)
            
            link_data = {
                'text': link.get_text(strip=True),
                'href': href,
                'absolute_url': absolute_url,
                'title': link.get('title', ''),
                'rel': link.get('rel', []),
                'target': link.get('target', '')
            }
            
            if parsed_link.netloc == base_domain or parsed_link.netloc == '':
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
    
    def _analyze_seo(self, soup: BeautifulSoup, text_content: str) -> Dict:
        """Perform SEO analysis."""
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
            
            key = name or property_attr
            if key:
                meta_tags[key] = content
        
        # Open Graph tags
        og_tags = {meta.get('property', '').replace('og:', ''): meta.get('content', '')
                   for meta in soup.find_all('meta', property=re.compile(r'^og:'))}
        
        # Twitter Card tags
        twitter_tags = {meta.get('name', '').replace('twitter:', ''): meta.get('content', '')
                       for meta in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})}
        
        # Keyword density
        words = re.findall(r'\b\w+\b', text_content.lower())
        word_count = len(words)
        word_freq = Counter(words)
        
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        keywords = {word: count for word, count in word_freq.most_common(20) 
                   if word not in stop_words and len(word) > 2}
        
        keyword_density = {word: round((count / word_count) * 100, 2) 
                          for word, count in keywords.items()} if word_count > 0 else {}
        
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
    
    def _analyze_structure(self, soup: BeautifulSoup) -> Dict:
        """Analyze HTML structure."""
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
        
        semantic_elements = ['header', 'footer', 'nav', 'main', 'article', 
                            'aside', 'section', 'figure', 'figcaption']
        structure['semantic_elements_used'] = [elem for elem in semantic_elements 
                                               if soup.find(elem)]
        
        return structure

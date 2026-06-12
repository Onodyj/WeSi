"""
Unit tests for WeSi crawler and analyzer.
"""
import unittest
from we_si.crawler import WebsiteCrawler
from we_si.analyzer import PageAnalyzer


class TestCrawler(unittest.TestCase):
    """Test cases for WebsiteCrawler."""
    
    def test_url_normalization(self):
        """Test URL normalization."""
        crawler = WebsiteCrawler("https://example.com")
        
        # Test fragment removal
        self.assertEqual(
            crawler.normalize_url("https://example.com/page#section"),
            "https://example.com/page"
        )
        
        # Test trailing slash removal
        self.assertEqual(
            crawler.normalize_url("https://example.com/page/"),
            "https://example.com/page"
        )
        
        # Test case normalization for domain
        self.assertEqual(
            crawler.normalize_url("https://Example.COM/page"),
            "https://example.com/page"
        )
        
        # Test root path
        self.assertEqual(
            crawler.normalize_url("https://example.com"),
            "https://example.com/"
        )
    
    def test_is_internal_url(self):
        """Test internal URL detection."""
        crawler = WebsiteCrawler("https://example.com")
        
        self.assertTrue(crawler.is_internal_url("https://example.com/page"))
        self.assertTrue(crawler.is_internal_url("/page"))
        self.assertFalse(crawler.is_internal_url("https://other.com/page"))
    
    def test_is_valid_url(self):
        """Test URL validation."""
        crawler = WebsiteCrawler("https://example.com")
        
        # Valid URLs
        self.assertTrue(crawler.is_valid_url("https://example.com/page"))
        self.assertTrue(crawler.is_valid_url("/page"))
        
        # Invalid URLs
        self.assertFalse(crawler.is_valid_url(""))
        self.assertFalse(crawler.is_valid_url("javascript:void(0)"))
        self.assertFalse(crawler.is_valid_url("mailto:test@example.com"))
        self.assertFalse(crawler.is_valid_url("https://example.com/image.jpg"))
        self.assertFalse(crawler.is_valid_url("https://example.com/file.pdf"))


class TestAnalyzer(unittest.TestCase):
    """Test cases for PageAnalyzer."""
    
    def test_cms_detection_wordpress(self):
        """Test WordPress detection."""
        analyzer = PageAnalyzer()
        
        html = '''
        <html>
        <head>
            <meta name="generator" content="WordPress 6.0">
            <script src="/wp-content/themes/test.js"></script>
        </head>
        <body class="wp-page">Content</body>
        </html>
        '''
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        result = analyzer.detect_cms(soup, html)
        self.assertIn('wordpress', result['detected'])
        self.assertEqual(result['probable'], 'wordpress')
    
    def test_cms_detection_squarespace(self):
        """Test Squarespace detection."""
        analyzer = PageAnalyzer()
        
        html = '''
        <html>
        <head>
            <meta name="generator" content="Squarespace">
            <script src="/universal/scripts-compressed/main.js"></script>
        </head>
        <body class="sqs-site">Content</body>
        </html>
        '''
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        result = analyzer.detect_cms(soup, html)
        self.assertIn('squarespace', result['detected'])
        self.assertEqual(result['probable'], 'squarespace')
    
    def test_structured_data_extraction(self):
        """Test JSON-LD extraction."""
        analyzer = PageAnalyzer()
        
        html = '''
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Test Org"
            }
            </script>
        </head>
        <body>Content</body>
        </html>
        '''
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        result = analyzer.extract_structured_data(soup)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['@type'], 'Organization')
        self.assertEqual(result[0]['name'], 'Test Org')
    
    def test_accessibility_analysis(self):
        """Test accessibility analysis."""
        analyzer = PageAnalyzer()
        
        html = '''
        <html>
        <body>
            <img src="test.jpg" alt="Test image">
            <img src="test2.jpg">
        </body>
        </html>
        '''
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        images = [
            {'has_alt': True},
            {'has_alt': False}
        ]
        
        result = analyzer.analyze_accessibility(soup, images)
        self.assertIn('1 image(s) missing alt text', result['issues'])
    
    def test_suggestion_generation(self):
        """Test suggestion generation."""
        analyzer = PageAnalyzer()
        
        analysis = {
            'seo': {
                'has_title': False,
                'has_meta_description': True,
                'word_count': 250
            },
            'headings': {
                'h1_count': 0
            },
            'images': {
                'missing_alt_count': 0
            }
        }
        
        cms = {'probable': 'squarespace'}
        
        suggestions = analyzer.generate_suggestions(analysis, cms)
        
        # Should have suggestions for missing title and H1
        self.assertTrue(any('title' in s['issue'].lower() for s in suggestions))
        self.assertTrue(any('h1' in s['issue'].lower() for s in suggestions))
        
        # Should have platform help for Squarespace
        title_suggestion = next(s for s in suggestions if 'title' in s['issue'].lower())
        self.assertIn('platform_help', title_suggestion)
        self.assertIn('Squarespace', title_suggestion['platform_help'])


class TestSecretManager(unittest.TestCase):
    """Test cases for SecretManager."""
    
    def test_encryption_decryption(self):
        """Test encrypt and decrypt."""
        from we_si.storage.secrets import SecretManager
        from cryptography.fernet import Fernet
        
        key = Fernet.generate_key()
        manager = SecretManager(key.decode())
        
        plaintext = "sk-test-api-key-12345"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        
        self.assertEqual(plaintext, decrypted)
        self.assertNotEqual(plaintext, encrypted.decode('utf-8', errors='ignore'))
    
    def test_generate_key(self):
        """Test key generation."""
        from we_si.storage.secrets import SecretManager
        
        key = SecretManager.generate_key()
        
        # Should be a valid base64 string
        self.assertIsInstance(key, str)
        self.assertTrue(len(key) > 0)
        
        # Should be able to create a manager with it
        manager = SecretManager(key)
        self.assertIsNotNone(manager)


class TestReportGenerators(unittest.TestCase):
    """Test cases for report generators."""
    
    def setUp(self):
        """Set up test data."""
        self.test_data = {
            'metadata': {
                'base_url': 'https://example.com',
                'domain': 'example.com',
                'analysis_date': '2024-01-01 12:00:00',
                'pages_crawled': 5
            },
            'summary': {
                'total_pages_analyzed': 5,
                'total_images': 10,
                'images_without_alt': 2,
                'total_internal_links': 25,
                'total_external_links': 5,
                'broken_links_found': 1,
                'avg_word_count': 350
            },
            'insights': {
                'critical': ['Missing title on 1 page'],
                'warnings': ['2 images without alt text'],
                'recommendations': ['Add more content'],
                'positive': ['Good average word count']
            },
            'pages': []
        }
    
    def test_html_report_generation(self):
        """Test HTML report generation."""
        from we_si.reports.html_report import HTMLReportGenerator
        
        generator = HTMLReportGenerator()
        html = generator.generate(self.test_data)
        
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('example.com', html)
        self.assertIn('Missing title on 1 page', html)
        self.assertIn('Executive Summary', html)
    
    def test_text_report_generation(self):
        """Test text report generation."""
        from we_si.reports.text_report import TextReportGenerator
        
        generator = TextReportGenerator()
        text = generator.generate(self.test_data)
        
        self.assertIn('WEBSITE ANALYSIS REPORT', text)
        self.assertIn('example.com', text)
        self.assertIn('Missing title on 1 page', text)
        self.assertIn('EXECUTIVE SUMMARY', text)
    
    def test_email_summary_generation(self):
        """Test email summary generation."""
        from we_si.reports.text_report import TextReportGenerator
        
        generator = TextReportGenerator()
        email = generator.generate_email_summary(self.test_data)
        
        self.assertIn('example.com', email)
        self.assertIn('5 pages analyzed', email)
        self.assertIn('critical issue', email.lower())


if __name__ == '__main__':
    unittest.main()

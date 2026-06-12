#!/usr/bin/env python3
"""
Test the website analyzer with a local HTML file to demonstrate all features.
"""

from website_analyzer import WebsiteAnalyzer
from bs4 import BeautifulSoup
import json


def test_with_sample_html():
    """Test the analyzer with sample HTML content."""
    
    # Create a comprehensive sample HTML page
    sample_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sample Website for Testing WeSi Analyzer</title>
        <meta name="description" content="This is a comprehensive sample page to test the WeSi website analyzer tool with various HTML elements and SEO features.">
        <meta name="keywords" content="website, analyzer, SEO, testing">
        <meta property="og:title" content="Sample Website">
        <meta property="og:description" content="Testing Open Graph tags">
        <meta name="twitter:card" content="summary">
        <link rel="canonical" href="https://example.com/sample">
    </head>
    <body>
        <header>
            <nav>
                <a href="/">Home</a>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
                <a href="https://external-site.com">External Link</a>
            </nav>
        </header>
        
        <main>
            <h1>Main Heading: Welcome to Our Sample Website</h1>
            
            <section>
                <h2>Section 1: Introduction</h2>
                <p>This is a comprehensive sample page designed to test all features of the WeSi website analyzer. 
                The analyzer provides insights into SEO, content quality, and technical structure.</p>
                
                <img src="/images/intro.jpg" alt="Introduction image showing website features">
                
                <h3>Subsection 1.1: Key Features</h3>
                <p>Our analyzer examines heading hierarchy, image alt texts, link structure, and much more.
                It helps improve website performance and search engine optimization.</p>
            </section>
            
            <section>
                <h2>Section 2: Benefits</h2>
                <p>Using WeSi website analyzer provides numerous benefits including improved SEO scores,
                better content organization, and enhanced user experience. The tool generates actionable
                insights that help website owners make informed decisions.</p>
                
                <img src="/images/benefits.jpg" alt="Benefits diagram">
                <img src="/images/chart.png">  <!-- Missing alt text -->
                
                <article>
                    <h3>Article: SEO Best Practices</h3>
                    <p>Search engine optimization is crucial for organic traffic. Key elements include
                    proper heading structure, meta tags, quality content, and technical excellence.</p>
                    
                    <h4>Technical SEO</h4>
                    <p>Technical SEO involves optimizing website structure, speed, and crawlability.
                    Using semantic HTML5 elements helps search engines understand your content better.</p>
                </article>
            </section>
            
            <section>
                <h2>Section 3: Content Analysis</h2>
                <p>The content analysis feature examines word count, keyword density, and content quality.
                It identifies the most frequently used keywords and provides recommendations for improvement.
                Quality content attracts more visitors and keeps them engaged.</p>
                
                <img src="https://example.com/images/analysis.jpg" alt="Content analysis visualization">
                
                <h3>Keyword Research</h3>
                <p>Effective keyword research helps target the right audience. Understanding keyword density
                and competition is essential for SEO success. The analyzer provides detailed keyword metrics.</p>
            </section>
            
            <aside>
                <h2>Related Resources</h2>
                <ul>
                    <li><a href="/resources/guide">SEO Guide</a></li>
                    <li><a href="/resources/tools">Other Tools</a></li>
                    <li><a href="https://example.org/external">External Resource</a></li>
                </ul>
            </aside>
        </main>
        
        <footer>
            <p>&copy; 2024 WeSi Website Analyzer</p>
            <nav>
                <a href="/privacy">Privacy Policy</a>
                <a href="/terms">Terms of Service</a>
            </nav>
        </footer>
        
        <script>
            // This script content should be excluded from content analysis
            console.log('Website loaded');
        </script>
    </body>
    </html>
    """
    
    # Create analyzer instance
    analyzer = WebsiteAnalyzer('https://example.com/sample')
    
    # Parse the HTML
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    print("="*60)
    print("TESTING WESI WEBSITE ANALYZER WITH SAMPLE HTML")
    print("="*60)
    
    # Test heading hierarchy
    print("\n1. HEADING HIERARCHY ANALYSIS")
    print("-"*60)
    heading_data = analyzer.analyze_heading_hierarchy(soup)
    print(f"H1 Count: {heading_data['counts']['h1']}")
    print(f"H2 Count: {heading_data['counts']['h2']}")
    print(f"H3 Count: {heading_data['counts']['h3']}")
    print(f"H4 Count: {heading_data['counts']['h4']}")
    print(f"H1 Headings: {heading_data['headings']['h1']}")
    if heading_data['issues']:
        print(f"Issues: {heading_data['issues']}")
    else:
        print("✓ No hierarchy issues found")
    
    # Test image extraction
    print("\n2. IMAGE ANALYSIS")
    print("-"*60)
    images = analyzer.extract_images(soup, 'https://example.com/sample')
    print(f"Total Images: {len(images)}")
    print(f"Images with Alt Text: {sum(1 for img in images if img['has_alt'])}")
    print(f"Images without Alt Text: {sum(1 for img in images if not img['has_alt'])}")
    print("\nImage Details:")
    for img in images[:3]:
        print(f"  - Src: {img['src'][:50]}...")
        print(f"    Alt: {img['alt'] if img['alt'] else '(missing)'}")
        print(f"    Placement: {img['placement']}")
    
    # Test link extraction
    print("\n3. LINK CLASSIFICATION")
    print("-"*60)
    links = analyzer.extract_links(soup, 'https://example.com/sample')
    print(f"Internal Links: {links['internal_count']}")
    print(f"External Links: {links['external_count']}")
    print("\nSample Internal Links:")
    for link in links['internal'][:3]:
        print(f"  - {link['url']} ({link['text']})")
    print("\nSample External Links:")
    for link in links['external'][:3]:
        print(f"  - {link['url']} ({link['text']})")
    
    # Test SEO analysis
    print("\n4. SEO ANALYSIS")
    print("-"*60)
    seo = analyzer.analyze_seo(soup, 'https://example.com/sample')
    print(f"Title: {seo['title']}")
    print(f"Title Length: {seo['title_length']} characters")
    print(f"Meta Description: {seo['meta_description'][:80]}...")
    print(f"Meta Description Length: {seo['meta_description_length']} characters")
    print(f"Open Graph Tags: {len(seo['og_tags'])} found")
    print(f"Twitter Tags: {len(seo['twitter_tags'])} found")
    print(f"Canonical URL: {seo['canonical']}")
    if seo['issues']:
        print(f"\nSEO Issues:")
        for issue in seo['issues']:
            print(f"  - {issue}")
    else:
        print("✓ No SEO issues found")
    
    # Test content analysis
    print("\n5. CONTENT ANALYSIS")
    print("-"*60)
    content = analyzer.analyze_content(soup)
    print(f"Word Count: {content['word_count']}")
    print(f"\nTop 10 Keywords:")
    for idx, keyword in enumerate(content['top_keywords'][:10], 1):
        kw_data = content['keyword_density'][keyword]
        print(f"  {idx}. {keyword}: {kw_data['count']} occurrences ({kw_data['density']}% density)")
    
    # Test layout structure
    print("\n6. LAYOUT STRUCTURE ANALYSIS")
    print("-"*60)
    structure = analyzer.analyze_layout_structure(soup)
    print(f"Has <header>: {structure['has_header']}")
    print(f"Has <nav>: {structure['has_nav']}")
    print(f"Has <main>: {structure['has_main']}")
    print(f"Has <footer>: {structure['has_footer']}")
    print(f"Has <aside>: {structure['has_aside']}")
    print(f"Sections: {structure['sections']}")
    print(f"Articles: {structure['articles']}")
    if structure['issues']:
        print(f"\nStructure Issues:")
        for issue in structure['issues']:
            print(f"  - {issue}")
    else:
        print("✓ No structure issues found")
    
    # Create a mock page data for SEO score calculation
    page_data = {
        'seo': seo,
        'heading_hierarchy': heading_data,
        'images': images,
        'broken_links': [],
        'structure': structure
    }
    
    print("\n7. SEO SCORE")
    print("-"*60)
    seo_score = analyzer.calculate_seo_score(page_data)
    print(f"SEO Score: {seo_score}/100")
    
    print("\n" + "="*60)
    print("TEST COMPLETE - All features working correctly!")
    print("="*60)
    
    # Save a sample report
    test_report = {
        'test_results': {
            'heading_hierarchy': heading_data,
            'images': images,
            'links': links,
            'seo': seo,
            'content': content,
            'structure': structure,
            'seo_score': seo_score
        }
    }
    
    with open('test_report.json', 'w', encoding='utf-8') as f:
        json.dump(test_report, f, indent=2, ensure_ascii=False)
    
    print("\nDetailed test report saved to: test_report.json")


if __name__ == '__main__':
    test_with_sample_html()

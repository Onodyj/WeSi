#!/usr/bin/env python3
"""
Example usage of the WeSi Website Analyzer
"""

from wesi import WebsiteAnalyzer
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    # Example 1: Basic usage with default settings
    print("Example 1: Basic Analysis")
    print("-" * 50)
    analyzer = WebsiteAnalyzer("https://example.com", max_pages=5, delay=0.5)
    analyzer.crawl()
    report = analyzer.generate_report()
    analyzer.save_report("example_basic_report.json")
    print("✅ Basic analysis complete\n")

    # Example 2: Analyzing a specific page
    print("Example 2: Single Page Analysis")
    print("-" * 50)
    analyzer2 = WebsiteAnalyzer("https://example.com", max_pages=1, delay=0.5)
    page_data = analyzer2.analyze_page("https://example.com")

    print(f"Page: {page_data['url']}")
    print(f"Status: {page_data['status_code']}")
    if 'error' not in page_data:
        print(f"Word Count: {page_data['seo']['word_count']}")
        print(f"Images: {page_data['images']['count']}")
        print(f"Images without alt: {page_data['images']['missing_alt_count']}")
        print(f"Internal Links: {page_data['links']['total_internal']}")
        print(f"External Links: {page_data['links']['total_external']}")
        print(f"H1 Tags: {page_data['headings']['counts']['h1']}")
    print()

    # Example 3: Custom analysis with insights
    print("Example 3: Detailed Analysis with Insights")
    print("-" * 50)
    analyzer3 = WebsiteAnalyzer("https://example.com", max_pages=10, delay=0.5)
    analyzer3.crawl()
    report3 = analyzer3.generate_report()

    # Display insights
    insights = report3['insights']
    print("\n📊 INSIGHTS SUMMARY:")
    print(f"Critical Issues: {len(insights['critical'])}")
    print(f"Warnings: {len(insights['warnings'])}")
    print(f"Recommendations: {len(insights['recommendations'])}")
    print(f"Positive Findings: {len(insights['positive'])}")

    # Display summary statistics
    summary = report3['summary']
    print("\n📈 STATISTICS:")
    print(f"Pages Analyzed: {summary['total_pages_analyzed']}")
    print(f"Total Images: {summary['total_images']}")
    print(f"Average Word Count: {summary['avg_word_count']}")

    analyzer3.save_report("example_detailed_report.json")
    print("\n✅ Detailed analysis complete\n")

    # Example 4: Accessing specific page data
    print("Example 4: Working with Page Data")
    print("-" * 50)
    if report3['pages']:
        first_page = report3['pages'][0]
        
        if 'error' not in first_page:
            # SEO data
            print(f"\nSEO Analysis for {first_page['url']}:")
            print(f"  Title: {first_page['seo']['title']}")
            print(f"  Title Length: {first_page['seo']['title_length']} chars")
            print(f"  Meta Description: {first_page['seo']['meta_description'][:50]}...")
            print(f"  Description Length: {first_page['seo']['meta_description_length']} chars")
            
            # Top keywords
            print(f"\n  Top 5 Keywords:")
            for idx, (word, count) in enumerate(list(first_page['seo']['top_keywords'].items())[:5], 1):
                density = first_page['seo']['keyword_density'][word]
                print(f"    {idx}. {word}: {count} times ({density}%)")
            
            # Structure
            print(f"\n  HTML Structure:")
            print(f"    Has Header: {first_page['structure']['has_header']}")
            print(f"    Has Footer: {first_page['structure']['has_footer']}")
            print(f"    Has Nav: {first_page['structure']['has_nav']}")
            print(f"    Has Main: {first_page['structure']['has_main']}")
            print(f"    Semantic Elements: {', '.join(first_page['structure']['semantic_elements_used'])}")

    print("\n" + "=" * 50)
    print("All examples completed!")
    print("=" * 50)

except Exception as e:
    logging.error(f"Error during example execution: {e}", exc_info=True)
    print(f"\n❌ Error: {e}")
    import sys
    sys.exit(1)

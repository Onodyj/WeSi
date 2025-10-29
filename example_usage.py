#!/usr/bin/env python3
"""
Example usage of the WeSi Website Analyzer
"""

from wesi import WebsiteAnalyzer
import json

# Example 1: Basic usage with default settings
print("Example 1: Basic Analysis")
print("-" * 50)
try:
    analyzer = WebsiteAnalyzer("https://example.com", max_pages=5)
    analyzer.crawl()
    report = analyzer.generate_report()
    analyzer.save_report("example_basic_report.json")
    print("✅ Basic analysis complete\n")
except Exception as e:
    print(f"❌ Error in Example 1: {e}\n")

# Example 2: Analyzing a specific page
print("Example 2: Single Page Analysis")
print("-" * 50)
try:
    analyzer2 = WebsiteAnalyzer("https://example.com", max_pages=1)
    page_data = analyzer2.analyze_page("https://example.com")

    print(f"Page: {page_data['url']}")
    print(f"Status: {page_data['status_code']}")
    
    # Check if page was successfully fetched
    if page_data.get('error'):
        print(f"Error: {page_data['error']}")
    else:
        print(f"Word Count: {page_data['seo']['word_count']}")
        print(f"Images: {page_data['images']['count']}")
        print(f"Images without alt: {page_data['images']['missing_alt_count']}")
        print(f"Internal Links: {page_data['links']['total_internal']}")
        print(f"External Links: {page_data['links']['total_external']}")
        print(f"H1 Tags: {page_data['headings']['counts']['h1']}")
    print()
except Exception as e:
    print(f"❌ Error in Example 2: {e}\n")

# Example 3: Custom analysis with insights
print("Example 3: Detailed Analysis with Insights")
print("-" * 50)
try:
    analyzer3 = WebsiteAnalyzer("https://example.com", max_pages=10)
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
except Exception as e:
    print(f"❌ Error in Example 3: {e}\n")

# Example 4: Accessing specific page data
print("Example 4: Working with Page Data")
print("-" * 50)
try:
    analyzer4 = WebsiteAnalyzer("https://example.com", max_pages=5)
    analyzer4.crawl()
    report4 = analyzer4.generate_report()
    
    if report4['pages']:
        first_page = report4['pages'][0]
        
        # Check if page was successfully analyzed
        if first_page.get('error'):
            print(f"❌ First page failed to analyze: {first_page['error']}")
        else:
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
    else:
        print("❌ No pages were analyzed successfully")
except Exception as e:
    print(f"❌ Error in Example 4: {e}")

print("\n" + "=" * 50)
print("All examples completed!")
print("=" * 50)

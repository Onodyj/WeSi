#!/usr/bin/env python3
"""
Example usage of the WeSi Website Analyzer
Demonstrates how to use the analyzer programmatically.
"""

from website_analyzer import WebsiteAnalyzer
import json


def main():
    """Example of using the website analyzer programmatically."""
    
    # Example 1: Basic usage
    print("Example 1: Basic Website Analysis")
    print("-" * 50)
    
    analyzer = WebsiteAnalyzer('https://example.com', timeout=10)
    results = analyzer.analyze()
    
    # Print some key metrics
    if results['summary']:
        print(f"SEO Score: {results['summary']['seo_score']}/100")
        print(f"Total Images: {results['summary']['total_images']}")
        print(f"Images Without Alt: {results['summary']['images_without_alt']}")
        print(f"Broken Links: {results['summary']['broken_links']}")
    
    # Save report
    analyzer.save_report('example_report.json')
    
    print("\n" + "=" * 50)
    print("Example 2: Analyzing Specific Page Elements")
    print("-" * 50)
    
    if results['pages']:
        page = results['pages'][0]
        
        if page['status'] == 'success':
            # Show heading structure
            print("\nHeading Structure:")
            for level in ['h1', 'h2', 'h3']:
                headings = page['heading_hierarchy']['headings'][level]
                if headings:
                    print(f"  {level.upper()}: {headings[:3]}")  # Show first 3
            
            # Show top keywords
            print("\nTop Keywords:")
            for keyword in page['content']['top_keywords'][:5]:
                density = page['content']['keyword_density'][keyword]
                print(f"  - {keyword}: {density['count']} occurrences ({density['density']}%)")
            
            # Show SEO issues
            if page['seo']['issues']:
                print("\nSEO Issues:")
                for issue in page['seo']['issues']:
                    print(f"  - {issue}")
    
    print("\n" + "=" * 50)
    print("Example 3: Recommendations")
    print("-" * 50)
    
    for idx, recommendation in enumerate(results['recommendations'][:5], 1):
        print(f"{idx}. {recommendation}")
    
    print("\n" + "=" * 50)
    print("Analysis complete! Check example_report.json for full details.")


if __name__ == '__main__':
    main()

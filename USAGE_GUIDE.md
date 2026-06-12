# WeSi Usage Guide

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Onodyj/WeSi.git
cd WeSi

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

Analyze any website with a single command:

```bash
python website_analyzer.py https://yourwebsite.com
```

The tool will generate a comprehensive JSON report named `website_analysis_report.json` with detailed insights.

## Command Line Options

```bash
# Analyze with custom output file
python website_analyzer.py https://example.com -o my_report.json

# Adjust request timeout (useful for slow websites)
python website_analyzer.py https://example.com -t 30

# Set maximum crawl depth
python website_analyzer.py https://example.com -d 5
```

## Programmatic Usage

You can also use WeSi as a Python library:

```python
from website_analyzer import WebsiteAnalyzer

# Create analyzer instance
analyzer = WebsiteAnalyzer('https://yourwebsite.com')

# Run analysis
results = analyzer.analyze()

# Access specific results
seo_score = results['summary']['seo_score']
print(f"SEO Score: {seo_score}/100")

# Save to custom location
analyzer.save_report('custom_output.json')
```

## What Does It Analyze?

### 1. Heading Hierarchy (H1-H6)

The tool examines all heading tags and identifies:
- Missing H1 tags (critical for SEO)
- Multiple H1 tags (not recommended)
- Hierarchy skips (e.g., H1 → H3 without H2)
- Complete heading structure

**Example Output:**
```json
{
  "heading_hierarchy": {
    "headings": {
      "h1": ["Main Heading: Welcome to Our Website"],
      "h2": ["Section 1", "Section 2", "Section 3"],
      "h3": ["Subsection 1.1", "Subsection 2.1"]
    },
    "counts": {
      "h1": 1,
      "h2": 3,
      "h3": 2
    },
    "issues": []
  }
}
```

### 2. Image Analysis

Comprehensive image metadata extraction:
- Source URLs (resolved to absolute paths)
- Alt text presence and content
- Placement context (header, body, footer, etc.)
- Position in document

**Example Output:**
```json
{
  "images": [
    {
      "src": "https://example.com/images/hero.jpg",
      "alt": "Hero image showing product features",
      "has_alt": true,
      "placement": "header",
      "position": 1
    },
    {
      "src": "https://example.com/images/chart.png",
      "alt": "",
      "has_alt": false,
      "placement": "body",
      "position": 2
    }
  ]
}
```

**Key Insights:**
- Images without alt text hurt accessibility and SEO
- The tool identifies which images need alt text

### 3. Link Classification

Extracts and categorizes all links:
- Internal links (same domain)
- External links (different domains)
- Link text analysis
- Broken link detection

**Example Output:**
```json
{
  "links": {
    "internal": [
      {
        "url": "https://example.com/about",
        "text": "About Us",
        "has_text": true
      }
    ],
    "external": [
      {
        "url": "https://external-site.com",
        "text": "Partner Site",
        "has_text": true
      }
    ],
    "internal_count": 15,
    "external_count": 5
  },
  "broken_links": [
    {
      "url": "https://example.com/old-page",
      "status_code": 404
    }
  ]
}
```

### 4. SEO Analysis

Comprehensive SEO metadata analysis:

#### Title Tag
- Optimal length: 50-60 characters
- Checks for presence and length

#### Meta Description
- Optimal length: 120-160 characters
- Critical for search result click-through rates

#### Open Graph Tags
- For social media sharing
- Facebook, LinkedIn, etc.

#### Twitter Card Tags
- Twitter-specific metadata
- Enhances tweet appearance

#### Canonical URL
- Prevents duplicate content issues

**Example Output:**
```json
{
  "seo": {
    "title": "Professional Web Development Services",
    "title_length": 40,
    "meta_description": "We provide expert web development...",
    "meta_description_length": 145,
    "og_tags": {
      "og:title": "Web Development Services",
      "og:description": "Expert solutions...",
      "og:image": "https://example.com/og-image.jpg"
    },
    "twitter_tags": {
      "twitter:card": "summary_large_image"
    },
    "canonical": "https://example.com/services",
    "issues": []
  }
}
```

### 5. Content Analysis

Keyword density and content metrics:
- Total word count
- Top keywords with frequency
- Keyword density percentages
- Excludes navigation and script content

**Example Output:**
```json
{
  "content": {
    "word_count": 850,
    "keyword_density": {
      "development": {
        "count": 12,
        "density": 1.41
      },
      "services": {
        "count": 10,
        "density": 1.18
      },
      "professional": {
        "count": 8,
        "density": 0.94
      }
    },
    "top_keywords": [
      "development",
      "services",
      "professional",
      "solutions",
      "business"
    ]
  }
}
```

**Key Insights:**
- Keyword density should be natural (typically 1-3%)
- Over-optimization can hurt SEO

### 6. Layout Structure

Semantic HTML5 structure analysis:
- Presence of semantic elements
- Section and article counts
- Structural issues

**Example Output:**
```json
{
  "structure": {
    "has_header": true,
    "has_nav": true,
    "has_main": true,
    "has_footer": true,
    "has_aside": true,
    "sections": 5,
    "articles": 3,
    "issues": []
  }
}
```

### 7. SEO Score

A calculated score (0-100) based on:
- Title tag optimization (15 points)
- Meta description optimization (15 points)
- H1 tag usage (10 points)
- Image alt text coverage (10 points)
- Broken links (up to -20 points)
- Semantic structure (5 points)

**Scoring Breakdown:**
- 90-100: Excellent SEO
- 70-89: Good SEO
- 50-69: Needs improvement
- 0-49: Poor SEO

## Actionable Recommendations

The tool provides specific recommendations such as:
- "Add alt text to 5 images (25% of total) for accessibility and SEO"
- "Add H1 headings to 2 page(s) for better SEO"
- "Fix 3 broken link(s) to improve user experience"
- "Add meta descriptions to improve click-through rates"

## Complete Report Structure

```json
{
  "pages": [
    {
      "url": "https://example.com",
      "status": "success",
      "status_code": 200,
      "heading_hierarchy": {...},
      "images": [...],
      "links": {...},
      "broken_links": [...],
      "seo": {...},
      "content": {...},
      "structure": {...}
    }
  ],
  "summary": {
    "total_pages_analyzed": 1,
    "timestamp": "2024-10-22T12:00:00",
    "base_url": "https://example.com",
    "total_images": 10,
    "images_without_alt": 2,
    "internal_links": 20,
    "external_links": 5,
    "broken_links": 0,
    "word_count": 850,
    "seo_score": 85
  },
  "recommendations": [
    "Add alt text to 2 images (20% of total) for accessibility and SEO",
    "Ensure all pages have unique, descriptive title tags",
    "Use semantic HTML5 elements for better structure",
    ...
  ]
}
```

## Best Practices

### Running Regular Audits
- Run WeSi after major content changes
- Schedule monthly SEO audits
- Compare reports over time to track improvements

### Interpreting Results
1. Start with the SEO score for an overall health check
2. Review recommendations for quick wins
3. Examine broken links and fix immediately
4. Check images without alt text
5. Verify meta tags are optimized
6. Review heading hierarchy

### Improving Your Score
1. **Add missing meta tags** - Quick wins with title and description
2. **Fix broken links** - Improves user experience and SEO
3. **Add alt text to images** - Boosts accessibility and SEO
4. **Use one H1 per page** - Critical for SEO
5. **Implement semantic HTML** - Better for search engines
6. **Optimize content** - Natural keyword usage

## Troubleshooting

### Connection Errors
If you get connection errors:
```bash
# Increase timeout
python website_analyzer.py https://example.com -t 30
```

### Large Websites
For large websites, the tool focuses on the main page to provide actionable insights quickly.

### Rate Limiting
The tool limits link checking to 50 URLs to avoid overwhelming servers. This is sufficient for identifying patterns.

## Examples

### Example 1: Personal Blog
```bash
python website_analyzer.py https://myblog.com -o blog_analysis.json
```

### Example 2: E-commerce Site
```bash
python website_analyzer.py https://mystore.com -o store_seo.json -t 20
```

### Example 3: Corporate Website
```bash
python website_analyzer.py https://company.com -o corporate_audit.json
```

## Contributing

Found a bug or have a feature request? Please open an issue on GitHub!

## Support

For questions or issues, please visit: https://github.com/Onodyj/WeSi/issues

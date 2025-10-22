# WeSi - Website Analyzer

A comprehensive Python tool to analyze and map websites for SEO, structure, and content quality insights.

## Features

- **HTML Structure Analysis**: Parse and identify layout structure using semantic HTML5 elements
- **Heading Hierarchy**: Analyze H1-H6 heading structure and identify hierarchy issues
- **Image Analysis**: Extract all images with src, alt text, and placement information
- **Link Classification**: Extract and classify internal/external links
- **Broken Link Detection**: Audit links for broken URLs and connection issues
- **SEO Analysis**: Comprehensive analysis of meta tags, title tags, and keyword density
- **Content Analysis**: Word count and keyword density calculation
- **JSON Report Generation**: Structured output with actionable insights
- **SEO Score**: Calculate a score (0-100) based on best practices

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Onodyj/WeSi.git
cd WeSi
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Analyze a website:
```bash
python website_analyzer.py https://example.com
```

### Advanced Options

```bash
python website_analyzer.py https://example.com --output my_report.json --timeout 20
```

### Command Line Options

- `url`: Website URL to analyze (required)
- `-o, --output`: Output JSON file (default: website_analysis_report.json)
- `-d, --max-depth`: Maximum crawl depth (default: 3)
- `-t, --timeout`: Request timeout in seconds (default: 10)

### Example

```bash
python website_analyzer.py https://example.com -o example_report.json
```

## Output Structure

The tool generates a comprehensive JSON report with the following structure:

```json
{
  "pages": [
    {
      "url": "https://example.com",
      "status": "success",
      "status_code": 200,
      "heading_hierarchy": {
        "headings": {
          "h1": ["Main Title"],
          "h2": ["Section 1", "Section 2"],
          ...
        },
        "counts": {"h1": 1, "h2": 2, ...},
        "issues": []
      },
      "images": [
        {
          "src": "https://example.com/image.jpg",
          "alt": "Image description",
          "has_alt": true,
          "placement": "body",
          "position": 1
        }
      ],
      "links": {
        "internal": [...],
        "external": [...],
        "internal_count": 10,
        "external_count": 5
      },
      "broken_links": [...],
      "seo": {
        "title": "Page Title",
        "title_length": 50,
        "meta_description": "Description...",
        "meta_description_length": 150,
        "og_tags": {...},
        "twitter_tags": {...},
        "issues": []
      },
      "content": {
        "word_count": 500,
        "keyword_density": {...},
        "top_keywords": [...]
      },
      "structure": {
        "has_header": true,
        "has_nav": true,
        "has_main": true,
        "has_footer": true,
        "issues": []
      }
    }
  ],
  "summary": {
    "total_pages_analyzed": 1,
    "total_images": 10,
    "images_without_alt": 2,
    "internal_links": 10,
    "external_links": 5,
    "broken_links": 0,
    "word_count": 500,
    "seo_score": 85
  },
  "recommendations": [
    "Add alt text to 2 images (20.0% of total) for accessibility and SEO.",
    "Ensure all pages have unique, descriptive title tags (50-60 characters).",
    ...
  ]
}
```

## Features in Detail

### 1. Heading Hierarchy Analysis
- Detects all H1-H6 headings
- Identifies missing H1 tags
- Detects multiple H1 tags (SEO issue)
- Checks for hierarchy skips (e.g., H1 to H3 without H2)

### 2. Image Analysis
- Extracts image source URLs (absolute paths)
- Checks for alt text presence
- Identifies image placement (header, body, footer, etc.)
- Provides position index

### 3. Link Classification
- Separates internal and external links
- Resolves relative URLs to absolute
- Checks for link text presence
- Counts links by type

### 4. Broken Link Detection
- Tests link accessibility
- Reports HTTP status codes
- Identifies connection failures
- Limits checks to avoid excessive requests

### 5. SEO Analysis
- **Title Tag**: Length check (optimal 50-60 characters)
- **Meta Description**: Length check (optimal 120-160 characters)
- **Meta Keywords**: Extraction (if present)
- **Open Graph Tags**: Social media metadata
- **Twitter Card Tags**: Twitter-specific metadata
- **Canonical URL**: Duplicate content prevention
- **Robots Meta Tag**: Crawling directives

### 6. Content Analysis
- Total word count
- Keyword density calculation
- Top 20 most frequent keywords
- Excludes script, style, nav, header, and footer content

### 7. Layout Structure
- Checks for semantic HTML5 elements
- Detects header, nav, main, footer, aside
- Counts sections and articles
- Identifies structural issues

### 8. SEO Score Calculation
Calculates a score (0-100) based on:
- Title tag presence and length
- Meta description presence and length
- H1 tag usage (one per page)
- Image alt text coverage
- Broken links count
- Semantic HTML structure

## Recommendations

The tool provides actionable recommendations to:
- Improve site architecture
- Enhance content quality
- Increase technical SEO
- Boost organic traffic and engagement
- Improve accessibility

## Requirements

- Python 3.7+
- requests >= 2.31.0
- beautifulsoup4 >= 4.12.0
- lxml >= 4.9.0

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

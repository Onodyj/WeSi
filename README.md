# WeSi - Website Analyzer

A comprehensive Python tool to map, analyze, and audit websites for structure, content quality, and SEO optimization.

## Features

WeSi provides detailed analysis of your website including:

### 🏗️ Structure Analysis
- **HTML Layout Structure**: Identifies semantic HTML5 elements (header, nav, main, article, aside, footer)
- **Heading Hierarchy**: Complete H1-H6 analysis with proper hierarchy validation
- **Element Counts**: Tracks usage of sections, divs, forms, tables, and lists

### 📝 Content Analysis
- **Body Copy Extraction**: Extracts and analyzes all visible text content
- **Word Count**: Measures content depth on each page
- **Keyword Density**: Identifies top keywords and their frequency
- **Text Quality**: Evaluates content depth and provides recommendations

### 🖼️ Image Analysis
- **Complete Image Inventory**: Catalogs all images with:
  - Source URLs (relative and absolute)
  - Alt text validation
  - Title attributes
  - Dimensions (width/height)
  - Placement context (parent element, header/footer/nav/article)
  - Loading attributes
  - CSS classes
- **Accessibility Audit**: Identifies images missing alt text

### 🔗 Link Analysis
- **Link Classification**:
  - Internal links (same domain)
  - External links (other domains)
- **Link Details**: Captures text, href, title, rel attributes, and target
- **Broken Link Detection**: Tests links and reports HTTP status codes
- **Link Auditing**: Identifies connection failures and 404 errors

### 🎯 SEO Analysis
- **Meta Tags**: Analyzes all meta tags including:
  - Title tags (with length validation)
  - Meta descriptions (with optimal length checking)
  - Meta keywords
  - Robots directives
  - Canonical URLs
- **Open Graph**: Extracts og: tags for social media
- **Twitter Cards**: Captures twitter: meta tags
- **Language Detection**: Identifies page language
- **Keyword Analysis**: Top keywords with density percentages
- **SEO Validation**: Checks for optimal title and description lengths

### 💡 Actionable Insights
The tool generates categorized insights:
- **Critical Issues**: Must-fix problems (missing titles, broken links)
- **Warnings**: Important improvements (missing meta descriptions, multiple H1s)
- **Recommendations**: Best practice suggestions (semantic HTML, content depth)
- **Positive Findings**: What you're doing well

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

Analyze a website with default settings (max 50 pages):
```bash
python wesi.py https://example.com
```

### Custom Options

Specify maximum pages and custom output file:
```bash
python wesi.py https://example.com 10 my_report.json
```

### Command Line Arguments

```
python wesi.py <website_url> [max_pages] [output_file]

Arguments:
  website_url  - The URL of the website to analyze (required)
  max_pages    - Maximum number of pages to crawl (default: 50)
  output_file  - Output JSON file name (default: website_analysis.json)
```

## Output

The tool generates a comprehensive JSON report with the following structure:

### Report Structure

```json
{
  "metadata": {
    "base_url": "https://example.com",
    "domain": "example.com",
    "analysis_date": "2024-01-01 12:00:00",
    "pages_crawled": 5
  },
  "summary": {
    "total_pages_analyzed": 5,
    "total_images": 15,
    "images_without_alt": 3,
    "total_internal_links": 42,
    "total_external_links": 8,
    "broken_links_found": 2,
    "avg_word_count": 487
  },
  "insights": {
    "critical": ["List of critical issues"],
    "warnings": ["List of warnings"],
    "recommendations": ["List of recommendations"],
    "positive": ["List of positive findings"]
  },
  "pages": [
    {
      "url": "https://example.com",
      "status_code": 200,
      "structure": { ... },
      "headings": { ... },
      "images": { ... },
      "links": { ... },
      "seo": { ... }
    }
  ]
}
```

### Page-Level Data

Each page in the report includes:
- **URL and Status**: Page URL and HTTP status code
- **Structure**: HTML5 semantic element usage
- **Headings**: Complete H1-H6 hierarchy with text, IDs, and classes
- **Images**: Detailed image inventory with alt text audit
- **Links**: Internal/external link classification
- **Broken Links**: Any broken links found on the page
- **SEO**: Meta tags, title, keywords, and content analysis

## Example Output

When you run the analyzer, you'll see console output like:

```
Starting analysis of https://example.com
Maximum pages to crawl: 10

Analyzing: https://example.com
Analyzing: https://example.com/about
Analyzing: https://example.com/contact
...

======================================================================
ANALYSIS COMPLETE - INSIGHTS
======================================================================

🔴 CRITICAL ISSUES:
  - 2 page(s) missing title tags. Add unique, descriptive titles to all pages.
  - Found 3 potentially broken link(s). Fix or remove broken links.

⚠️  WARNINGS:
  - 5 page(s) missing meta descriptions. Add compelling descriptions (150-160 characters).
  - 8 out of 45 images missing alt text. Add descriptive alt text for accessibility and SEO.

💡 RECOMMENDATIONS:
  - 3 page(s) use limited semantic HTML5 elements. Use <header>, <nav>, <main>, <article>.
  - Average page word count is 250. Consider adding more quality content (aim for 300+ words).

✅ POSITIVE FINDINGS:
  - Good content depth with average 487 words per page.

======================================================================
SUMMARY STATISTICS
======================================================================
Pages analyzed: 10
Total images: 45
Images without alt text: 8
Internal links: 127
External links: 23
Broken links: 3
Average word count: 487

✅ Full detailed report saved to: website_analysis.json
```

## Use Cases

### 1. SEO Audit
- Identify missing or poorly optimized meta tags
- Find pages without proper heading hierarchy
- Discover broken links affecting SEO
- Analyze keyword usage and density

### 2. Content Quality Assessment
- Measure content depth across pages
- Find thin content pages that need expansion
- Identify keyword optimization opportunities
- Ensure consistent content structure

### 3. Accessibility Audit
- Find images missing alt text
- Check semantic HTML usage
- Validate proper heading hierarchy
- Ensure proper HTML structure

### 4. Technical SEO
- Audit title tags and meta descriptions
- Check for duplicate H1 tags
- Validate canonical URLs
- Review robots directives

### 5. Site Architecture Review
- Map internal linking structure
- Identify external link patterns
- Understand site navigation
- Plan site improvements

## Requirements

- Python 3.7+
- beautifulsoup4 4.12.3
- requests 2.31.0
- lxml 5.1.0
- urllib3 2.2.0

## How It Works

1. **Crawling**: Starts from the base URL and follows internal links up to the specified maximum
2. **Parsing**: Uses BeautifulSoup with lxml parser for robust HTML parsing
3. **Analysis**: Performs comprehensive analysis on each page:
   - Structure and semantic HTML
   - Heading hierarchy validation
   - Image cataloging and alt text checking
   - Link extraction and classification
   - SEO element validation
   - Content analysis and keyword extraction
4. **Link Auditing**: Tests a sample of links for broken/dead links
5. **Insight Generation**: Analyzes collected data to generate actionable recommendations
6. **Reporting**: Outputs structured JSON with complete data and insights

## Limitations

- Maximum pages crawled is configurable (default 50) to avoid overloading servers
- Link checking samples links to balance thoroughness with performance
- Respects server load with 0.5-second delay between requests
- Only follows links within the same domain (configurable)
- Requires accessible content (no JavaScript rendering)

## Best Practices

1. **Start Small**: Test with a low page limit first (5-10 pages)
2. **Review Output**: Check the JSON report for detailed page-by-page data
3. **Prioritize Critical Issues**: Address critical findings first
4. **Regular Audits**: Run periodically to track improvements
5. **Respect Robots.txt**: Ensure you have permission to crawl the site

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is available for use under standard open source practices.

## Author

Created for comprehensive website analysis and SEO optimization.

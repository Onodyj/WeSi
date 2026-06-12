# Quick Start Guide

## Installation

```bash
# Clone the repository
git clone https://github.com/Onodyj/WeSi.git
cd WeSi

# Install dependencies
pip install -r requirements.txt
```

## Running Your First Analysis

### Analyze a website with default settings:
```bash
python wesi.py https://yourwebsite.com
```

This will:
- Crawl up to 50 pages
- Generate insights and recommendations
- Save a detailed JSON report as `website_analysis.json`

### Limit the number of pages:
```bash
python wesi.py https://yourwebsite.com 10
```

### Specify a custom output file:
```bash
python wesi.py https://yourwebsite.com 20 my_site_audit.json
```

## Understanding the Output

### Console Output
You'll see real-time progress as pages are analyzed, followed by:

1. **Critical Issues** 🔴 - Must fix immediately
   - Missing title tags
   - Broken links
   
2. **Warnings** ⚠️ - Should fix soon
   - Missing meta descriptions
   - Multiple H1 tags
   - Images without alt text

3. **Recommendations** 💡 - Best practices
   - Use semantic HTML5
   - Improve content depth
   - Add external links

4. **Summary Statistics** 📊
   - Pages analyzed
   - Image count and alt text stats
   - Link statistics
   - Content metrics

### JSON Report
The detailed JSON report contains:

- **Metadata**: Analysis timestamp, domain, pages crawled
- **Summary**: High-level statistics
- **Insights**: Categorized recommendations
- **Pages**: Detailed data for each page including:
  - HTML structure analysis
  - Complete heading hierarchy
  - All images with attributes
  - All links (internal/external)
  - SEO meta tags
  - Keyword analysis

## Common Use Cases

### 1. Pre-Launch SEO Audit
```bash
python wesi.py https://staging.yoursite.com 100 pre_launch_audit.json
```
Check all SEO elements before going live.

### 2. Content Quality Check
```bash
python wesi.py https://yoursite.com/blog 50 blog_audit.json
```
Ensure blog posts have proper structure and metadata.

### 3. Accessibility Audit
Focus on the "Images without alt text" metric in the report.

### 4. Broken Link Check
Review the "broken_links" section in each page's data.

### 5. Competitive Analysis
```bash
python wesi.py https://competitor.com 30 competitor_analysis.json
```
Study competitor site structure and SEO.

## Interpreting Results

### Title Tags
- **Optimal**: 50-60 characters
- **Issue**: Missing or too long/short

### Meta Descriptions
- **Optimal**: 150-160 characters
- **Issue**: Missing or too long/short

### Heading Hierarchy
- **Best Practice**: One H1 per page
- **Issue**: Multiple H1s or missing H1

### Images
- **Best Practice**: All images have descriptive alt text
- **Issue**: Missing alt attributes

### Content Depth
- **Recommended**: 300+ words per page
- **Issue**: Thin content (< 300 words)

### Semantic HTML
- **Best Practice**: Use header, nav, main, article, footer
- **Issue**: Excessive use of generic divs

## Tips for Best Results

1. **Start Small**: Test with 5-10 pages first
2. **Check Robots.txt**: Ensure you're allowed to crawl
3. **Review Critical Issues First**: Address red flags immediately
4. **Track Progress**: Run regularly to measure improvements
5. **Use the JSON**: Integrate data into your workflow

## Troubleshooting

### "Failed to fetch page"
- Check URL is correct and accessible
- Verify you have internet connection
- Website might be blocking automated requests

### Analysis is slow
- Reduce max_pages parameter
- Some sites have slow response times
- Tool includes 0.5s delay to be respectful

### Too many broken links reported
- Some links might be temporarily down
- External sites might have changed
- Review and verify manually

## Next Steps

1. Review the JSON report in detail
2. Prioritize fixes based on impact
3. Implement improvements
4. Re-run analysis to verify changes
5. Set up regular audits (weekly/monthly)

## Getting Help

- Review the full README.md for detailed documentation
- Check example_usage.py for programmatic usage
- Submit issues on GitHub for bugs or feature requests

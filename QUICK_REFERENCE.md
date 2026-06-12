# WeSi Quick Reference

## Installation
```bash
git clone https://github.com/Onodyj/WeSi.git
cd WeSi
pip install -r requirements.txt
```

## Basic Usage
```bash
python website_analyzer.py https://yourwebsite.com
```

## Common Commands
```bash
# Custom output file
python website_analyzer.py https://example.com -o report.json

# Increase timeout for slow sites
python website_analyzer.py https://example.com -t 30

# Run test suite
python test_analyzer.py

# Run example
python example_usage.py
```

## What It Analyzes

| Feature | What It Does |
|---------|--------------|
| **Headings** | H1-H6 hierarchy, counts, issues |
| **Images** | src, alt text, placement |
| **Links** | Internal/external classification |
| **Broken Links** | HTTP status, connectivity |
| **SEO** | Title, meta description, OG tags |
| **Content** | Word count, keyword density |
| **Structure** | Semantic HTML elements |
| **Score** | Overall SEO rating (0-100) |

## Key Outputs

### Summary Metrics
- Total images / images without alt text
- Internal / external link counts
- Broken link count
- Word count
- SEO score

### Recommendations
- Specific, actionable improvements
- Prioritized by impact
- SEO best practices
- Accessibility suggestions

## JSON Report Structure
```
{
  "pages": [{
    "heading_hierarchy": {...},
    "images": [...],
    "links": {...},
    "broken_links": [...],
    "seo": {...},
    "content": {...},
    "structure": {...}
  }],
  "summary": {...},
  "recommendations": [...]
}
```

## SEO Score Guide
- **90-100**: Excellent
- **70-89**: Good
- **50-69**: Needs improvement
- **0-49**: Poor

## Programmatic Usage
```python
from website_analyzer import WebsiteAnalyzer

analyzer = WebsiteAnalyzer('https://example.com')
results = analyzer.analyze()
analyzer.save_report('output.json')

# Access specific data
score = results['summary']['seo_score']
images = results['pages'][0]['images']
```

## Documentation Files

| File | Description |
|------|-------------|
| `README.md` | Overview and features |
| `USAGE_GUIDE.md` | Detailed usage instructions |
| `ADVANCED_EXAMPLES.md` | Integration patterns |
| `IMPLEMENTATION_SUMMARY.md` | Complete feature list |
| `DEMO_OUTPUT.md` | Sample output |
| `QUICK_REFERENCE.md` | This file |

## Common Issues

**Connection timeout?**
```bash
python website_analyzer.py https://site.com -t 30
```

**Want more details?**
Check the generated JSON file for complete analysis.

## Integration Examples

**CI/CD**: Check `ADVANCED_EXAMPLES.md` for GitHub Actions workflow

**Monitoring**: Set up cron jobs for regular audits

**API**: Create Flask wrapper for HTTP API

## Support
GitHub Issues: https://github.com/Onodyj/WeSi/issues

## Quick Tips
1. Run regularly to track improvements
2. Fix broken links immediately
3. Add alt text to all images
4. Keep title tags 50-60 characters
5. Meta descriptions 120-160 characters
6. Use semantic HTML5 elements
7. One H1 per page

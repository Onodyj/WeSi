# Advanced Examples

## Integration Examples

### 1. Batch Analysis Script

Analyze multiple websites and compare results:

```python
#!/usr/bin/env python3
"""
Batch analyze multiple websites and generate comparison report.
"""

from website_analyzer import WebsiteAnalyzer
import json
from datetime import datetime

websites = [
    'https://yoursite.com',
    'https://competitor1.com',
    'https://competitor2.com'
]

results = []

for url in websites:
    print(f"\nAnalyzing {url}...")
    analyzer = WebsiteAnalyzer(url, timeout=15)
    result = analyzer.analyze()
    results.append({
        'url': url,
        'seo_score': result['summary'].get('seo_score', 0),
        'word_count': result['summary'].get('word_count', 0),
        'images_without_alt': result['summary'].get('images_without_alt', 0),
        'broken_links': result['summary'].get('broken_links', 0)
    })

# Save comparison
with open('comparison_report.json', 'w') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'websites': results
    }, f, indent=2)

print("\n" + "="*60)
print("COMPARISON SUMMARY")
print("="*60)
for r in results:
    print(f"\n{r['url']}")
    print(f"  SEO Score: {r['seo_score']}/100")
    print(f"  Word Count: {r['word_count']}")
    print(f"  Images Without Alt: {r['images_without_alt']}")
    print(f"  Broken Links: {r['broken_links']}")
```

### 2. Automated Monitoring

Set up automated SEO monitoring:

```python
#!/usr/bin/env python3
"""
Monitor website SEO health over time.
"""

from website_analyzer import WebsiteAnalyzer
import json
from datetime import datetime
import os

def monitor_website(url, history_file='seo_history.json'):
    """Monitor website and track changes over time."""
    
    # Load history
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
    
    # Analyze current state
    analyzer = WebsiteAnalyzer(url)
    results = analyzer.analyze()
    
    # Add to history
    history.append({
        'timestamp': datetime.now().isoformat(),
        'seo_score': results['summary'].get('seo_score', 0),
        'total_images': results['summary'].get('total_images', 0),
        'images_without_alt': results['summary'].get('images_without_alt', 0),
        'broken_links': results['summary'].get('broken_links', 0),
        'word_count': results['summary'].get('word_count', 0)
    })
    
    # Save history
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    # Check for degradation
    if len(history) > 1:
        previous = history[-2]
        current = history[-1]
        
        print("\n" + "="*60)
        print("CHANGE DETECTION")
        print("="*60)
        
        score_change = current['seo_score'] - previous['seo_score']
        if score_change < 0:
            print(f"⚠️  SEO Score decreased by {abs(score_change)} points")
        elif score_change > 0:
            print(f"✓ SEO Score improved by {score_change} points")
        else:
            print("→ SEO Score unchanged")
        
        broken_change = current['broken_links'] - previous['broken_links']
        if broken_change > 0:
            print(f"⚠️  {broken_change} new broken link(s) detected")
        elif broken_change < 0:
            print(f"✓ {abs(broken_change)} broken link(s) fixed")
    
    return results

# Usage
if __name__ == '__main__':
    monitor_website('https://yourwebsite.com')
```

### 3. CI/CD Integration

Integrate into your deployment pipeline:

```python
#!/usr/bin/env python3
"""
CI/CD integration for SEO quality gate.
"""

from website_analyzer import WebsiteAnalyzer
import sys

def check_seo_quality(url, min_score=70):
    """
    Check if website meets minimum SEO standards.
    Returns exit code 0 if passed, 1 if failed.
    """
    
    analyzer = WebsiteAnalyzer(url)
    results = analyzer.analyze()
    
    score = results['summary'].get('seo_score', 0)
    broken_links = results['summary'].get('broken_links', 0)
    
    print(f"\nSEO Quality Check for {url}")
    print("="*60)
    print(f"SEO Score: {score}/100 (minimum: {min_score})")
    print(f"Broken Links: {broken_links}")
    
    # Quality checks
    passed = True
    
    if score < min_score:
        print(f"❌ FAILED: SEO score {score} is below minimum {min_score}")
        passed = False
    else:
        print(f"✓ PASSED: SEO score meets minimum requirement")
    
    if broken_links > 0:
        print(f"❌ FAILED: {broken_links} broken link(s) found")
        passed = False
    else:
        print("✓ PASSED: No broken links found")
    
    # Check critical issues
    if results['pages']:
        page = results['pages'][0]
        if page['status'] == 'success':
            if not page['seo']['title']:
                print("❌ FAILED: Missing title tag")
                passed = False
            if not page['seo']['meta_description']:
                print("❌ FAILED: Missing meta description")
                passed = False
            if page['heading_hierarchy']['counts']['h1'] == 0:
                print("❌ FAILED: Missing H1 heading")
                passed = False
    
    return 0 if passed else 1

# Usage
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ci_check.py <url> [min_score]")
        sys.exit(1)
    
    url = sys.argv[1]
    min_score = int(sys.argv[2]) if len(sys.argv) > 2 else 70
    
    exit_code = check_seo_quality(url, min_score)
    sys.exit(exit_code)
```

### 4. Generate HTML Report

Convert JSON report to HTML:

```python
#!/usr/bin/env python3
"""
Generate an HTML report from JSON analysis.
"""

import json
from datetime import datetime

def generate_html_report(json_file, output_file='report.html'):
    """Generate HTML report from JSON analysis."""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    recommendations = data.get('recommendations', [])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WeSi Analysis Report</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 10px;
                margin-bottom: 30px;
            }}
            .score {{
                font-size: 72px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .metric-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metric-value {{
                font-size: 36px;
                font-weight: bold;
                color: #667eea;
            }}
            .metric-label {{
                color: #666;
                margin-top: 5px;
            }}
            .recommendations {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .recommendation {{
                padding: 15px;
                margin: 10px 0;
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                border-radius: 4px;
            }}
            h1, h2 {{
                margin: 0 0 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>WeSi Website Analysis Report</h1>
            <p>Generated: {summary.get('timestamp', datetime.now().isoformat())}</p>
            <p>URL: {summary.get('base_url', 'N/A')}</p>
            <div class="score">{summary.get('seo_score', 0)}/100</div>
            <p>SEO Score</p>
        </div>
        
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{summary.get('word_count', 0)}</div>
                <div class="metric-label">Total Words</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('total_images', 0)}</div>
                <div class="metric-label">Total Images</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('images_without_alt', 0)}</div>
                <div class="metric-label">Images Without Alt</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('internal_links', 0)}</div>
                <div class="metric-label">Internal Links</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('external_links', 0)}</div>
                <div class="metric-label">External Links</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{summary.get('broken_links', 0)}</div>
                <div class="metric-label">Broken Links</div>
            </div>
        </div>
        
        <div class="recommendations">
            <h2>Recommendations</h2>
            {"".join(f'<div class="recommendation">{rec}</div>' for rec in recommendations)}
        </div>
    </body>
    </html>
    """
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"HTML report generated: {output_file}")

# Usage
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generate_html.py <json_report>")
        sys.exit(1)
    
    generate_html_report(sys.argv[1])
```

## GitHub Actions Workflow

Add to `.github/workflows/seo-check.yml`:

```yaml
name: SEO Quality Check

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  seo-check:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run SEO Analysis
      run: |
        python website_analyzer.py https://yoursite.com -o seo_report.json
    
    - name: Upload Report
      uses: actions/upload-artifact@v2
      with:
        name: seo-report
        path: seo_report.json
```

## Cron Job for Regular Monitoring

```bash
# Add to crontab (crontab -e)
# Run daily at 2 AM
0 2 * * * cd /path/to/WeSi && python website_analyzer.py https://yoursite.com -o daily_$(date +\%Y\%m\%d).json
```

## Docker Integration

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY website_analyzer.py .

ENTRYPOINT ["python", "website_analyzer.py"]
```

Build and run:

```bash
# Build
docker build -t wesi-analyzer .

# Run
docker run -v $(pwd):/output wesi-analyzer https://example.com -o /output/report.json
```

## API Wrapper Example

Create a simple Flask API:

```python
from flask import Flask, jsonify, request
from website_analyzer import WebsiteAnalyzer

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    analyzer = WebsiteAnalyzer(url)
    results = analyzer.analyze()
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python test_analyzer.py

# The test demonstrates all features with sample HTML
```

## Performance Tips

1. **Timeout Configuration**: Adjust timeout for slow websites
2. **Batch Processing**: Analyze multiple pages in parallel
3. **Caching**: Cache results to avoid repeated requests
4. **Rate Limiting**: Be respectful of target servers

## Limitations

- Link checking is limited to 50 URLs to avoid overwhelming servers
- Currently analyzes single pages (main URL provided)
- Requires internet connection to analyze live websites
- Respects robots.txt and server response times

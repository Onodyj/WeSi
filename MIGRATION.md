# Migrating from WeSi 1.0 to 2.0

## Overview

WeSi 2.0 introduces a complete platform architecture while maintaining backward compatibility with the original CLI tool. This guide helps you understand the changes and upgrade smoothly.

## What's New in 2.0?

### Major Features Added
- **Full-Site Analysis Platform**: RESTful API with asynchronous processing
- **AI Assistant**: Context-aware recommendations using OpenAI
- **Multiple Report Formats**: HTML, text, and Google Docs
- **User Management**: Multi-user support with subscription tiers
- **Secure API Key Storage**: Encrypted storage for user API keys
- **CMS Detection**: Automatic platform detection with specific recommendations
- **Enhanced Analysis**: Accessibility audits, structured data extraction
- **Background Jobs**: Celery-based async processing with progress tracking

### Backward Compatibility
✅ **The original CLI tool (`wesi.py`) still works exactly as before!**

You can continue using:
```bash
python wesi.py https://example.com 10 report.json
```

## Migration Paths

### Path 1: Keep Using CLI (No Changes Needed)
If you're happy with the CLI tool, no migration is needed. Your existing scripts and workflows will continue to work.

### Path 2: Use New Features Programmatically
You can import and use the new modules in your existing Python code:

```python
# Old way (still works)
from wesi import WebsiteAnalyzer
analyzer = WebsiteAnalyzer("https://example.com", max_pages=50)
analyzer.crawl()
report = analyzer.generate_report()

# New way - more features
from we_si.crawler import WebsiteCrawler
from we_si.analyzer import PageAnalyzer

crawler = WebsiteCrawler("https://example.com", max_pages=50, max_depth=3)
pages = crawler.crawl()

analyzer = PageAnalyzer()
for page in pages:
    analysis = analyzer.analyze_page(page['url'], page['content'])
    print(f"CMS: {analysis['cms']['probable']}")
```

### Path 3: Deploy Full API Platform
Set up the complete platform with API, database, and background workers.

## Step-by-Step Migration to Full Platform

### 1. Install New Dependencies
```bash
pip install -r requirements.txt
```

New dependencies include:
- SQLAlchemy (database)
- Celery & Redis (async processing)
- Flask (API)
- Cryptography (secure storage)
- OpenAI (AI assistant)

### 2. Set Up Configuration
```bash
# Interactive configuration
python config_helper.py

# Or manually copy and edit
cp .env.example .env
# Edit .env with your settings
```

### 3. Initialize Database
```bash
python -c "from we_si.models import init_db; init_db()"
```

### 4. Start Services
```bash
# Automated startup
./start_wesi.sh

# Or manually:
redis-server  # Terminal 1
celery -A we_si.tasks worker --loglevel=info  # Terminal 2
python we_si/api.py  # Terminal 3
```

## Code Migration Examples

### Example 1: Basic Analysis
```python
# Old (v1.0)
from wesi import WebsiteAnalyzer
analyzer = WebsiteAnalyzer("https://example.com", max_pages=10)
analyzer.crawl()
report = analyzer.generate_report()

# New (v2.0) - with CMS detection
from we_si.crawler import WebsiteCrawler
from we_si.analyzer import PageAnalyzer

crawler = WebsiteCrawler("https://example.com", max_pages=10)
pages = crawler.crawl()

analyzer = PageAnalyzer()
for page in pages:
    analysis = analyzer.analyze_page(page['url'], page['content'])
    cms = analysis['cms']['probable']
    suggestions = analysis['suggestions']
    print(f"Detected CMS: {cms}")
```

### Example 2: Report Generation
```python
# Old (v1.0) - JSON only
analyzer.save_report("output.json")

# New (v2.0) - Multiple formats
from we_si.reports.html_report import HTMLReportGenerator
from we_si.reports.text_report import TextReportGenerator

html_gen = HTMLReportGenerator()
html = html_gen.generate(analysis_data)

text_gen = TextReportGenerator()
text = text_gen.generate(analysis_data)
```

### Example 3: AI Assistant (New in 2.0)
```python
from we_si.ai.assistant import AIAssistant

assistant = AIAssistant(api_key="your-openai-key")
response = assistant.get_quick_answer(
    "What should I fix first?",
    analysis_data
)
print(response)
```

## Configuration Differences

### v1.0 Configuration
```python
# Command line only
python wesi.py https://example.com 50
```

### v2.0 Configuration
```bash
# Environment variables (.env file)
DATABASE_URL=sqlite:///wesi.db
WESI_ENCRYPTION_KEY=your-fernet-key
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-your-key  # Optional
```

## API Integration

If you were scraping the JSON output from v1.0, you can now use the REST API:

### Old Approach
```bash
python wesi.py https://example.com 10 output.json
# Parse output.json
```

### New Approach
```bash
# Start analysis
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "base_url": "https://example.com"}'

# Get status
curl http://localhost:5000/api/status/{job_id}

# Download report
curl http://localhost:5000/api/analysis/{site_id}/report/json
```

## Feature Mapping

| v1.0 Feature | v2.0 Equivalent | Notes |
|--------------|-----------------|-------|
| CLI analysis | `wesi.py` (unchanged) | Still works! |
| JSON reports | `/api/analysis/{id}/report/json` | Via API |
| Basic crawler | `we_si.crawler.WebsiteCrawler` | Enhanced with robots.txt |
| Page analysis | `we_si.analyzer.PageAnalyzer` | Added CMS detection |
| Report generation | `we_si.reports.*` | Multiple formats |
| - | AI Assistant | New feature |
| - | User management | New feature |
| - | Async processing | New feature |

## Breaking Changes

✅ **None for CLI users!** The original `wesi.py` is unchanged.

⚠️ **For programmatic users:**
- The package structure changed from `wesi.py` module to `we_si/` package
- Import paths changed: `from wesi import X` → `from we_si.module import X`
- Old `WebsiteAnalyzer` class still in `wesi.py` but new features in `we_si/`

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Redis connection failed"
```bash
# Install Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # macOS

# Start Redis
redis-server
```

### "Encryption key not set"
```bash
python config_helper.py
# Or manually generate:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Getting Help

- Check `example_v2_usage.py` for working examples
- Read the updated README.md for full documentation
- Run tests: `python -m unittest tests.test_wesi`
- Original docs still available in QUICKSTART.md

## Rollback Plan

If you need to rollback to v1.0:
1. The CLI tool (`wesi.py`) never changed - just use it
2. Remove new files if desired: `rm -rf we_si/ tests/ .env`
3. Uninstall new dependencies: `pip uninstall celery redis flask sqlalchemy`

## Next Steps

1. ✅ Try the new CLI features with existing workflow
2. ✅ Experiment with AI assistant
3. ✅ Deploy API for team access
4. ✅ Set up automated analysis jobs
5. ✅ Integrate with your existing tools via REST API

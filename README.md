# WeSi - Website Analyzer

A comprehensive Python-based website analysis platform that provides detailed SEO, accessibility, and performance insights with AI-powered recommendations.

## ⚡ Quick Start

### For CLI Users (Simple)
```bash
# Install dependencies
pip install -r requirements.txt

# Analyze a website (works just like v1.0)
python wesi.py https://example.com 10 report.json
```

### For API Platform (Full Features)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
python config_helper.py

# 3. Start all services
./start_wesi.sh

# API now available at http://localhost:5000
```

### Try the Examples
```bash
# See new features in action
python example_v2_usage.py
```

## Features

### 🚀 Version 2.0 - Full Site Analysis Platform

WeSi now provides enterprise-grade website analysis with advanced features:

### 🏗️ Full-Site Crawler
- **Intelligent Crawling**: Respects robots.txt and rate limits
- **Configurable Depth**: Control crawl depth and page limits based on subscription
- **URL Normalization**: Automatic deduplication and canonicalization
- **Same-Origin Policy**: Stays within your domain automatically
- **Optional JS Rendering**: Playwright support for client-side rendered pages

### 🔍 Enhanced Analysis
- **CMS Detection**: Automatically identifies WordPress, Squarespace, Wix, Shopify, and more
- **Comprehensive SEO**: Title tags, meta descriptions, keywords, Open Graph, Twitter Cards
- **Accessibility Audit**: WCAG compliance checking, alt text validation, semantic HTML analysis
- **Structured Data**: JSON-LD extraction and validation
- **Performance Metrics**: Load time tracking per page
- **Content Analysis**: Word count, keyword density, readability

### 📊 Multiple Report Formats
- **HTML Reports**: Beautiful, styled reports with executive summaries and detailed breakdowns
- **Text Reports**: CLI/email-friendly plain text summaries
- **Google Docs**: Auto-generated formatted Google Docs (requires API setup)
- **JSON Export**: Machine-readable data for integrations

### 🤖 AI Assistant Integration
- **Context-Aware**: Uses your actual site data, not generic responses
- **Plain Language**: Explains technical issues in simple terms
- **Platform-Specific**: Provides Squarespace, WordPress, Wix-specific instructions
- **Conversation History**: Maintains context across follow-up questions
- **Action Plans**: Generates prioritized improvement roadmaps

### 🔒 Secure API Key Storage
- **Encrypted Storage**: Fernet-based encryption for API keys at rest
- **User Keys**: Users can provide their own OpenAI/Google API keys
- **Environment Isolation**: Keys never exposed in API responses

### 💼 Subscription Tiers
- **Free**: 10 pages/run, 5 analyses/month, basic reports
- **Standard**: 50 pages/run, 20 analyses/month, AI assistant, Google Docs
- **Full**: 200 pages/run, 100 analyses/month, all features

### ⚡ Asynchronous Processing
- **Background Jobs**: Celery-based task queue with Redis
- **Real-time Progress**: WebSocket/SSE support for live updates
- **Job Management**: Query job status, pause, resume capabilities

## Installation

### Prerequisites
- Python 3.7+
- Redis (for async processing)
- Optional: Playwright (for JS rendering)
- Optional: Google Cloud credentials (for Google Docs integration)

### Basic Setup

1. Clone the repository:
```bash
git clone https://github.com/Onodyj/WeSi.git
cd WeSi
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add the output to .env as WESI_ENCRYPTION_KEY
```

5. Initialize the database:
```bash
python -c "from we_si.models import init_db; init_db()"
```

### Optional: Playwright Setup

For JavaScript-rendered pages:
```bash
playwright install chromium
```

### Optional: Google Docs API Setup

1. Create a Google Cloud project
2. Enable Google Docs API
3. Create a service account
4. Download credentials JSON
5. Set path in .env: `GOOGLE_DOCS_CREDENTIALS=/path/to/credentials.json`

## Usage

### Running the API Server

1. Start Redis:
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A we_si.tasks worker --loglevel=info
```

3. Start Flask API:
```bash
python we_si/api.py
```

The API will be available at `http://localhost:5000`

### Legacy CLI Usage

The original CLI tool is still available:

```bash
python wesi.py https://example.com 10 report.json
```

### API Endpoints

#### Start Analysis
```bash
POST /api/analyze
{
  "user_id": 1,
  "base_url": "https://example.com",
  "max_pages": 50,
  "max_depth": 3
}
```

#### Check Status
```bash
GET /api/status/<job_id>
```

#### Get Results
```bash
GET /api/analysis/<site_analysis_id>
```

#### Download Report
```bash
GET /api/analysis/<site_analysis_id>/report/html
GET /api/analysis/<site_analysis_id>/report/text
GET /api/analysis/<site_analysis_id>/report/json
```

#### AI Assistant Chat
```bash
POST /api/analysis/<site_analysis_id>/assistant/chat
{
  "user_id": 1,
  "message": "How can I improve my SEO?",
  "conversation_id": 123  // optional
}
```

#### Manage API Keys
```bash
# List services
GET /api/user/<user_id>/api-keys

# Add/update key
POST /api/user/<user_id>/api-keys
{
  "service": "openai",
  "api_key": "sk-..."
}

# Delete key
DELETE /api/user/<user_id>/api-keys/<service>
```

## Architecture

```
we_si/
├── __init__.py
├── crawler.py          # Enhanced crawler with robots.txt support
├── analyzer.py         # Page analyzer with CMS detection
├── models.py           # SQLAlchemy database models
├── tasks.py            # Celery async tasks
├── api.py              # Flask REST API
├── storage/
│   └── secrets.py      # Encrypted API key storage
├── reports/
│   ├── html_report.py  # HTML report generator
│   ├── text_report.py  # Text report generator
│   └── gdoc_report.py  # Google Docs generator
└── ai/
    └── assistant.py    # AI assistant integration

tests/
└── test_wesi.py        # Unit tests

wesi.py                 # Legacy CLI tool (still functional)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_SECRET_KEY` | Yes | Flask session secret key |
| `DATABASE_URL` | Yes | Database connection URL (default: sqlite:///wesi.db) |
| `WESI_ENCRYPTION_KEY` | Yes | Fernet key for API key encryption |
| `REDIS_URL` | Yes | Redis connection URL for Celery |
| `OPENAI_API_KEY` | No | Server-side OpenAI key (users can provide their own) |
| `GOOGLE_DOCS_CREDENTIALS` | No | Path to Google service account JSON |
| `ENABLE_PLAYWRIGHT` | No | Enable JavaScript rendering (true/false) |

## Database Models

- **User**: User accounts
- **Subscription**: Subscription tiers and limits
- **APIKey**: Encrypted API keys
- **SiteAnalysis**: Analysis jobs and results
- **PageAnalysis**: Individual page data
- **AssistantConversation**: AI chat history
- **AssistantMessage**: Individual chat messages

## Subscription Tiers

### Free Tier
- 10 pages per analysis
- 5 analyses per month
- Depth: 2 levels
- Basic reports only

### Standard Tier
- 50 pages per analysis
- 20 analyses per month
- Depth: 3 levels
- AI assistant access
- Google Docs reports

### Full Tier
- 200 pages per analysis
- 100 analyses per month
- Depth: 5 levels
- All features included
- Priority support

## Testing

Run the test suite:
```bash
python -m pytest tests/
# or
python -m unittest discover tests/
```

## Development

### Project Structure (old content preserved below)

## 🤖 NEW: AI Chatbot Integration

WeSi now includes an integrated AI chatbot that allows you to interactively query and discuss your website analysis results! Ask questions about your SEO, content quality, and get actionable recommendations.

**Supported AI Providers:**
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Google (Gemini)

See [CHATBOT.md](CHATBOT.md) for full documentation.

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

3. (Optional) For chatbot functionality, install AI provider:
```bash
# For OpenAI
pip install openai

# For Anthropic Claude
pip install anthropic

# For Google Gemini
pip install google-generativeai
```

## Usage

### Basic Usage

Analyze a website with default settings (max 50 pages):
```bash
python wesi.py https://example.com
```

### Chatbot Mode

Analyze and chat about your results:
```bash
python wesi.py https://example.com --chat --provider openai
```

Chat with existing analysis:
```bash
python wesi.py --chat-only --analysis website_analysis.json --provider openai
```

### Custom Options

Specify maximum pages and custom output file:
```bash
python wesi.py https://example.com --max-pages 10 --output my_report.json
```

### Command Line Arguments

```
python wesi.py [url] [options]

Positional Arguments:
  url                  - The URL of the website to analyze

Options:
  --max-pages N        - Maximum number of pages to crawl (default: 50)
  --output FILE        - Output JSON file name (default: website_analysis.json)
  --chat               - Launch chatbot after analysis
  --chat-only          - Launch chatbot without analysis (requires --analysis)
  --analysis FILE      - Path to existing analysis file (for --chat-only)
  --provider PROVIDER  - Chatbot provider: openai, anthropic, google (default: openai)
  --model MODEL        - Specific model to use with chatbot
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

## API Server (NEW!)

WeSi now includes a REST API server for asynchronous website analysis with API key authentication!

### Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create an API key:**
   ```bash
   python scripts/add_api_key.py --key "your-secret-key" --owner "Your Name"
   ```

3. **Start the API server:**
   ```bash
   python api/server.py
   ```

4. **Submit an analysis job:**
   ```bash
   curl -X POST "http://localhost:8000/analyze" \
     -H "X-API-Key: your-secret-key" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "max_pages": 10}'
   ```

### Features

- 🔐 **API Key Authentication**: Secure access with API keys
- ⚡ **Asynchronous Processing**: Submit jobs and check status later
- 💾 **SQLite Persistence**: Jobs and results stored in database
- 🤖 **Background Worker**: Automatic processing of pending jobs
- 📊 **Job Tracking**: Monitor job status and retrieve reports
- 📚 **Interactive Docs**: Auto-generated API docs at `/docs`

### Documentation

For detailed API documentation, examples, and usage instructions, see [API_README.md](API_README.md).

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is available for use under standard open source practices.

## Author

Created for comprehensive website analysis and SEO optimization.

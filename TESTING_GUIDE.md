# WeSi Chatbot Testing Guide

This guide will help you test the AI chatbot integration and see its capabilities.

## Quick Test (No API Key Required)

You can test the chatbot system without any API keys using the mock chatbot:

```bash
# Run the test suite
python3 test_chatbot.py

# Run the example demonstrations
python3 example_chatbot_usage.py
```

This will show you how the chatbot architecture works without requiring real API credentials.

## Testing with Real AI (Requires API Key)

To test with actual AI capabilities, follow these steps:

### Step 1: Choose Your AI Provider

Pick one of these providers and get an API key:

**Option A: OpenAI (Recommended for testing)**
- Sign up at: https://platform.openai.com/signup
- Get API key: https://platform.openai.com/api-keys
- Models: `gpt-3.5-turbo` (fast, cheap) or `gpt-4` (better quality)
- Cost: ~$0.002 per analysis session

**Option B: Anthropic Claude**
- Sign up at: https://console.anthropic.com/
- Get API key in settings
- Models: `claude-3-sonnet-20240229` or `claude-3-opus-20240229`

**Option C: Google Gemini**  
- Sign up at: https://makersuite.google.com/
- Get API key: https://makersuite.google.com/app/apikey
- Model: `gemini-pro`
- Cost: Free tier available

### Step 2: Install the Provider Package

```bash
# For OpenAI (recommended for first test)
pip install openai

# OR for Anthropic
pip install anthropic

# OR for Google
pip install google-generativeai
```

### Step 3: Set Your API Key

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-actual-key-here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-your-actual-key-here"
```

### Step 4: Run Your First Test

**Method 1: Quick Test with Existing Report**

Use one of the example reports that come with the repo:

```bash
python wesi.py --chat-only --analysis example_detailed_report.json --provider openai
```

You'll see:
```
Loaded analysis from: example_detailed_report.json

======================================================================
WeSi Chatbot - Interactive Mode
======================================================================
Type your questions about the website analysis.
Commands: 'quit', 'exit', 'help'
======================================================================

You: 
```

**Method 2: Full Analysis + Chat**

Analyze a real website and immediately chat about it:

```bash
# Small website (fast, good for testing)
python wesi.py https://example.com --max-pages 3 --chat --provider openai

# Your own website
python wesi.py https://your-website.com --max-pages 5 --chat --provider openai
```

## What to Test

Once you're in the chatbot, try these questions to see its capabilities:

### Basic Questions
```
You: Give me a summary of the analysis
You: What are the critical issues?
You: How many pages were analyzed?
```

### SEO-Specific Questions
```
You: What SEO improvements should I make?
You: Are my title tags optimized?
You: Do I have any missing meta descriptions?
You: What's my keyword density?
```

### Content Analysis
```
You: How's my content quality?
You: Which pages have thin content?
You: What's the average word count per page?
```

### Technical Questions
```
You: Do I have any broken links?
You: Which images are missing alt text?
You: Is my HTML structure semantic?
You: What's my heading hierarchy?
```

### Follow-Up Conversations
The chatbot maintains context, so you can ask follow-ups:
```
You: What are my issues?
Assistant: [Lists issues]

You: Tell me more about the first one
Assistant: [Details about first issue]

You: How do I fix it?
Assistant: [Specific guidance]
```

## Testing Different Providers

Compare the responses from different AI models:

```bash
# OpenAI GPT-3.5 (fast, good quality)
python wesi.py --chat-only --analysis example_detailed_report.json --provider openai --model gpt-3.5-turbo

# OpenAI GPT-4 (slower, best quality)
python wesi.py --chat-only --analysis example_detailed_report.json --provider openai --model gpt-4

# Anthropic Claude (detailed, nuanced)
python wesi.py --chat-only --analysis example_detailed_report.json --provider anthropic

# Google Gemini (fast, free tier)
python wesi.py --chat-only --analysis example_detailed_report.json --provider google
```

## Example Test Session

Here's a complete example test session:

```bash
$ python wesi.py https://example.com --max-pages 3 --chat --provider openai

Starting analysis of https://example.com
Maximum pages to crawl: 3

[1/3] Crawling: https://example.com
[2/3] Crawling: https://example.com/about
[3/3] Crawling: https://example.com/contact

Crawl complete! Analyzed 3 page(s).

======================================================================
ANALYSIS COMPLETE - INSIGHTS
======================================================================

🔴 CRITICAL ISSUES:
  - 1 page(s) missing title tags

⚠️  WARNINGS:
  - 2 page(s) missing meta descriptions
  - 5 images missing alt text

Report saved to: website_analysis.json

======================================================================
Launching chatbot...
======================================================================

You: Give me a summary
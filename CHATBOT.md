# WeSi Chatbot Integration

WeSi now includes an integrated chatbot feature that allows you to interactively query and discuss your website analysis results using AI-powered assistants.

## Features

- **Multi-Provider Support**: Works with OpenAI (GPT), Anthropic (Claude), and Google (Gemini)
- **Context-Aware**: Chatbot has full access to your website analysis data
- **Interactive Mode**: Ask questions naturally about your website's SEO, content, structure, and more
- **Flexible Usage**: Use immediately after analysis or later with saved reports
- **Extensible Design**: Easy to add support for additional chatbot providers

## Installation

### 1. Install Base Requirements

```bash
pip install -r requirements.txt
```

### 2. Install Chatbot Provider (Choose One or More)

**For OpenAI (GPT):**
```bash
pip install openai
```

**For Anthropic (Claude):**
```bash
pip install anthropic
```

**For Google (Gemini):**
```bash
pip install google-generativeai
```

### 3. Set Up API Keys

You need an API key for your chosen provider:

**OpenAI:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Anthropic:**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

**Google:**
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Usage

### Option 1: Analyze and Chat (One Command)

Run analysis and immediately launch chatbot:

```bash
python wesi.py https://example.com --chat --provider openai
```

With custom options:
```bash
python wesi.py https://example.com --max-pages 20 --output my_report.json --chat --provider anthropic
```

### Option 2: Chat with Existing Report

If you already have an analysis report:

```bash
python wesi.py --chat-only --analysis website_analysis.json --provider openai
```

### Option 3: Standalone Chatbot

You can also use the chatbot module directly:

```bash
python chatbot.py --provider openai --analysis website_analysis.json
```

## Provider Options

### OpenAI (Default)

- **Models**: gpt-3.5-turbo (default), gpt-4, gpt-4-turbo
- **Best for**: General purpose, balanced performance
- **Setup**: [Get API key](https://platform.openai.com/api-keys)

```bash
python wesi.py https://example.com --chat --provider openai --model gpt-4
```

### Anthropic Claude

- **Models**: claude-3-sonnet-20240229 (default), claude-3-opus-20240229
- **Best for**: Detailed analysis, nuanced responses
- **Setup**: [Get API key](https://console.anthropic.com/)

```bash
python wesi.py https://example.com --chat --provider anthropic --model claude-3-opus-20240229
```

### Google Gemini

- **Models**: gemini-pro (default), gemini-pro-vision
- **Best for**: Fast responses, cost-effective
- **Setup**: [Get API key](https://makersuite.google.com/app/apikey)

```bash
python wesi.py https://example.com --chat --provider google
```

## Example Conversations

### Getting Started

```
You: Give me a summary of the analysis
Assistant: Here's a summary...

### Common Questions

See example_chatbot_usage.py for more examples.

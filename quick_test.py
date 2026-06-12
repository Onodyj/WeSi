#!/usr/bin/env python3
"""
Quick Test Script for WeSi Chatbot
This script helps you quickly test the chatbot with a mock AI (no API key needed).
"""

import json
import sys
from chatbot import ChatbotInterface


class InteractiveMockChatbot(ChatbotInterface):
    """
    Mock chatbot that demonstrates chatbot capabilities without requiring API keys.
    This shows how the system works, but uses predefined logic instead of real AI.
    """
    
    def send_message(self, message: str) -> str:
        """Process message and return intelligent mock response."""
        self.conversation_history.append({"role": "user", "content": message})
        
        message_lower = message.lower()
        
        if not self.analysis_data:
            response = "❌ No analysis data loaded. Please provide an analysis report."
        
        # Summary requests
        elif any(word in message_lower for word in ["summary", "overview", "general"]):
            summary = self.analysis_data.get('summary', {})
            metadata = self.analysis_data.get('metadata', {})
            response = f"""📊 **Website Analysis Summary**

**URL:** {metadata.get('base_url', 'N/A')}
**Pages Analyzed:** {summary.get('total_pages_analyzed', 0)}
**Analysis Date:** {metadata.get('analysis_date', 'N/A')}

**Key Metrics:**
- Total Images: {summary.get('total_images', 0)}
- Images Missing Alt Text: {summary.get('images_without_alt', 0)}
- Internal Links: {summary.get('total_internal_links', 0)}
- External Links: {summary.get('total_external_links', 0)}
- Broken Links: {summary.get('broken_links_found', 0)}
- Average Word Count: {summary.get('avg_word_count', 0)} words/page

Would you like details on any specific area?"""

        # Critical issues
        elif "critical" in message_lower or "urgent" in message_lower:
            insights = self.analysis_data.get('insights', {})
            critical = insights.get('critical', [])
            if critical:
                response = "🔴 **Critical Issues Found:**\n\n" + "\n".join(f"{i+1}. {issue}" for i, issue in enumerate(critical))
                response += "\n\nThese should be addressed immediately as they significantly impact SEO and user experience."
            else:
                response = "✅ **Great news!** No critical issues found. Your site's core elements are in good shape."
        
        # Warnings
        elif "warning" in message_lower or "medium" in message_lower:
            insights = self.analysis_data.get('insights', {})
            warnings = insights.get('warnings', [])
            if warnings:
                response = "⚠️ **Warnings:**\n\n" + "\n".join(f"{i+1}. {w}" for i, w in enumerate(warnings))
                response += "\n\nThese are important improvements that should be made soon."
            else:
                response = "✅ No warnings found!"
        
        # Recommendations
        elif "recommend" in message_lower or "suggest" in message_lower or "improve" in message_lower:
            insights = self.analysis_data.get('insights', {})
            recommendations = insights.get('recommendations', [])
            if recommendations:
                response = "💡 **Recommendations:**\n\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(recommendations))
                response += "\n\nImplementing these will further enhance your site's quality and SEO performance."
            else:
                response = "Your site is well-optimized! No additional recommendations at this time."
        
        # SEO-specific
        elif "seo" in message_lower:
            insights = self.analysis_data.get('insights', {})
            response = "🎯 **SEO Analysis:**\n\n"
            response += "**Critical SEO Issues:**\n"
            for issue in insights.get('critical', [])[:3]:
                response += f"- {issue}\n"
            response += "\n**SEO Warnings:**\n"
            for warning in insights.get('warnings', [])[:3]:
                response += f"- {warning}\n"
            response += "\nFocus on fixing critical issues first for maximum SEO impact."
        
        # Images
        elif "image" in message_lower or "alt" in message_lower or "picture" in message_lower:
            summary = self.analysis_data.get('summary', {})
            total = summary.get('total_images', 0)
            missing = summary.get('images_without_alt', 0)
            response = f"""🖼️ **Image Analysis:**

- Total Images: {total}
- Images with Alt Text: {total - missing}
- Images Missing Alt Text: {missing}

"""
            if missing > 0:
                percentage = (missing / total * 100) if total > 0 else 0
                response += f"⚠️ {percentage:.1f}% of your images are missing alt text. This affects:\n"
                response += "1. **Accessibility** - Screen readers can't describe these images\n"
                response += "2. **SEO** - Search engines use alt text to understand images\n"
                response += "3. **UX** - Alt text displays when images fail to load\n\n"
                response += "**Fix:** Add descriptive alt text to each image describing what it shows."
            else:
                response += "✅ All images have alt text! Great for accessibility and SEO."
        
        # Links
        elif "link" in message_lower:
            summary = self.analysis_data.get('summary', {})
            internal = summary.get('total_internal_links', 0)
            external = summary.get('total_external_links', 0)
            broken = summary.get('broken_links_found', 0)
            response = f"""🔗 **Link Analysis:**

- Internal Links: {internal}
- External Links: {external}
- Broken Links: {broken}

"""
            if broken > 0:
                response += f"⚠️ Found {broken} broken link(s). Broken links:\n"
                response += "- Hurt SEO (search engines penalize broken links)\n"
                response += "- Create poor user experience\n"
                response += "- Indicate outdated content\n\n"
                response += "**Action:** Review and fix or remove broken links."
            else:
                response += "✅ No broken links found! Your link structure is healthy."
        
        # Content
        elif "content" in message_lower or "word" in message_lower or "text" in message_lower:
            summary = self.analysis_data.get('summary', {})
            avg_words = summary.get('avg_word_count', 0)
            response = f"""📝 **Content Analysis:**

- Average Word Count: {avg_words} words per page

"""
            if avg_words < 300:
                response += "⚠️ Your average content length is below recommended levels.\n\n"
                response += "**Why it matters:**\n"
                response += "- Search engines prefer substantial content (300+ words)\n"
                response += "- More content = more keyword opportunities\n"
                response += "- Better user engagement and value\n\n"
                response += "**Recommendation:** Expand thin pages with quality content."
            else:
                response += "✅ Good content depth! You're meeting recommended word count standards."
        
        # How to fix
        elif "how" in message_lower and "fix" in message_lower:
            response = """🔧 **General Fixing Guide:**

**For Missing Title Tags:**
```html
<head>
  <title>Your Page Title (50-60 characters)</title>
</head>
```

**For Meta Descriptions:**
```html
<meta name="description" content="Your description here (150-160 chars)">
```

**For Image Alt Text:**
```html
<img src="image.jpg" alt="Descriptive text about the image">
```

**For Broken Links:**
1. Find the broken link in your HTML
2. Update the URL or remove the link
3. Consider setting up 301 redirects for important pages

What specific issue would you like help with?"""
        
        # Help
        elif "help" in message_lower:
            response = """❓ **How to Use This Chatbot:**

You can ask me about:
- **"Give me a summary"** - Overview of the analysis
- **"What are the critical issues?"** - Most important problems
- **"Tell me about images"** - Image analysis and alt text
- **"What about SEO?"** - SEO-specific findings
- **"How's my content?"** - Content quality analysis
- **"Do I have broken links?"** - Link health check
- **"How do I fix [issue]?"** - Specific fixing guidance

**Note:** This is a DEMO using mock AI. For real AI-powered responses, use:
`python wesi.py --chat-only --analysis report.json --provider openai`
(Requires OpenAI API key)

Try asking a specific question!"""
        
        # Default response
        else:
            response = f"""I understand you're asking: "{message}"

This is a **demo chatbot** using predefined logic. For actual AI-powered conversations, you'll need to:

1. Get an API key from OpenAI, Anthropic, or Google
2. Install the provider: `pip install openai`
3. Set your API key: `export OPENAI_API_KEY="your-key"`
4. Run with: `python wesi.py --chat-only --analysis your_report.json --provider openai`

Try these demo questions:
- "Give me a summary"
- "What are the critical issues?"
- "Tell me about my images"
- "How's my SEO?"
- "help"
"""
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response


def main():
    """Run interactive mock chatbot test."""
    print("="*70)
    print("WeSi Chatbot - DEMO MODE (No API Key Required)")
    print("="*70)
    print()
    print("This demonstrates the chatbot interface using mock responses.")
    print("For real AI responses, follow the setup in TESTING_GUIDE.md")
    print()
    
    # Try to load an analysis file
    import os
    analysis_files = [
        'test_analysis.json',
        'example_detailed_report.json',
        'example_basic_report.json',
        'website_analysis.json'
    ]
    
    analysis_data = None
    loaded_file = None
    
    for filename in analysis_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    analysis_data = json.load(f)
                loaded_file = filename
                print(f"✅ Loaded analysis data from: {filename}")
                break
            except Exception as e:
                print(f"⚠️  Could not load {filename}: {e}")
    
    if not analysis_data:
        print()
        print("❌ No analysis file found. Please run an analysis first:")
        print("   python wesi.py https://example.com --max-pages 3")
        print()
        sys.exit(1)
    
    print()
    print("="*70)
    print("Interactive Chat Session")
    print("="*70)
    print("Commands: 'quit', 'exit', 'help'")
    print("="*70)
    print()
    
    # Create chatbot
    chatbot = InteractiveMockChatbot(analysis_data=analysis_data)
    
    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("\n👋 Goodbye! To test with real AI, see TESTING_GUIDE.md\n")
                break
            
            # Get response
            response = chatbot.send_message(user_input)
            print(f"\nAssistant:\n{response}\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == '__main__':
    main()

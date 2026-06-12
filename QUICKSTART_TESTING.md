# Quick Start: Testing the Chatbot

## 🚀 Two Ways to Test

### 1️⃣ Instant Demo (30 seconds)

No setup needed! Run this right now:

```bash
cd /home/runner/work/WeSi/WeSi
python3 quick_test.py
```

**What you'll see:**
```
======================================================================
WeSi Chatbot - DEMO MODE (No API Key Required)
======================================================================

You: give me a summary
Assistant: 
📊 **Website Analysis Summary**
...
```

**Try these commands:**
- `help` - See what you can ask
- `give me a summary` - Overview of analysis
- `what are the critical issues?` - Important problems
- `tell me about images` - Image analysis
- `quit` - Exit

### 2️⃣ Real AI Testing (5 minutes)

**Step 1:** Choose a provider and get an API key
- OpenAI: https://platform.openai.com/api-keys (Recommended)
- Anthropic: https://console.anthropic.com/
- Google: https://makersuite.google.com/app/apikey (Free tier!)

**Step 2:** Install the package
```bash
pip install openai  # or: anthropic, google-generativeai
```

**Step 3:** Set your API key
```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
```

**Step 4:** Run with real AI
```bash
python wesi.py --chat-only --analysis example_detailed_report.json --provider openai
```

**Now chat with real AI!**
```
You: What are my top 3 SEO priorities?
Assistant: Based on the analysis, your top 3 SEO priorities are:

1. **Missing Title Tags** - Found on 2 pages. Title tags are crucial 
   for search rankings...
   
2. **Images Without Alt Text** - 5 images are missing alt text...

3. **Meta Descriptions** - 2 pages need meta descriptions for better
   click-through rates...

Would you like specific guidance on implementing any of these?

You: How do I add title tags?
Assistant: Here's how to add proper title tags...
```

## 📊 Feature Comparison

| Feature | Demo Mode | Real AI Mode |
|---------|-----------|--------------|
| Speed | Instant | 1-2 seconds per response |
| Setup | None | API key required |
| Cost | Free | ~$0.001-$0.05 per session |
| Responses | Predefined logic | Dynamic AI-generated |
| Context | Basic | Full understanding |
| Follow-ups | Limited | Natural conversation |

## 🎯 What to Test

### Basic Queries
✓ "Give me a summary"
✓ "What are the issues?"
✓ "How many pages were analyzed?"

### SEO Questions  
✓ "What are my SEO problems?"
✓ "How can I improve my rankings?"
✓ "Are my title tags good?"

### Technical Details
✓ "Tell me about broken links"
✓ "Which images need alt text?"
✓ "How's my HTML structure?"

### Action Items
✓ "How do I fix [specific issue]?"
✓ "What should I prioritize?"
✓ "Give me a step-by-step plan"

## 💡 Tips

1. **Start with Demo Mode** - Get familiar with the interface
2. **Use Example Reports** - Test with included example files first
3. **Ask Follow-ups** - The AI remembers context
4. **Be Specific** - "What SEO issues on the homepage?" works better than "Tell me everything"
5. **Try Different Providers** - Each AI has different strengths

## 📚 More Information

- **TESTING_GUIDE.md** - Complete testing documentation (207 lines)
- **CHATBOT.md** - Full chatbot documentation
- **example_chatbot_usage.py** - Code examples for programmers
- **IMPLEMENTATION_SUMMARY.md** - Technical details

## 🆘 Troubleshooting

**"No module named openai"**
```bash
pip install openai
```

**"API key not found"**
```bash
export OPENAI_API_KEY="your-key"  # Make sure it's in quotes
```

**"No analysis file found"**
```bash
python wesi.py https://example.com --max-pages 3  # Create one first
```

## 🎉 Start Now!

The easiest way to see it in action:

```bash
python3 quick_test.py
```

Then try: `help`, `summary`, `critical issues`, `quit`

---

**Ready for real AI?** See TESTING_GUIDE.md for detailed setup instructions.

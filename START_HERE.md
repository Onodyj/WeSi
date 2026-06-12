# 🎯 FASTEST WAY TO TEST - For Non-Technical Users

## Option 1: Double-Click Method (Easiest!)

### On Windows:
1. Find the file `run_demo.bat` in the WeSi folder
2. **Double-click** `run_demo.bat`
3. A black window will open with the chatbot
4. Start typing your questions!

### On Mac/Linux:
1. Find the file `run_demo.sh` in the WeSi folder
2. **Right-click** → Open With → Terminal (or double-click if configured)
3. Start typing your questions!

---

## Option 2: Copy-Paste Method (Also Easy!)

### Step 1: Open Terminal
- **Windows**: Press `Windows Key + R`, type `cmd`, press Enter
- **Mac**: Press `Command + Space`, type `terminal`, press Enter
- **Linux**: Press `Ctrl + Alt + T`

### Step 2: Copy & Paste These Commands

**For Windows, copy this ENTIRE block:**
```
cd %USERPROFILE%\Documents\WeSi
python quick_test.py
```

**For Mac/Linux, copy this ENTIRE block:**
```
cd ~/Documents/WeSi
python3 quick_test.py
```

### Step 3: Paste into Terminal
- **Windows**: Right-click in the black window to paste
- **Mac/Linux**: Press `Command + V` or `Ctrl + Shift + V`

### Step 4: Press Enter

---

## What Happens Next?

You'll see:
```
======================================================================
WeSi Chatbot - DEMO MODE (No API Key Required)
======================================================================

You: 
```

**Now type any question!** Examples:
- `help` - See what you can ask
- `give me a summary` - Get analysis overview
- `what are critical issues?` - See important problems
- `quit` - Exit the chatbot

---

## Common Questions

### "Where is the WeSi folder?"
It's wherever you downloaded/cloned this project. Common locations:
- Windows: `C:\Users\YourName\Documents\WeSi` or `C:\Users\YourName\Downloads\WeSi`
- Mac: `/Users/YourName/Documents/WeSi` or `/Users/YourName/Downloads/WeSi`
- Linux: `/home/yourname/Documents/WeSi` or `/home/yourname/Downloads/WeSi`

### "Nothing happens when I double-click"
Try the Copy-Paste Method instead (Option 2 above).

### "I see an error message"
Read the error and check:
1. Are you in the WeSi folder? (The folder that has `quick_test.py` in it)
2. Is Python installed? (Download from https://www.python.org/ if not)
3. Did you run the base requirements? (`pip install -r requirements.txt`)

### "How do I stop it?"
Type `quit` and press Enter, or press `Ctrl + C`.

---

## Need More Help?

See **HOW_TO_RUN.md** for detailed instructions with troubleshooting.

---

## Want to Use Real AI Instead of Demo?

The demo uses fake AI responses. For real AI:

1. **Get an API key** from one of these:
   - OpenAI: https://platform.openai.com/api-keys (easiest)
   - Google: https://makersuite.google.com/app/apikey (free tier)
   - Anthropic: https://console.anthropic.com/

2. **See TESTING_GUIDE.md** for complete setup instructions

The demo is enough to see how it works though!

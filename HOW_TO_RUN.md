# How to Run the Chatbot - Step-by-Step Guide

## ⚠️ Important: These are TERMINAL COMMANDS, not code to put in files

The commands in this guide are meant to be typed into your **terminal** (also called command prompt, shell, or console).

---

## 🖥️ Step 1: Open Your Terminal

**On Windows:**
- Press `Windows Key + R`
- Type `cmd` or `powershell`
- Press Enter

**On Mac:**
- Press `Command + Space`
- Type `terminal`
- Press Enter

**On Linux:**
- Press `Ctrl + Alt + T`
- Or search for "Terminal" in your applications

---

## 📂 Step 2: Navigate to the WeSi Folder

In your terminal, type these commands **one at a time** and press Enter after each:

```bash
cd path/to/WeSi
```

Replace `path/to/WeSi` with the actual location where you cloned/downloaded this repository.

**Example:**
- Windows: `cd C:\Users\YourName\Documents\WeSi`
- Mac/Linux: `cd ~/Documents/WeSi`

**To find your current location**, type:
```bash
pwd
```

**To see files in current folder**, type:
```bash
ls          # Mac/Linux
dir         # Windows
```

You should see files like: `wesi.py`, `chatbot.py`, `quick_test.py`

---

## 🎯 Step 3A: Run the INSTANT DEMO (Easiest - No Setup)

Once you're in the WeSi folder, simply type:

```bash
python3 quick_test.py
```

**Or if that doesn't work, try:**
```bash
python quick_test.py
```

### What You'll See:

```
======================================================================
WeSi Chatbot - DEMO MODE (No API Key Required)
======================================================================

You: 
```

Now you can type questions like:
- `help`
- `give me a summary`
- `what are the critical issues?`
- `quit` (to exit)

**That's it!** You're now testing the chatbot.

---

## 🤖 Step 3B: Run with REAL AI (Requires Setup)

### For OpenAI (Recommended)

**1. Get an API Key**
- Go to: https://platform.openai.com/api-keys
- Sign up / Log in
- Click "Create new secret key"
- Copy the key (starts with `sk-...`)

**2. Install OpenAI Package**

In your terminal (in the WeSi folder), type:

```bash
pip install openai
```

Wait for it to finish installing.

**3. Set Your API Key**

**On Mac/Linux:**
```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
```
(Replace `sk-your-actual-key-here` with your real key)

**On Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-actual-key-here
```

**On Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-your-actual-key-here"
```

**4. Run the Chatbot**

```bash
python wesi.py --chat-only --analysis example_detailed_report.json --provider openai
```

Or on Windows if `python` doesn't work:
```bash
python3 wesi.py --chat-only --analysis example_detailed_report.json --provider openai
```

### Now You're Chatting with Real AI!

```
You: What are my top 3 SEO priorities?
Assistant: Based on the analysis, your top 3 SEO priorities are:
1. Missing title tags...
...
```

---

## 📋 Complete Example Session

Here's exactly what you type in your terminal:

```bash
# 1. Navigate to WeSi folder
cd ~/Documents/WeSi

# 2. Verify you're in the right place
ls

# 3. Run the instant demo
python3 quick_test.py

# When prompted, type:
help
give me a summary
quit

# Done!
```

---

## 🔧 Troubleshooting

### "python3: command not found"
**Try:** `python quick_test.py` instead

### "No module named 'chatbot'"
**Solution:** Make sure you're in the WeSi folder
```bash
cd path/to/WeSi
ls  # Should show chatbot.py
```

### "pip: command not found"
**Try:** `pip3 install openai` or `python -m pip install openai`

### "No such file or directory"
**Solution:** You're not in the WeSi folder
```bash
cd path/to/WeSi  # Navigate to WeSi first
```

### API Key Not Working
**Make sure:**
1. You copied the ENTIRE key (starts with `sk-`)
2. You put it in quotes: `"sk-..."`
3. You're in the same terminal window where you set the key

---

## ✅ Summary: Where to Run Commands

| What | Where |
|------|-------|
| All commands | **Terminal/Command Prompt** |
| File location | **WeSi folder** (navigate with `cd`) |
| Python files | **Already exist** (don't edit them) |
| API key | **Terminal** (set with `export` or `set`) |

**You don't need to create any files or edit any code!**

Everything is already set up. You just need to:
1. Open terminal
2. Navigate to WeSi folder (`cd path/to/WeSi`)
3. Run the command (`python3 quick_test.py`)

---

## 🎥 Video Walkthrough Alternative

If you're still confused, here's what a complete session looks like:

```
$ cd ~/Documents/WeSi
$ ls
chatbot.py  quick_test.py  wesi.py  ...

$ python3 quick_test.py
======================================================================
WeSi Chatbot - DEMO MODE (No API Key Required)
======================================================================
✅ Loaded analysis data from: example_detailed_report.json

You: help
Assistant: ❓ **How to Use This Chatbot:**
...

You: give me a summary
Assistant: 📊 **Website Analysis Summary**
**URL:** https://example.com
...

You: quit
👋 Goodbye!
$
```

**The `$` symbol means you're back at the terminal prompt** - this is where you type commands.

---

## 🆘 Still Having Issues?

If you're still stuck, tell me:
1. What operating system you're using (Windows/Mac/Linux)
2. Where you downloaded/cloned WeSi
3. What command you tried
4. What error message you see (copy the full message)

I'll provide specific help for your situation.

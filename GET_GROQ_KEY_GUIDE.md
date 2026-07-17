# Get Your Free Groq API Key — 2 Minute Guide

**Read this while you're waiting for something to load, then follow the steps below.**

---

## What You're Getting
- **Free API key** for Groq (instant generation, no credit card needed)
- **Limits**: 25 requests per month on free tier
- **Speed**: Groq is one of the fastest inference providers
- **Your 5 coding bots** will use this to answer when Ollama is offline

---

## Step-by-Step (Copy/Paste Friendly)

### Step 1: Open Browser
Open any browser (Chrome, Edge, Firefox, Safari).

### Step 2: Navigate to Groq Console
Go to this URL (copy/paste it):
```
https://console.groq.com/keys
```

### Step 3: Sign In or Create Account
- You'll see a login page
- Click **"Sign in with Google"** (easiest, uses your Google account)
  - OR click **"Create account"** if you don't have one
  - OR use email signup

The page will look like this:
```
┌─────────────────────────────────┐
│  GROQ Console                   │
│                                 │
│  ┌─────────────────────────────┐│
│  │ Sign in with Google         ││
│  └─────────────────────────────┘│
│                                 │
│  ┌─────────────────────────────┐│
│  │ Continue with Email         ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

### Step 4: Verify Email (if new account)
If you created a new account, you'll get an email from Groq.
Click the verification link in that email.

### Step 5: Find the API Keys Page
Once logged in, you'll see the dashboard.
Look for a menu on the left sidebar or top nav.
Click **"API Keys"** or **"Keys"**.

The page will show something like:
```
┌──────────────────────────────────────┐
│ API Keys                             │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ + Create API Key               │   │
│ └────────────────────────────────┘   │
│                                      │
│ (No keys yet)                        │
└──────────────────────────────────────┘
```

### Step 6: Create API Key
Click the **"Create API Key"** button or **"+"** button.

A dialog will appear asking you to name it. Enter:
```
jacky-squad
```

Then click **"Create"** or **"Generate"**.

### Step 7: Copy Your Key
A new key will appear on screen. It looks like:
```
gsk_abcDEF1234ghi567JKL890MNO1234PQRstu_VwXyZ
```

**Copy this entire key.**

⚠️ **IMPORTANT:**
- Do NOT share this key publicly
- Do NOT post it on GitHub or Discord
- This key is like a password — guard it
- We'll paste it into a gitignored vault file (it stays private on your PC)

### Step 8: Paste Into Vault
1. Go back to Notepad (should still be open with `secrets.env` file)
2. You should see the cursor right after: `GROQ_API_KEY_1=`
3. **Right-click → Paste** (or Ctrl+V)
4. **Save the file** (Ctrl+S)

Done! Your vault now has your Groq key.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Can't find the Create API Key button" | Look for a **"+"** icon or a button in the top-right of the Keys page |
| "Email not verified" | Check your email (including spam folder) for Groq verification link |
| "Key is very long and has underscores" | That's normal! Copy the whole thing, including underscores |
| "Notepad is closed" | I'll re-open it when you tell me the key is ready |
| "I made a typo" | Just delete and try again — the vault file is easy to edit |

---

## What Happens After

1. You tell me: "Key is pasted"
2. I run the full test suite automatically
3. All 5 coding bots come online
4. Platform ready for action

**Total time from now: ~5 minutes**

---

## Copy/Paste Reference

**If you need to send me the Groq key directly** (if Notepad isn't working):
- Copy the key from Groq console
- Paste it in the chat
- I'll put it in the vault for you

**The key looks like:**
```
gsk_[50+ random characters]
```

---

**Ready? Open that browser tab and follow the steps above!**

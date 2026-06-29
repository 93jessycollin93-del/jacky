# Cloud Squad Quick Start

**Your 5 coding bots are ready to go live.** They just need a free API key.

## 2-minute setup

### 1. Get a free Groq key (instant, no credit card)
- Go to https://console.groq.com/keys
- Click **Create API Key**
- Copy it

### 2. Paste into vault
Open `E:\AI\Jacky\secrets\secrets.env` in a text editor and add:
```
GROQ_API_KEY_1=<your_key_here>
```

### 3. Restart the server
```bash
# Kill the old serve.py (Ctrl+C in the terminal)
# Then:
cd E:\AI\Jacky
python serve.py
```

That's it. The 5 coding bots now have internet fallback.

---

## How it works

**Without a key:**
- `/api/chat` tries Ollama (local, free)
- If Ollama is offline or fails, it says "Groq unavailable, no keys set"
- No cost

**With a key:**
- `/api/chat` tries Ollama first (if running)
- If Ollama fails or is offline, automatically falls back to **Groq** (free tier: 25 req/month)
- If Groq fails, tries Gemini, then OpenRouter
- **You don't have to do anything** — it's automatic

---

## What you can do now

### Single expert opinion (Lead bot only)
```bash
curl -X POST http://localhost:5000/api/squads/coding/ask \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"write me a Python HTTP client"}]}'
```

### All 5 experts respond
```bash
curl -X POST http://localhost:5000/api/squads/coding/discuss \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"review this code"}]}'
```

### From the browser
1. Go to http://localhost:5000/hub
2. Log in with your SAS token
3. Pick **Coding** squad on the left
4. Type a question
5. **Lead responds** (or toggle "All Reply" for all 5)

---

## Free tier limits

| Provider | Free limit | Cost per request |
|---|---|---|
| Groq | 25/month | $0 |
| Gemini | 60/day | $0 |
| OpenRouter | varies | $0.50–5.00 per 1M tokens (cheaper than direct Claude/GPT) |

You'll auto-rotate through them. Groq is first and fastest.

---

## Troubleshooting

**"All routes failed: local was unsafe/unavailable and the free cloud tier could not answer"**
- Groq key is not pasted in `secrets/secrets.env`, OR
- The key is pasted but server wasn't restarted

**Fix:** Add key to vault, restart, then test again.

**"Ollama is running but bots still use Groq"**
- That's fine! Groq often responds faster than a local model. The system is using what's fastest.
- If you want to force local-only, set `integrations.cloud_bots.enabled = false` in `config.json`.

---

## Next steps

Once this works:
1. **Customize bot personalities** — edit `E:\AI\Jacky\bots\*.json` to change how each bot answers
2. **Populate your memory** — run `/api/collector/collect` to start building the knowledge graph
3. **Enable security squad** — add keys for more sophisticated analysis
4. **Put on the internet** — use `Start_SAS_Public.cmd` to expose via Cloudflare tunnel

The squad will be there.

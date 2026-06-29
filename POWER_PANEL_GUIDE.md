# SAS Power Panel — Complete Control Guide

**Access:** `http://localhost:5000/dashboard` → **⚡ Power Panel** section at top

---

## 🎯 Quick Start: 3 Power Modes

Click one button to auto-configure everything:

### 🌱 **Eco Mode** (Low Power, Free, Private)
- **What:** Offline-first, no cloud APIs
- **Best for:** Privacy-focused work, no internet quota
- **Speed:** Slow (~5-10 min per task)
- **Cost:** $0
- **Servers:** Ollama ✓, Jacky ✓, FCC ✗
- **AIs:** LM Studio ✓, NIM ✗, Groq ✗, Gemini ✗
- **Bots:** Monitor ✓, GitHub ✗, Security ✗

**Use when:** Writing sensitive docs, testing locally, no cloud budget

---

### ⚖️ **Balanced Mode** (Mixed, Recommended)
- **What:** Local + cloud fallback, best tradeoff
- **Best for:** Daily work, cost-conscious
- **Speed:** Medium (~2-3 min per task)
- **Cost:** $0 + NIM free tier (40 req/min)
- **Servers:** Ollama ✓, Jacky ✓, FCC ✓
- **AIs:** NIM ✓, LM Studio ✓, Groq ✓, Gemini ✗
- **Bots:** Monitor ✓, GitHub ✓, Security ✗

**Use when:** Most work (default mode)

---

### 🚀 **Performance Mode** (High Power, Fast, Cloud)
- **What:** Cloud-first, all AIs enabled, fastest
- **Best for:** Urgent work, complex reasoning, multi-agent tasks
- **Speed:** Fast (~30 sec per task)
- **Cost:** Cloud quotas consumed
- **Servers:** Ollama ✗, Jacky ✓, FCC ✓
- **AIs:** NIM ✓, Groq ✓, Gemini ✓, LM Studio ✗
- **Bots:** Monitor ✓, GitHub ✓, Security ✓

**Use when:** Coding complex features, debugging, critical work

---

## 🎛️ Manual Control: The Power Panel

Everything is toggleable manually via switches next to each service/bot/AI:

### **SERVERS Section**
- **Jacky (Brain)** `:5000` — Core orchestrator. Always on in Balanced/Performance.
- **FCC Proxy (Coder)** `:8082` — Claude Code CLI proxy. Eco mode disables.
- **Ollama (Local LLMs)** `:11434` — Model server. Performance mode disables (uses cloud instead).

**Manual control:** Click toggle to start/stop. Dots show status:
- 🟢 Online (running)
- ⚪ Offline (stopped)
- 🟠 Loading (starting)

---

### **BOTS Section**
- **Monitor Bot** — System health, alerts, metrics. Always active.
- **GitHub Bot** — Auto-pulls repos, manages branches. Disabled in Eco.
- **Security Bot** — Scans code, checks vulnerabilities. Disabled in Eco/Balanced.

**Toggle:** Enable/disable on-demand. Persists in config.

---

### **AI BACKENDS Section**
- **NVIDIA NIM** ☁️ — Free tier (40 req/min). Fastest cloud option. Default primary.
- **LM Studio** 🔌 — Local, offline. Respects GPU thermal gates (70-75°C). Primary in Eco.
- **Groq** ☁️ — Free, super-fast fallback. Used if NIM quota exhausted.
- **Gemini** ☁️ — Free, highest reasoning fallback. Last resort.

**Toggle:** Enable/disable. Reorder (see next section).

---

## 🧠 Intelligence Tier (Reorder the AI Fallback Chain)

**What it does:** Defines the order Jacky tries AIs. First enabled one wins.

**How to reorder:** Click any tier row to move it up. Example:

```
Current order (Balanced mode):
1. NVIDIA NIM (40 req/min, cloud)       ↑↓
2. LM Studio (offline, local, ~5 min)   ↑↓
3. Groq (free, cloud, fast)             ↑↓
4. Gemini (free, cloud, fallback)       ↑↓
```

**Click row 2 (LM Studio)** → moves up to position 1:
```
New order:
1. LM Studio (offline, local, ~5 min)   ↑↓
2. NVIDIA NIM (40 req/min, cloud)       ↑↓
3. Groq (free, cloud, fast)             ↑↓
4. Gemini (free, cloud, fallback)       ↑↓
```

Now Jacky tries LM Studio first (if GPU cool), then falls back to NIM.

**Jacky's auto-escalation:** If GPU ≥75°C, Jacky skips local and moves to next enabled cloud AI.

---

## ⚡ Quick Actions

### **🌡️ Check GPU Temp**
- Shows real-time RTX 3090 temperature
- Green (<70°C): Safe for local LM Studio
- Yellow (70-75°C): Local works but risky
- Red (≥75°C): Do NOT use local, escalate to cloud

### **📥 Pull Model from Ollama**
- Downloads new models (qwen2.5-coder:14b, whiterabbitneo, etc.)
- Takes 15-30 min for ~14GB models
- Monitor in "Local Models" card

### **⚙️ Open FCC Admin UI**
- Launches `http://127.0.0.1:8082/admin` in browser
- Configure NIM API key, switch model, apply changes
- Auto-restarts FCC Proxy

### **🛑 Stop All Servers**
- Gracefully stops Jacky, FCC Proxy, Ollama
- Use before shutdown
- Restart manually when needed

---

## 📊 Real-Time Feedback

Each action shows instant feedback in the **Action Feedback** line:
- 🟢 Green = Success
- 🟠 Orange = In progress
- 🔴 Red = Error

---

## 🔧 Under the Hood

### Keyboard Navigation
- **Preset buttons** at top: `[🌱 Eco]` `[⚖️ Balanced]` `[🚀 Performance]`
- **Toggles**: Click switch for on/off

### Persistence
- Config auto-saves to `E:\AI\Jacky\config.json`
- Power mode, tier order, bot states persist across restarts

### Thermal Protection (Built-In)
- If GPU hits 75°C, Jacky auto-disables local backends
- Automatically escalates to cloud AIs
- Re-enables local when GPU cools to <70°C
- No manual intervention needed

---

## 💡 Common Workflows

### **I want to code fast (urgent)**
→ Click `[🚀 Performance]`
→ FCC Proxy enables, all clouds ready, GitHub bot active
→ `fcc-claude.cmd` now uses NIM + Groq fallback

### **I want free, private work**
→ Click `[🌱 Eco]`
→ Ollama only, FCC disabled, GitHub bot off
→ Slower but zero cost & all data local

### **I want to test LM Studio locally first, fall back to cloud**
→ Click `[⚖️ Balanced]`
→ Click LM Studio row 1x to move it to position 1
→ Check GPU temp [🌡️ Check GPU Temp]
→ If green, LM Studio is primary; if too hot, auto-escalates to NIM

### **My GPU is overheating**
→ [🌡️ Check GPU Temp] shows red (≥75°C)
→ Power Panel auto-disabled LM Studio
→ Jacky auto-uses NIM cloud instead
→ Let GPU cool ~5 min
→ GPU cools, LM Studio re-enables automatically

---

## 🚨 Troubleshooting

| Issue | Fix |
|-------|-----|
| Server won't start | Check Windows firewall, port already in use? |
| GPU temp stuck high | Close other GPU apps (Chrome, Discord, etc.) |
| FCC Admin UI 404 | FCC Proxy not running; click toggle or `[🚀 Performance]` |
| Model pull stuck | Check internet speed, disk space (~20GB for two models) |
| Jacky not responding | Restart: Stop All → wait 5s → click `[⚖️ Balanced]` |

---

## 🎓 Mental Model

```
Your request
    ↓
Jacky (Brain) reads Power Panel settings
    ↓
Checks thermal gate: GPU temp OK?
    ├─ YES: Use AI tier #1
    └─ NO: Skip to tier #2+ (cloud)
    ↓
Route to selected AI backend (NIM, Groq, Gemini, or LM Studio)
    ↓
Get response, return to you
```

**Power Panel** = You configure the tiers and thermal rules.
**Jacky** = Intelligently executes them.

---

**Updated:** 2026-06-29 | **Power Panel UI:** SAS Dashboard

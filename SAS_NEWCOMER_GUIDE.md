# SAS — The Newcomer's Guide
### For someone brand new to this system *and* new to "cybernetic culture"

**Version:** 1.0 · **Date:** 2026-06-29 · **Status:** verified against a live run of the platform

---

## 0. Read this first (the 60-second mental model)

**SAS** = *Situation-Aware System*. It is your **own private AI command center** that runs **on your own PC**, for free, without sending your work to anyone else's cloud.

Think of it like this:

> You have a team of AI workers living on your computer. SAS is the **office building** they work in — with a front door (login), a control room (dashboard), and a meeting room (chat). A manager named **Jacky** decides which worker handles each job, and a safety officer watches the temperature of your graphics card so nothing melts.

That's it. Everything below is just detail on that one picture.

You do **not** need to code to use it. You type questions in a web page, like texting. The code only matters if you want to change how the workers behave.

---

## 1. The words people use here ("cybernetic culture" glossary)

This world has its own slang. Here's the plain-English version. Skim it once; come back when a word confuses you.

| Word you'll hear | What it actually means |
|---|---|
| **SAS** | The whole system. The "building" your AI team works in. |
| **Jacky** | The manager AI. It reads your request and routes it to the right worker. Also the project's name. |
| **Bot** | One AI worker with a job. You have 10 of them. |
| **Squad** | A team of bots that work together. You have 3 squads (Coding, Security, Archivist). |
| **Lead** | The head bot of a squad — the one who answers first. |
| **Local-first** | Always try to use the free AI *on your PC* before reaching for the paid internet AI. |
| **Ollama** | The program that runs the free AI models on your PC. SAS talks to it. If Ollama is off, the AI can't think. |
| **Model** | One "brain" the AI can use (e.g. `qwen2.5-coder`). Bigger = smarter but slower/hotter. |
| **Thermal gating** | A safety rule: if your graphics card gets too hot (limit **75°C**), SAS automatically backs off to protect the hardware. |
| **Situation Assessor** | The "safety officer" that checks CPU, memory, and GPU temperature before every job. |
| **Thinking mode** | How hard the AI works: **fast** (quick), **balanced**, or **deep** (slow but thorough). |
| **The Hub** | The main screen — roster of bots on the left, chat in the middle, live stats on the right. |
| **The Collector** | A background worker that quietly gathers and refines knowledge into a "graph" over time. |
| **Condenser** | The idea of squeezing knowledge down to its essence without losing meaning. There's a benchmark that scores how well a condenser does this. |
| **The loop** | The core cycle everything follows: **FETCH → FILTER → COMPRESS → INTERNALIZE → ACT → repeat**. (Gather info, keep the good parts, distill it, store it, use it, do it again.) |
| **Token** | Your password to get into SAS. Kept in a "vault" (a secrets file), never typed in public. |
| **SAS Comms** | A special mode that unlocks a "Claude Code" expert personality. Off by default. |

> **The one cultural idea to absorb:** this system prefers **free, local, and safe** over fast-and-expensive. It would rather use the AI on your own machine, protect your graphics card, and keep your data private — even if that's a little slower. That value (privacy + self-reliance + not wasting money) *is* the culture.

---

## 2. Before you start (the checklist)

You need three things ready:

1. **Python 3.11+** installed. (You have it — verified 3.11.1.)
2. **Ollama** installed and **running**, with at least one model pulled. *This is the #1 thing newcomers forget.* No Ollama = the AI can't answer (you'll get a polite "service unavailable").
3. **Your SAS login token** — already saved in your secrets vault. You don't need to memorize it; the system reads it for you.

---

## 3. Starting SAS — step by step

Do these **in order**. Order matters.

### Step 1 — Start the AI engine (Ollama)
Open a terminal and run:
```bash
ollama serve
```
Leave that window open. Then make sure you have a model (one time only):
```bash
ollama pull qwen2.5-coder:14b      # a good coding model
ollama list                         # confirm it shows up
```

### Step 2 — Start SAS
Either **double-click `Start_Jacky.cmd`** in `E:\AI\Jacky\`, **or** in a terminal:
```bash
cd E:\AI\Jacky
python serve.py        # production server (recommended)
```
You'll see a banner ending with `Auth: ENABLED`. That's good — it means your login is protecting the system.

### Step 3 — Open it in your browser
Go to:
```
http://localhost:5000/dashboard
```

### Step 4 — Log in
You'll see a login box. Paste your **SAS token**. You're in.

> **Putting SAS on your phone / the internet:** that's what `Start_SAS_Public.cmd` is for — it also starts a secure Cloudflare tunnel. Use the local steps above until you're comfortable.

---

## 4. The three screens (what each one is for)

| Screen | URL | What you do there |
|---|---|---|
| **Dashboard** | `/dashboard` | The control room. See CPU/GPU/memory, the safety status, toggle the team on/off, set thinking mode. |
| **Hub** | `/hub` | The main workspace. Pick a squad on the left, chat in the middle, watch live stats on the right. |
| **Chat** | `/chat` | Just the conversation, full-screen. Good for focused back-and-forth. |

Start in the **Hub**. It's the cockpit.

---

## 5. Your first 10 minutes (do these in order)

1. **Check the safety light.** On the dashboard, find the status badge. **"Safe"** (green) means your GPU is cool and local AI is good to go. *(On a real run it read: GPU 56°C, 75°C cap, 19°C headroom → Safe.)*
2. **Ask one question.** In the Hub, click the **Coding** squad, type *"write a Python function to reverse a list"*, press Enter. The **Lead** bot answers.
3. **Get a second opinion.** Turn on **"All Reply"** and ask again — now every bot in the squad responds. Use this for design decisions.
4. **Try the safe shell.** Click the `PS>` button and type `Get-Date`. SAS runs it. Now try `Remove-Item C:\something` — it's **blocked**. (Only safe, read-only commands are allowed.)
5. **Watch the Collector.** Open the Collector area, hit **Collect Now** once. You'll see it FETCH → FILTER → COMPRESS → INTERNALIZE → ACT and grow its knowledge graph. *(Verified: 20 items in → 19 refined nodes stored.)*

If all five worked, your system is healthy.

---

## 6. The safety systems (and why they're not optional)

SAS protects you in three ways. Don't disable them.

- **Thermal gating (75°C cap).** Your RTX 3090 throttles itself to avoid damage. SAS watches the temperature and, if it climbs, switches to smaller models or pauses. This is why the system sometimes feels cautious — it's guarding a £/$ thousand piece of hardware.
- **Login (auth).** The token gate keeps strangers out, which matters the moment SAS faces the internet. It turns on automatically whenever a token exists.
- **Shell whitelist.** The `PS>` command box only allows safe, read-only commands (`Get-*`, `ls`, `git status`, `python`, etc.). Anything that deletes, formats, or changes system settings is refused. This is deliberate.

---

## 7. The knowledge engine (Collector + Condenser)

This is the "gets smarter over time" part.

- **The Collector** runs the loop in the background: it gathers data (your memory files, system state, project files), keeps only the novel/durable bits, distills them, and files them into a **knowledge graph** stored at `E:\AI\Jacky\data\`. Start it, and it quietly builds a memory of your world.
- **The Condenser Benchmark** is a *test* of how well a knowledge-squeezer works. Run it to get a score:
  ```bash
  python condenser_benchmark.py            # baseline scores ~0.65
  python condenser_adversary.py            # tests it against an attacker
  ```
  You don't need these to use SAS day-to-day. They exist so the "smarter over time" machinery can be measured and improved, not just hoped at.

---

## 8. Troubleshooting (real symptoms → real fixes)

| What you see | What it means | Fix |
|---|---|---|
| AI replies **"service unavailable" / 503** with a "fallback chain" | The AI engine isn't reachable. The message literally says why: *"No local models pulled"* and *"cloud disabled"*. | Start Ollama (`ollama serve`) and pull a model (`ollama pull ...`). This is the #1 newcomer issue. |
| Browser says **"unauthorized"** or kicks you to login | You're not logged in (or the session expired). | Go to `/login`, paste your token again. |
| Page won't load at all | The server isn't running. | Start it: `python serve.py` in `E:\AI\Jacky`. |
| Bot is **very slow** | GPU is hot or the model is large. | Check the badge; switch **thinking mode** to **fast**; or use a smaller model. |
| `PS>` command **"blocked"** | The command isn't on the safe list. | That's intentional. Ask the Coding squad how to do it safely instead. |
| Collector shows **0 nodes** | Nothing collected yet, or the memory folder is empty. | Hit **Collect Now**; make sure `C:\Users\93jes\.claude\...\memory` has files. |
| Dashboard shows **GPU temp climbing toward 75°C** | Heavy load. | Let it cool; SAS will auto-throttle. Avoid running many big models at once. |

> **Golden rule:** 90% of "it's broken" moments are just **Ollama isn't running**. Check that first, every time.

---

## 9. Cheat sheet (print this)

```
START:   1) ollama serve     2) python serve.py     3) open localhost:5000/dashboard   4) log in
SCREENS: /dashboard (control)   /hub (work)   /chat (talk)
ASK:     Hub → pick squad → type → Enter   (Lead answers; "All Reply" = whole squad)
SAFE:    GPU cap 75°C · login required · shell is read-only only
MODES:   fast (quick) · balanced · deep (thorough)
FIXIT:   "service unavailable" = start Ollama + pull a model
HEALTH:  python -c "import jacky_api" should print 'Engine ready'
```

---

## 10. Where things live (file map)

```
E:\AI\Jacky\
  serve.py              <- start THIS for production
  jacky_api.py          <- the brain of the web service (all the endpoints)
  jacky_core.py         <- the manager logic (routing jobs to bots)
  situation_assessor.py <- the safety officer (reads GPU temp)
  squad_manager.py      <- loads the 10 bots, injects your memory into them
  data_collector.py     <- the background knowledge collector
  condenser_benchmark.py / condenser_adversary.py  <- knowledge-squeezer tests
  config.json           <- the dials (thinking mode, power mode, which bots are on)
  bots\*.json           <- the 10 bot personalities (edit these to change behavior)
  sas_ui\               <- the web pages (dashboard.html, hub.html, chat.html)
  data\                 <- the knowledge graph + results live here

H:\AI_ARCHIVE\          <- long-term backups, guides, corpora
```

Want to change a bot's personality? Edit its file in `bots\`, then in the Hub hit **reload** (or call `/api/squads/reload`). No restart needed.

---

## 11. Future-proofing notes (so it keeps working)

- **Keep Ollama models updated** occasionally: `ollama pull <model>` refreshes them.
- **Back up `E:\AI\Jacky\data\`** (the knowledge graph) — it's the only part that grows and can't be regenerated.
- **Don't commit secrets.** The token and API keys live in the vault and are git-ignored. Never paste them into a file you share or push.
- **The system degrades gracefully on purpose.** If Ollama is down, cloud is off, or the GPU is hot, SAS tells you *why* instead of crashing. Read the message — it's designed to guide you.
- **One concept runs through everything:** the loop (FETCH → FILTER → COMPRESS → INTERNALIZE → ACT). Bots, the collector, even the benchmark are all instances of it. Once that clicks, the whole system stops feeling like separate parts.

---

*You don't have to understand the code to run SAS. Start Ollama, start the server, log in, and talk to your squad. Everything else you can learn one piece at a time.*

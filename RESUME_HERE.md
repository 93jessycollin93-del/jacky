# RESUME HERE — Jacky / SAS handoff

**Saved:** 2026-06-28, just before a planned shutdown.
**Paste-to-Claude prompt:** `E:\AI\_RESUME_PROMPT.txt`

---

## Where things stand

### DONE ✅
- **Jacky v1.1 engine** — situation-aware routing (GPU thermal gating, CPU/RAM
  assessment), simplified to 2 named cloud bots (jacky/Gemini, claude_jr/Haiku)
  + free escalation tier (Groq→Gemini→OpenRouter). xAI/Johnny/Onslaught removed.
- **SAS = secure internet PWA** — token login, waitress prod server (`serve.py`),
  Cloudflare tunnel, installable on phone. Verified live over the internet.
- **Daily tools** — `daily_workflow.py`, `efficiency_check.py` (CSV trend log).
- **Git repo initialized** at `E:\AI\Jacky` (2 commits). NOT pushed yet.
  GitHub username: **93jessycollin93-del**. Token in `.env` is a placeholder.

### IN PROGRESS ⏳ (resume on restart)
Model downloads were running when we shut down. `ollama pull` RESUMES from cache,
so just re-run the script. Status at shutdown:
- `nomic-embed-text` (274 MB) — was ~38%
- `whiterabbitneo` (~7.5 GB) — pending
- `deepseek-r1:14b` (~8 GB) — pending
- `gpt-oss:20b` (~11.5 GB) — pending

Re-run: `cd E:\AI\Jacky && bash pull_models.sh` (background). Check `ollama list`.

### KNOWN ISSUE
Downloads crawl at ~0.9 MB/s because the **AV/VPN intercepts HTTPS** (same MITM
that broke pip/winget). Pausing the VPN/AV makes it fast. User's call.

---

## To bring SAS back online
1. `Start_SAS_Public.cmd` (double-click) → starts Ollama + server + tunnel,
   prints a NEW `*.trycloudflare.com` URL (changes each restart).
2. Login token: `secrets\secrets.env` → `SAS_ACCESS_TOKEN`.
3. Permanent URL `sas.cybernetic67.com` not set up yet — see `TUNNEL_SETUP.md`
   (needs a one-time Cloudflare browser login the user must approve).

## Key files
| File | Role |
|---|---|
| `serve.py` | Production server (use this for internet, not jacky_api.py) |
| `Start_SAS_Public.cmd` | One-click: Ollama + server + tunnel |
| `pull_models.sh` | Sequential model downloads (resumable) |
| `pull_models.log` | Download progress log |
| `TUNNEL_SETUP.md` | Quick + permanent tunnel setup |
| `OPERATIONAL_GUIDE.md` | Daily routine, metrics, troubleshooting |
| `ARCHITECTURE.md` | Engine deep-dive |
| `GITHUB_SETUP.md` | Push steps (username already filled in) |
| `secrets\secrets.env` | Vault: SAS token, API keys (gitignored) |

## Open follow-ups
- [ ] Finish 4 model downloads
- [ ] (optional) Push repo to github.com/93jessycollin93-del/jacky (needs real token)
- [ ] (optional) Permanent sas.cybernetic67.com tunnel
- [ ] (optional) Add free cloud keys (Groq/Gemini/OpenRouter) to the vault —
      currently placeholders, so the free fallback tier is dormant

# Coding Agent Tier — Free Claude Code Proxy

**Status:** WIP — setup complete, TLS workaround pending (known, documented)  
**Location:** `E:\AI\free-claude-code` (upstream: [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code) commit `478e966`)  
**Part of:** AI Foundry v1.1, Jacky's "hands" (CLI agent; Jacky's router is the "brain")

---

## What it is

A proxy server that runs the **Claude Code CLI agentic harness** (file edits, shell commands, tool use) against:
- **Default:** NVIDIA NIM free tier (40 req/min, `nvidia_nim/kimi-k2.5`, `nvidia_nim/glm5.1`, etc.)
- **Optional (local):** LM Studio or llama.cpp when the GPU is cool enough (≥75°C = stop, ≥70°C = warm)

Keeps **your paid Claude Code CLI untouched** — the proxy env vars are scoped to a child process, never polluting your main shell.

---

## Quick start

### 1. Get a free NVIDIA NIM key
- Sign up: https://build.nvidia.com
- Generate API key (40 req/min free)
- You'll paste it in step 3

### 2. Start the proxy (manual only)
```
cd E:\AI\free-claude-code
Start_FreeCC_Server.cmd
```
Leaves a window open. Opens `http://127.0.0.1:8082/admin` in your browser.

### 3. Configure NIM (Admin UI)
- Paste your NVIDIA NIM API key into `NVIDIA_NIM_API_KEY`
- `MODEL` is set to `nvidia_nim/moonshotai/kimi-k2.5` by default (change if you prefer GLM 4.7 etc.)
- Click **Validate → Apply**
- Server auto-restarts

### 4. Launch Claude Code against the proxy
From your project folder:
```
fcc-claude.cmd
```
This spawns `claude` with `ANTHROPIC_BASE_URL=localhost:8082` — your actual paid CLI is never touched.

---

## Thermal gate for local backends (optional)

If you want to use LM Studio (offline, no cloud quota):

1. Check GPU temp:
```powershell
Check_GPU_Before_Local.ps1
```
   - **OK** (< 70°C): safe to use local
   - **WARM** (70–75°C): prefer NIM, local is risky
   - **STOP** (≥ 75°C): do NOT use local, let it cool

2. In Admin UI, set `MODEL` to `lmstudio/<model-name>` (e.g., `lmstudio/qwen3.5-coder`)

3. Launch: `fcc-claude.cmd`

4. When done, flip back to `nvidia_nim/...` in Admin UI

---

## Known issue: uv applink crash

**Current state:** TLS shim (`sitecustomize.py`) works standalone (verified: direct HTTP 200 to NIM), but uv's Python entry point still crashes with "no OPENSSL_Applink" on cert file loads during startup.

**Root cause:** uv's standalone CPython on Windows + OpenSSL file BIO load (certifi) = applink crash, compounded by Avast HTTPS interception (requires OS cert store, not file certs).

**Workaround (ready, not yet deployed):**
- Direct truststore context verified to work (no file BIO, uses Windows store, passes Avast)
- Need to bypass uv entry point or use `UV_PYTHON_PREFER_FROZEN` / custom launcher
- Tracked as: "TLS workaround — uv applink" (next PR)

**To test once fixed:** see Verification section below.

---

## Architecture

```
Your project folder
  ↓
fcc-claude.cmd launcher (scoped env vars, child process)
  ↓
proxy (localhost:8082)
  ├─ DEFAULT: NVIDIA NIM cloud (40 req/min free)
  ├─ OPTIONAL: LM Studio local (offline, if GPU cool)
  └─ Admin UI (127.0.0.1:8082/admin)
```

---

## Files

| File | Purpose |
|------|---------|
| `Start_FreeCC_Server.cmd` | Launch proxy manually (manual-only, like Jacky) |
| `fcc-claude.cmd` | Launch Claude Code with proxy env (use from your project folder) |
| `Check_GPU_Before_Local.ps1` | Pre-flight check: is GPU cool enough for local LM Studio? |
| `.venv/Lib/site-packages/sitecustomize.py` | TLS shim (truststore + Windows cert store) |

---

## Verification (once TLS is fixed)

1. **Proxy health:** `Start_FreeCC_Server.cmd` + open `http://127.0.0.1:8082/admin` → should render
2. **Paid session safe:** in a normal terminal, `echo $env:ANTHROPIC_BASE_URL` is empty (untouched)
3. **NIM path:** `fcc-claude.cmd` → ask it a one-liner; confirm proxy log shows `nvidia_nim/...` route
4. **Local path:** `Check_GPU_Before_Local.ps1` (OK), flip Admin UI `MODEL` to `lmstudio/<model>`, `fcc-claude.cmd` → confirm route to `lmstudio/...` offline
5. **Thermal gate:** confirm pre-flight refuses local when GPU ≥75°C

---

## Constraints

- **Manual-start only:** no auto-boot (matches Foundry v1.1 ops policy)
- **No global env changes:** proxy env is scoped per invocation (protects your real Claude Code)
- **Thermal gated:** local backend reuses Jacky's thresholds (70°C / 75°C from config.json)
- **Secrets:** NIM key lives in `~/.fcc/` (gitignored; separate from Jacky vault)
- **No Telegram/Discord:** messaging disabled (free-claude-code optionally supports it, but not wired here)

---

## Dependencies

- `uv ≥0.11.0` (installed globally; manages isolated Python 3.14 + deps)
- Python 3.14 (provisioned by uv, doesn't touch system 3.11)
- truststore (OS cert store, handles Avast HTTPS interception)
- Standard: fastapi, uvicorn, httpx, openai SDK, pydantic, etc.

---

## Pinned version

**free-claude-code v2.4.0, commit `478e966`** (June 28, 2026)

To update, re-run `uv sync` in the repo directory.

---

**Frame:** Jacky is the brain (router, decision maker). Claude Code CLI (via this proxy) is the hands (agent that edits, runs tests, refactors code). Ollama ensemble stays the training partner (free exploration, specialized locals).

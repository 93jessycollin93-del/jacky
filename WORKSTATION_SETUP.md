# Workstation Setup & Operating Guide

How to run the Jacky project from your Windows PC: get **Claude Code inside
VS Code**, point it at your **free NIM proxy**, check your **hardware/drives**,
and keep **hourly auto-saves committed to GitHub** so nothing is ever lost.

> **About "connect to my PC / take over":** no remote agent can or should silently
> control your machine — that's how malware works, not this. Instead, the tools
> below run *on your PC, started by you*, and commit to GitHub automatically.
> You stay in control; you can stop any of it at any time.

---

## 1. Claude Code in VS Code (your three windows)

You have three VS Code windows open: a **Codespace**, an **"Agents"** folder, and
a fresh **Welcome** window. Install the extension once per *place*:

### Install the extension
1. In VS Code, open **Extensions** (`Ctrl+Shift+X`).
2. Search **"Claude Code"** (publisher: **Anthropic**) and click **Install**.
3. Launch with **`Ctrl+Esc`**, or the Claude icon in the sidebar.

### Per-window notes
| Window | Where the extension installs | What to do |
|--------|------------------------------|------------|
| **Local "Agents" folder** | On your **PC** | Install normally (steps above). Open the folder with **File → Open Folder**. |
| **Codespace** (cloud) | **Inside the Codespace**, not your PC | With the Codespace window focused, the Extensions panel shows an **"Install in Codespace"** button — use that. Local installs don't carry over. |
| **Welcome window** | n/a until you open a folder | **File → Open Folder** → pick `E:\AI\Jacky` (or clone of this repo), then it behaves like the local case. |

> Tip: open this very project (`E:\AI\Jacky`) in one window so Claude Code has the
> repo context — the same files that are on GitHub.

---

## 2. Point Claude Code at the free NIM proxy

The free coding tier (NVIDIA NIM, 40 req/min) is already documented in
**[`CODING_AGENT_TIER.md`](CODING_AGENT_TIER.md)** — start the proxy with
`Start_FreeCC_Server.cmd` and configure your key at `http://127.0.0.1:8082/admin`.

To make **VS Code's integrated terminal** use the proxy for `claude`:

- **Easiest:** from the project folder in the VS Code terminal, run your existing
  `fcc-claude.cmd` launcher. It sets `ANTHROPIC_BASE_URL=http://127.0.0.1:8082`
  for that **child process only** — your paid Claude Code CLI is never touched.
- **Per-terminal (manual):**
  ```powershell
  $env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8082"
  claude
  ```
  Closing the terminal clears it. **Do not** set this globally — keeping it scoped
  is what protects your paid CLI (see the constraints in `CODING_AGENT_TIER.md`).

> The bundled **VS Code extension** uses your normal (paid) Claude Code login.
> Use the **terminal + `fcc-claude.cmd`** path when you want the free NIM route.

---

## 3. Check your hardware and drives (G: / H:)

I can't read your PC from the cloud, so run this read-only script and paste the
summary back — then we'll do the "how to operate my PC" walkthrough with real
numbers.

```powershell
pwsh -File tools/Check_Workstation.ps1
```

It reports CPU, RAM, GPU (with the **70 °C warm / 75 °C stop** thermal gate), and
**every drive including G: and H:** with free space. A full copy is written to
`workstation_report.txt` (gitignored, stays on your machine).

---

## 4. Hourly saves + GitHub commits (never lose work)

Two layers, different jobs:

- **VS Code file auto-save** (saves files to disk as you type):
  `File → Preferences → Settings` → search **`files.autoSave`** → set
  **`afterDelay`**. This does *not* touch git.
- **Git snapshots** (commit + push to GitHub) — the scripts in `tools/`:

### Turn on hourly auto-commit (opt-in, run once)
```powershell
pwsh -File tools/Register_AutoSave_Task.ps1
```
This registers a Windows Scheduled Task **`JackyAutoSave`** that, every hour:
1. stages everything (`git add -A`),
2. commits `chore(autosave): snapshot <timestamp>` **only if there are changes**,
3. pushes to your **current branch** on GitHub (with retry/backoff for flaky Wi-Fi).

Nothing runs until you register it — matching the "manual-start only" ops policy.

### Save right now (before you stop working)
Double-click **`Save_Now.cmd`** (repo root), or:
```powershell
pwsh -File tools/autosave.ps1            # commit + push
pwsh -File tools/autosave.ps1 -NoPush    # commit locally only
```

### Change interval / stop it
```powershell
pwsh -File tools/Register_AutoSave_Task.ps1 -IntervalMinutes 30   # e.g. every 30 min
pwsh -File tools/Unregister_AutoSave_Task.ps1                     # turn it OFF
```

> **"Anytime anyone works on it":** with the task registered, every machine that
> has the repo + the task does its own hourly snapshot to the same branch. Each
> person should `git pull` when they sit down so they build on the latest push.
> Activity is logged to `autosave.log` (gitignored).

---

## 5. Daily operating rhythm

1. **Start the proxy** (if using free tier): `Start_FreeCC_Server.cmd`.
2. **Open the project** in VS Code (`E:\AI\Jacky`); `git pull` first.
3. **Work** — Claude Code in the sidebar (paid) or `fcc-claude.cmd` in the
   terminal (free NIM).
4. **Snapshots happen automatically** every hour once `JackyAutoSave` is on.
5. **Before shutdown**, double-click **`Save_Now.cmd`** for a final push.

---

## Files added by this guide

| File | Purpose |
|------|---------|
| `tools/Check_Workstation.ps1` | Hardware + drive (incl. G:/H:) report |
| `tools/autosave.ps1` | Snapshot engine: stage, commit, push |
| `tools/Register_AutoSave_Task.ps1` | Turn on hourly auto-save (opt-in) |
| `tools/Unregister_AutoSave_Task.ps1` | Turn it off |
| `Save_Now.cmd` | One-click manual snapshot |

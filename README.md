# JACKY - AI Operations Manager

**Frame:** It's Jacky's PC. You learn from Jacky.

Jacky is your **AI-driven system manager** that keeps everything organized, monitors your projects and assets, alerts you to problems, and teaches you about the systems you're using.

## What Jacky does

1. **Manages your PC** — monitors GPU, RAM, CPU, disk, processes
2. **Orchestrates bots** — decides how many bots needed for each task (1? 3 in parallel?)
3. **Monitors projects** — GitHub, local files, branches, PRs, model downloads
4. **Alerts & educates** — tells you what's happening AND explains why
5. **SAS Dashboard** — one place to see everything at a glance

## Quick Start

### 1. Install dependencies
```bash
cd E:\AI\Jacky
pip install -r requirements.txt
```

Or just run the launcher (it does this automatically):
```bash
Start_Jacky.cmd
```

### 2. Start Jacky
```bash
python jacky_core.py
```

Or double-click:
```
Start_Jacky.cmd
```

### 3. Open the SAS Dashboard
Once Jacky starts, open your browser to:
```
http://localhost:5000/dashboard
```

## Project Structure

```
E:\AI\Jacky\
├── jacky_core.py          ← Main orchestrator (the boss)
├── bots/                  ← Bot modules (pluggable)
│   ├── monitor_bot.py     ← System health
│   ├── github_bot.py      ← GitHub management
│   └── security_bot.py    ← Coming soon
├── sas_ui/                ← SAS Dashboard
│   └── dashboard.html     ← Web interface
├── data/                  ← State, logs, metrics
│   └── jacky.db          ← SQLite database
├── config.json            ← Configuration
├── requirements.txt       ← Python dependencies
└── README.md             ← This file
```

## Configuration

Edit `config.json` to customize:
- Max concurrent bots
- Resource limits (CPU, memory, GPU)
- Alert thresholds
- Enabled bots
- Integrations (GitHub, Ollama, local file system)

## Creating Custom Bots

Jacky auto-discovers bots. To add one:

1. Create `bots/my_bot.py`:
```python
class MyBot:
    def __init__(self):
        self.name = "my_bot"
    
    def handle_task(self, task):
        # Do your thing
        return result
```

2. Add `"my_bot"` to `enabled_bots` in `config.json`

3. Jacky will find it on next start.

## How Jacky decides resource allocation

Given a task, Jacky:
1. Analyzes the task (complexity, deadline, type)
2. Checks available resources (CPU, RAM, GPU, I/O)
3. Estimates time if 1 bot vs 2 vs 3 vs 4 run in parallel
4. Picks the allocation that best matches your preferences
   - **"speed"** → use more bots, parallel processing
   - **"cost"** → use fewer bots, sequential
   - **"balanced"** → middle ground

## Alerts & Education

When something needs attention, Jacky alerts you AND explains why:

```
⚠️ GPU Memory Check Failed
   RTX 3090 not responding to nvidia-smi query

💡 What this means:
   GPU drivers might need updating, or a process is locking it.
   Jacky is retrying the check every 30 seconds.
```

This way, you're not just getting alerts — you're learning how systems work.

## SAS Dashboard

The **Situational Awareness Security** dashboard shows:
- **System metrics** (CPU, RAM, GPU, disk)
- **Bot pool status** (which bots are idle/busy/error)
- **Task queue** (what's waiting)
- **Alerts** (with education)
- **Project status** (cyber-store, ERU, etc.)

Open it in your browser: `http://localhost:5000/dashboard`

## API

Jacky exposes a REST API for integration:

```bash
# Get system status
curl http://localhost:5000/api/status

# Submit a task
curl -X POST http://localhost:5000/api/task \
  -H "Content-Type: application/json" \
  -d '{"name":"run_tests","priority":"high"}'

# Get bot status
curl http://localhost:5000/api/bots
```

## Advanced: Integration with Local Models

Jacky can monitor your Ollama models on E:\AI\Ollama\models:
- Tracks download progress
- Alerts if downloads fail
- Suggests which model to use based on task complexity
- Monitors GPU allocation

## Troubleshooting

**Jacky won't start:**
- Check Python 3.11+ is installed: `python --version`
- Check port 5000 is available
- Check `E:\AI\Jacky\data\` exists (Jacky creates it)

**Bots not discovered:**
- Make sure bot file is in `bots/` folder
- Make sure bot class is named correctly
- Check `config.json` has bot listed in `enabled_bots`

**SAS Dashboard not loading:**
- Check `sas_ui/dashboard.html` exists
- Try `http://localhost:5000` (might not have `/dashboard` route yet)

## Next Steps

1. **Monitor Bot** — watch your system and learn about it
2. **GitHub Bot** — manage your repos and branches
3. **Security Bot** — audit permissions and vulnerabilities
4. **Memory Manager** — orchestrate your storage across drives
5. **Custom Bots** — add your own for specialized tasks

---

**Frame:** It's Jacky's PC. You're the user. Jacky is in charge, and you're learning.

---

## 🤖 OmniAgent — Autonomous AI Agent Layer

OmniAgent is a fully-equipped autonomous agent built on top of Jacky,
giving GitHub Copilot (and any MCP-compatible client) access to **all
essential tools, skills, and integrations** in one place.

### Features

| Category | What's included |
|----------|----------------|
| **Tool calling** | File ops, shell commands, web fetch/search, GitHub API, code search |
| **MCP integration** | `jacky-mcp-server` + filesystem + GitHub MCP servers |
| **Skills system** | Reusable `*.skill.md` files with YAML front-matter |
| **Specialist agents** | Coder, Researcher, Tester, DevOps, Accessibility |
| **Reasoning** | ReAct, Plan-and-Execute, Tree-of-Thoughts frameworks |
| **CI/CD** | GitHub Actions: agent task trigger, lint, test, nightly health check |
| **Safety** | Path sandboxing, shell allowlist, secret scanning, thermal gating |

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set env vars (copy and fill in)
cp .env.template .env

# 3. Run the test suite (agent tools + skills)
python -m pytest tests/agent_tests/ -v

# 4. Try an example
python examples/use_file_ops.py
python examples/invoke_skill.py skills/web-research.skill.md
```

### Invoking OmniAgent (GitHub Copilot)

```
# Simple task
@OmniAgent fix the null-pointer in jacky_core.py line 42

# Research
@OmniAgent run skill: web-research query="best local LLM for coding 2025"

# End-to-end feature
@OmniAgent implement a /healthz endpoint, add a test, open a PR
```

### Available Agents

| Agent | File | Role |
|-------|------|------|
| OmniAgent | `.github/agents/omniagent.agent.md` | Top-level orchestrator |
| CoderAgent | `agents/coder.agent.md` | Code implementation & review |
| ResearcherAgent | `agents/researcher.agent.md` | Web research & documentation |
| TesterAgent | `agents/tester.agent.md` | Test writing & QA |
| DevOpsAgent | `agents/devops.agent.md` | CI/CD, Docker, deployment |
| AccessibilityAgent | `agents/accessibility.agent.md` | WCAG 2.1 AA audits |

### Available Skills

| Skill | File | Description |
|-------|------|-------------|
| web-research | `skills/web-research.skill.md` | Multi-source research → report |
| code-refactor | `skills/code-refactor.skill.md` | Safe incremental refactoring |
| add-feature | `skills/add-feature.skill.md` | Feature: design → code → PR |

### MCP Server

Configure in `mcp-servers/mcp-config.json`. Exposes:
- `jacky_route_task` — route to cheapest capable model
- `jacky_get_system_status` — GPU temp, CPU, RAM
- `jacky_list_models` — available Ollama models

See [docs/omniagent-architecture.md](docs/omniagent-architecture.md) for the
full architecture diagram and routing decision tree.

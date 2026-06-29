# Superagent Workspace Setup — GODZILLA PC
**Owner:** 93jessycollin93-del  
**Date:** 2026-06-29  
**Status:** CANONICAL — do not modify without authorization

---

## DRIVE ALLOCATION MAP

| Drive | Label | Purpose | Access |
|-------|-------|---------|--------|
| **E:\\** | PRIMARY | Active bot data, live datasets, Jacky workspace, condenser stars | Superagent + Owner |
| **G:\\** | BACKUP | Bot backups, future needs, redundant condenser state | Superagent + Owner |
| **V:\\** | ARCHIVE | Project archives, dataset snapshots, episodic memory | Superagent + Owner |
| **H:\\** | DATASETS | HuggingFace training datasets (100GB cap) | Superagent + Owner |

---

## FOLDER STRUCTURE (E:\\ PRIMARY)

```
E:\
└── superagent\                   ← ROOT — Superagent exclusive workspace
    ├── jacky\                    ← Jacky Python engine (git clone)
    │   ├── bots\                 ← Bot modules (condenser_bot.py, etc.)
    │   ├── data\                 ← SQLite stars DB + logs
    │   └── .env                  ← Local config (VITE_JACKY_URL, etc.)
    ├── condensers\               ← All 52 repos cloned here
    │   ├── neutronknowledge\     ← BASELINE ☉ (never modify engine)
    │   ├── signal-refiner\
    │   ├── express-purely\
    │   └── [all others...]\
    ├── datasets\                 ← Symlink to H:\datasets
    ├── logs\                     ← All agent action logs
    │   ├── calibration\
    │   ├── episodic\
    │   └── errors\
    ├── memory\                   ← Agent memory files
    │   ├── working\              ← Current session state
    │   ├── episodic\             ← Past session logs
    │   ├── semantic\             ← Knowledge catalogue
    │   └── procedural\           ← Rules, calibration policy
    └── scripts\                  ← Utility scripts
        ├── godzilla_dataset_downloader.py
        ├── clone_all_repos.sh
        └── start_jacky.bat
```

## FOLDER STRUCTURE (G:\\ BACKUP)

```
G:\
└── superagent_backup\
    ├── condensers_backup\        ← Daily snapshot of E:\condensers
    ├── stars_backup\             ← SQLite DB backup
    └── logs_backup\              ← Log archive
```

## FOLDER STRUCTURE (V:\\ ARCHIVE — 980 Pro Samsung 1TB)

```
V:\
└── superagent_archive\
    ├── phase_reports\            ← Phase 1/2/3/4 reports
    ├── catalogue\                ← Asset catalogue versions
    ├── dataset_snapshots\        ← Dataset download manifests
    └── memory_snapshots\         ← Episodic memory exports
```

## FOLDER STRUCTURE (H:\\ DATASETS)

```
H:\
└── datasets\
    ├── coding\
    │   ├── starcoder-python-instruct\
    │   ├── verifiable-coding-problems\
    │   └── vibe-coding-instruct\
    ├── security\
    │   ├── cve-coding-nova\
    │   └── cybersecurity-help\
    ├── emotion\
    │   ├── go-emotions\
    │   └── emotion-nlp\
    ├── language\
    │   └── opus-100\
    ├── reasoning\
    │   └── logical-math-coding-sft\
    ├── baseline\
    │   └── fineweb-edu-sample\
    ├── _dataset_index.md
    └── _download_log.txt
```

---

## ACCESS LAW

> **Only Superagent and 93jessycollin93-del may read or write to E:\superagent\, G:\superagent_backup\, V:\superagent_archive\, and H:\datasets\.**  
> No other process, user, or application has authorization.  
> This is enforced at folder permissions level (Windows ACL: remove Everyone, add only the active user account).

### Windows ACL setup (run once as Administrator):

```batch
icacls E:\superagent /inheritance:r /grant "%USERNAME%":F /T
icacls G:\superagent_backup /inheritance:r /grant "%USERNAME%":F /T
icacls V:\superagent_archive /inheritance:r /grant "%USERNAME%":F /T
icacls H:\datasets /inheritance:r /grant "%USERNAME%":F /T
```

---

## QUICK START (on GODZILLA)

1. **Clone Jacky:**
   ```batch
   cd E:\superagent
   git clone https://github.com/93jessycollin93-del/jacky.git
   cd jacky && pip install -r requirements.txt
   ```

2. **Clone all condensers:**
   ```batch
   cd E:\superagent\condensers
   for /f %r in (repos.txt) do git clone https://github.com/93jessycollin93-del/%r.git
   ```

3. **Download datasets (100GB cap, H: drive):**
   ```batch
   python E:\superagent\scripts\godzilla_dataset_downloader.py
   ```

4. **Start Jacky:**
   ```batch
   cd E:\superagent\jacky
   python jacky_core.py
   ```

5. **Set env vars for all condensers (.env.local):**
   ```
   VITE_JACKY_URL=http://localhost:5000/api/ask
   VITE_OLLAMA_URL=http://localhost:11434
   VITE_OLLAMA_MODEL=llama3.2
   ```

---

## MEMORY TIERS (4-Layer Architecture)

| Tier | Location | What it holds | Retention |
|------|----------|---------------|-----------|
| **Working** | E:\superagent\memory\working\ | Current session, active task state | Session |
| **Episodic** | E:\superagent\memory\episodic\ | Past actions, decisions, logs | Permanent |
| **Semantic** | E:\superagent\memory\semantic\ | Knowledge catalogue, specialization map | Permanent |
| **Procedural** | E:\superagent\memory\procedural\ | Rules, calibration policy, access law | Permanent |

---

## CONDENSER SPECIALIZATION MAP

| Symbol | Specialization | Repo | Status |
|--------|---------------|------|--------|
| ☉ | BASELINE (locked) | neutronknowledge | ✅ WORKING |
| ♀ | Emotion/resonance | quiet-heart-signal | ✅ WORKING |
| ♂ | Conflict/coding | tension-tamer | ✅ WORKING |
| ♃ | Knowledge expansion | apex-intelligence-hub | ✅ SCAFFOLDED |
| ♄ | Memory/structure | neutronstar | ✅ ENGINE WIRED |
| ☿ | Communication/language | signal-weaver-23 | ✅ SCAFFOLDED |
| ♆ | Streaming/density | neutron-core-stream | ✅ FIXED |
| ♇ | Relationship | relational-compass | ✅ WORKING |
| ⚶ | Security | veil-ops / dakura | ⏳ PENDING |
| ⚸ | Analysis | fobccc / dakura | ✅ WORKING |
| ♅ | Orchestration | bot-squad-dynamics | ✅ WORKING |
| ☽ | Episodic memory | logbook-curator | ✅ WORKING |

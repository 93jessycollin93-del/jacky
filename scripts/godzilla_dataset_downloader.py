#!/usr/bin/env python3
"""
GODZILLA AI Dataset Downloader
Author: Superagent (for 93jessycollin93-del)
Target: H:\\datasets\\ (GODZILLA PC, Drive H:)
Cap: 100GB
Primary storage: E:\\ | Backup: G:\\ | Archive: V:\\ (980 Pro Samsung)

Run this on GODZILLA:
  python godzilla_dataset_downloader.py

Requirements (install once):
  pip install huggingface_hub datasets tqdm

Datasets selected per condenser specialization:
  coding     — starcoder-python-instruct, verifiable-coding-problems
  security   — CVE dataset, security advisories
  emotion    — emotion NLP, GoEmotions
  language   — multilingual NLP, translation pairs
  reasoning  — logical math, philosophy
  baseline   — general knowledge compression
"""

import os, sys, shutil
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BASE_DIR   = Path("H:/datasets")   # Change to E:/ or V:/ as needed
MAX_GB     = 100
MAX_BYTES  = MAX_GB * 1024 ** 3
LOG_FILE   = BASE_DIR / "_download_log.txt"

DATASETS = [
    # CODING SPECIALIZATION
    {
        "name":   "starcoder-python-instruct",
        "repo":   "OLMo-Coding/starcoder-python-instruct",
        "type":   "dataset",
        "folder": "coding/starcoder-python-instruct",
        "cap_gb": 5,
        "why":    "High-quality Python code instruction pairs. Best for coding condenser training.",
    },
    {
        "name":   "verifiable-coding-problems",
        "repo":   "PrimeIntellect/verifiable-coding-problems",
        "type":   "dataset",
        "folder": "coding/verifiable-coding-problems",
        "cap_gb": 3,
        "why":    "144k coding problems with verified solutions. Ground-truth for code reasoning.",
    },
    {
        "name":   "vibe-coding-instruct",
        "repo":   "CodeDevX/Vibe-Coding-Instruct",
        "type":   "dataset",
        "folder": "coding/vibe-coding-instruct",
        "cap_gb": 4,
        "why":    "1.1M instruction-following coding examples. Modern, high-signal training data.",
    },

    # SECURITY / CYBERSECURITY SPECIALIZATION
    {
        "name":   "cve-coding-nova",
        "repo":   "GatlingPeaShooter/CVE-coding-NOVA",
        "type":   "dataset",
        "folder": "security/cve-coding-nova",
        "cap_gb": 2,
        "why":    "CVE vulnerability dataset for security condenser. Real-world threat patterns.",
    },
    {
        "name":   "cybersecurity-help",
        "repo":   "trained-on-earth/cybersecurity-help",
        "type":   "dataset",
        "folder": "security/cybersecurity-help",
        "cap_gb": 1,
        "why":    "Security Q&A pairs. Good for defensive security reasoning training.",
    },

    # EMOTION / HUMAN ANALYSIS SPECIALIZATION
    {
        "name":   "go-emotions",
        "repo":   "google-research-datasets/go_emotions",
        "type":   "dataset",
        "folder": "emotion/go-emotions",
        "cap_gb": 1,
        "why":    "58k Reddit sentences labelled with 27 emotion categories. Best emotion dataset.",
    },
    {
        "name":   "emotion-nlp",
        "repo":   "dair-ai/emotion",
        "type":   "dataset",
        "folder": "emotion/emotion-nlp",
        "cap_gb": 0.5,
        "why":    "6-class emotion classification. Fast to train, high accuracy baseline.",
    },

    # LANGUAGE / MULTILINGUAL SPECIALIZATION
    {
        "name":   "opus-multilingual",
        "repo":   "Helsinki-NLP/opus-100",
        "type":   "dataset",
        "folder": "language/opus-100",
        "cap_gb": 5,
        "why":    "100-language parallel corpus. Foundation for multilingual condenser.",
    },

    # REASONING / PHILOSOPHY SPECIALIZATION
    {
        "name":   "logical-math-coding-sft",
        "repo":   "kanhatakeyama/wizardlm8x22b-logical-math-coding-sft",
        "type":   "dataset",
        "folder": "reasoning/logical-math-coding-sft",
        "cap_gb": 3,
        "why":    "284k logical/math/coding reasoning chains. Best for deep analysis condenser.",
    },

    # BASELINE / GENERAL SPECIALIZATION
    {
        "name":   "fineweb-edu-sample",
        "repo":   "HuggingFaceFW/fineweb-edu",
        "type":   "dataset",
        "folder": "baseline/fineweb-edu-sample",
        "cap_gb": 10,
        "why":    "High-quality educational web text. Best general compression training data.",
        "split":  "sample-10BT",   # Use sample to stay in cap
    },
]

# ─── UTILITIES ────────────────────────────────────────────────────────────────

def get_dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) if path.exists() else 0

def log(msg: str):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def format_gb(b: int) -> str:
    return f"{b / 1024**3:.2f} GB"

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    try:
        from huggingface_hub import snapshot_download, hf_hub_download
        from tqdm import tqdm
    except ImportError:
        print("Installing requirements...")
        os.system(f"{sys.executable} -m pip install huggingface_hub datasets tqdm -q")
        from huggingface_hub import snapshot_download

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log(f"\n{'='*60}")
    log(f"GODZILLA AI Dataset Downloader — starting")
    log(f"Target: {BASE_DIR}")
    log(f"Cap: {MAX_GB} GB")
    log(f"{'='*60}\n")

    total_used = get_dir_size(BASE_DIR)
    log(f"Existing data: {format_gb(total_used)}")

    for ds in DATASETS:
        dest = BASE_DIR / ds["folder"]
        cap_bytes = int(ds["cap_gb"] * 1024 ** 3)

        log(f"\n─── {ds['name']} ───────────────────────────────")
        log(f"    Repo:   {ds['repo']}")
        log(f"    Target: {dest}")
        log(f"    Cap:    {ds['cap_gb']} GB")
        log(f"    Why:    {ds['why']}")

        if total_used + cap_bytes > MAX_BYTES:
            log(f"    ⚠️  Skipped — would exceed {MAX_GB}GB cap")
            continue

        if dest.exists() and get_dir_size(dest) > 1024 * 1024:
            log(f"    ✅ Already downloaded ({format_gb(get_dir_size(dest))})")
            continue

        dest.mkdir(parents=True, exist_ok=True)

        try:
            kwargs = {"repo_id": ds["repo"], "repo_type": "dataset", "local_dir": str(dest)}
            if "split" in ds:
                kwargs["allow_patterns"] = [f"*{ds['split']}*"]
            snapshot_download(**kwargs)
            size = get_dir_size(dest)
            total_used += size
            log(f"    ✅ Downloaded: {format_gb(size)}")
            log(f"    📊 Total used: {format_gb(total_used)} / {MAX_GB} GB")
        except Exception as e:
            log(f"    ❌ Error: {e}")
            if dest.exists() and get_dir_size(dest) == 0:
                shutil.rmtree(dest, ignore_errors=True)

    log(f"\n{'='*60}")
    log(f"COMPLETE — Total downloaded: {format_gb(total_used)}")
    log(f"Log saved to: {LOG_FILE}")
    log(f"{'='*60}\n")

    # Write dataset index
    index_path = BASE_DIR / "_dataset_index.md"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# GODZILLA Dataset Index\n")
        f.write(f"**Total cap:** {MAX_GB} GB  |  **Drive:** H:\\  |  **Archive:** V:\\\n\n")
        f.write("| Specialization | Dataset | Folder | Why |\n")
        f.write("|---|---|---|---|\n")
        for ds in DATASETS:
            f.write(f"| {ds['folder'].split('/')[0]} | {ds['name']} | {ds['folder']} | {ds['why']} |\n")
    log(f"Index written to: {index_path}")

if __name__ == "__main__":
    main()

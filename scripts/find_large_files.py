#!/usr/bin/env python3
"""Find files >= 500 MB on V:\ — sorted largest first. Read-only inventory."""
import os, json
from pathlib import Path
from datetime import datetime

DRIVE      = "V:\\"
MIN_BYTES  = 500 * 1024**2          # 500 MB (binary)
OUT_JSON   = "V_large_files.json"

def human(b): return f"{b / 1024**3:.2f} GB"

def scan(root):
    big = []
    for cur, dirs, files in os.walk(root):
        for name in files:
            fp = os.path.join(cur, name)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue                      # skip unreadable / broken links
            if sz >= MIN_BYTES:
                big.append((sz, fp, os.path.splitext(name)[1].lower()))
    big.sort(key=lambda x: x[0], reverse=True)
    return big

if __name__ == "__main__":
    if not os.path.exists(DRIVE):
        raise SystemExit(f"Drive {DRIVE} not found")

    print(f"Scanning {DRIVE} for files >= 500 MB ...")
    results = scan(DRIVE)

    total = sum(s for s, _, _ in results)
    print(f"\n{len(results)} files >= 500 MB  |  {human(total)} total\n")
    print(f"{'SIZE':>10}  {'EXT':<8} PATH")
    print("-" * 70)
    for sz, fp, ext in results:
        print(f"{human(sz):>10}  {ext or '(none)':<8} {fp}")

    report = {
        "drive": DRIVE,
        "scanned_at": datetime.now().isoformat(),
        "threshold_mb": 500,
        "count": len(results),
        "total_gb": round(total / 1024**3, 2),
        "files": [{"size_gb": round(s / 1024**3, 2), "ext": e, "path": p}
                  for s, p, e in results],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved → {OUT_JSON}")

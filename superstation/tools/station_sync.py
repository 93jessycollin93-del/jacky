#!/usr/bin/env python3
"""station_sync — vendor the kernel into an adopting repo, with drift detection.

    python3 superstation/tools/station_sync.py --to ../core-light-vault
    python3 superstation/tools/station_sync.py --to ../core-light-vault --check
    python3 superstation/tools/station_sync.py --check-all ..

The fleet's previous answer to sharing code was to copy files and verify them
"by checksum, not by inspection" — with the checksums living in a prose document
that nothing executed. This does the same copy and writes the checksums to a
lockfile that CI can actually run, so an edited copy is a failing check rather
than a surprise six months later.

Why vendor at all rather than publish a package: the nine repos share no
registry, no build system and no dependency in common, and three of them are
edited by a hosted builder that will not run ``npm install`` on our behalf. A
committed copy is the only distribution mechanism all of them support. The
lockfile is what makes that survivable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
SUPERSTATION = ROOT / "superstation"
KERNEL_TS = SUPERSTATION / "kernel" / "ts"
LOCKFILE = "station.lock.json"
VENDOR_SUBPATH = Path("src") / "superstation"

SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".venv", "__pycache__"}


def kernel_version() -> str:
    return (SUPERSTATION / "VERSION").read_text().strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kernel_files() -> List[Path]:
    return sorted(p for p in KERNEL_TS.glob("*.ts") if p.is_file())


def build_lock() -> Dict[str, object]:
    return {
        "_comment": (
            "Written by superstation/tools/station_sync.py. Do not hand-edit. "
            "Run station_sync.py --check to verify this vendored copy still matches "
            "the kernel it was taken from."
        ),
        "kernel": kernel_version(),
        "source": "93jessycollin93-del/jacky:superstation/kernel/ts",
        "files": {p.name: digest(p) for p in kernel_files()},
    }


def vendor_dir(repo: Path) -> Path:
    """Where the kernel goes in a target repo.

    ``src/superstation`` for anything with a ``src/`` (every Vite app in the
    fleet has one); a top-level ``superstation/`` otherwise.
    """
    return repo / VENDOR_SUBPATH if (repo / "src").is_dir() else repo / "superstation"


def sync(repo: Path, dry_run: bool = False) -> Tuple[int, List[str]]:
    target = vendor_dir(repo)
    notes: List[str] = []
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
    for src in kernel_files():
        dst = target / src.name
        if dst.exists() and digest(dst) == digest(src):
            continue
        notes.append(f"{'would write' if dry_run else 'wrote'} {dst.relative_to(repo)}")
        if not dry_run:
            shutil.copy2(src, dst)
    lock_path = target / LOCKFILE
    lock = build_lock()
    if not dry_run:
        lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    notes.append(f"{'would write' if dry_run else 'wrote'} {lock_path.relative_to(repo)}")
    return 0, notes


def check(repo: Path) -> Tuple[int, List[str]]:
    """Verify a vendored copy against its lockfile and against the live kernel."""
    target = vendor_dir(repo)
    lock_path = target / LOCKFILE
    problems: List[str] = []

    if not lock_path.exists():
        return 0, [f"{repo.name}: no vendored kernel (no {lock_path.relative_to(repo)}) — skipped"]

    try:
        lock = json.loads(lock_path.read_text())
    except ValueError as err:
        return 1, [f"{repo.name}: {LOCKFILE} is not valid JSON ({err})"]

    live = kernel_version()
    if lock.get("kernel") != live:
        problems.append(
            f"{repo.name}: vendored kernel {lock.get('kernel')} but source is {live} — "
            "re-run station_sync.py"
        )

    recorded: Dict[str, str] = lock.get("files") or {}
    current = {p.name: digest(p) for p in kernel_files()}

    for name, want in recorded.items():
        dst = target / name
        if not dst.exists():
            problems.append(f"{repo.name}: {name} is in the lockfile but missing from the repo")
            continue
        got = digest(dst)
        if got != want:
            problems.append(f"{repo.name}: {name} has been edited locally (drifted from the lockfile)")
        elif name in current and current[name] != want:
            problems.append(f"{repo.name}: {name} is stale — the source kernel has moved on")

    for name in current:
        if name not in recorded:
            problems.append(f"{repo.name}: {name} exists in the source kernel but was never vendored here")

    if problems:
        return 1, problems
    return 0, [f"{repo.name}: vendored kernel {lock['kernel']} matches source ({len(recorded)} files)"]


def find_repos(root: Path) -> List[Path]:
    out = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and child.name not in SKIP_DIRS and (child / ".git").exists():
            out.append(child)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Vendor the Superstation kernel, or check a vendored copy.")
    ap.add_argument("--to", type=Path, help="target repo to vendor into")
    ap.add_argument("--check", action="store_true", help="verify instead of writing")
    ap.add_argument("--check-all", type=Path, metavar="DIR", help="check every git repo under DIR")
    ap.add_argument("--dry-run", action="store_true", help="show what would be written")
    args = ap.parse_args()

    print(f"station_sync — kernel {kernel_version()}\n")

    if args.check_all:
        rc = 0
        for repo in find_repos(args.check_all.resolve()):
            code, notes = check(repo)
            rc |= code
            for n in notes:
                print(f"  {'FAIL' if code else 'ok  '}  {n}")
        print("\n" + ("FAILED — vendored copies have drifted" if rc else "OK — no drift"))
        return rc

    if not args.to:
        ap.error("one of --to or --check-all is required")

    repo = args.to.resolve()
    if not repo.is_dir():
        print(f"  no such directory: {repo}")
        return 1

    code, notes = (check(repo) if args.check else sync(repo, args.dry_run))
    for n in notes:
        print(f"  {n}")
    print("\n" + ("FAILED" if code else "OK"))
    return code


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Lightweight project sanity checker for refactor tasks."""
from __future__ import annotations

from pathlib import Path

REQUIRED = ["README.md", "requirements.txt"]


def main() -> None:
    missing = [name for name in REQUIRED if not Path(name).exists()]
    if missing:
        raise SystemExit(f"Missing required files: {', '.join(missing)}")
    print("Refactor preflight passed")


if __name__ == "__main__":
    main()

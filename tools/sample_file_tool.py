#!/usr/bin/env python3
"""Example custom tool: summarize text files without external dependencies."""
from __future__ import annotations

import argparse
from pathlib import Path


def summarize(path: Path, max_lines: int) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    preview = "\n".join(lines[:max_lines])
    return f"File: {path}\nLines: {len(lines)}\nPreview:\n{preview}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a text file")
    parser.add_argument("path")
    parser.add_argument("--max-lines", type=int, default=20)
    args = parser.parse_args()
    print(summarize(Path(args.path), args.max_lines))


if __name__ == "__main__":
    main()

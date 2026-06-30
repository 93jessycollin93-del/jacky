#!/usr/bin/env python3
"""Simple local secret-pattern preflight for demonstration purposes."""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Demonstration-only patterns for common committed-secret mistakes. Production
# environments should still use a dedicated scanner such as GitHub secret scanning.
PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*=\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)['\"](api[_-]?key|token|secret)['\"]\s*:\s*['\"][^'\"]{12,}['\"]"),
]


def scan(path: Path) -> list[str]:
    findings: list[str] = []
    text = path.read_text(errors="ignore")
    for pattern in PATTERNS:
        if pattern.search(text):
            findings.append(str(path))
    return findings


def main() -> None:
    files = [Path(arg) for arg in sys.argv[1:]] or list(Path(".").glob("**/*"))
    findings: list[str] = []
    for path in files:
        if path.is_file() and ".git" not in path.parts:
            findings.extend(scan(path))
    if findings:
        raise SystemExit("Potential secrets found in: " + ", ".join(sorted(set(findings))))
    print("Security preflight passed")


if __name__ == "__main__":
    main()

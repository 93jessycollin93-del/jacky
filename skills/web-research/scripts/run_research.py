#!/usr/bin/env python3
"""Create a structured research brief skeleton for OmniAgent."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a research brief template")
    parser.add_argument("question", help="Research question")
    args = parser.parse_args()
    now = datetime.now(timezone.utc).isoformat()
    print(f"# Research Brief\n\nQuestion: {args.question}\nAccessed: {now}\n")
    print("## Findings\n- ")
    print("## Sources\n- ")
    print("## Recommendation\n- ")
    print("## Risks / Unknowns\n- ")


if __name__ == "__main__":
    main()

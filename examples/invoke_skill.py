#!/usr/bin/env python3
"""
examples/invoke_skill.py — Show how to invoke a skill programmatically.

Skills are Markdown documents. This script parses the front-matter and
prints what tools and parameters the skill expects.

Run: python examples/invoke_skill.py skills/web-research.skill.md
"""

from __future__ import annotations

import sys
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def parse_frontmatter(text: str) -> dict:
    """Very simple YAML front-matter parser (no external deps)."""
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    fm_block = text[3:end].strip()
    result: dict = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def extract_parameters(text: str) -> list[dict]:
    """Parse the Parameters table from the skill Markdown."""
    params: list[dict] = []
    in_table = False
    for line in text.splitlines():
        if "| Name" in line and "Required" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 3:
                params.append({
                    "name": cells[0].strip("`"),
                    "required": "✅" in cells[1],
                    "description": cells[2],
                })
        elif in_table:
            break
    return params


def main():
    skill_path = sys.argv[1] if len(sys.argv) > 1 else "skills/web-research.skill.md"
    full_path = _ROOT / skill_path

    if not full_path.exists():
        print(f"Skill file not found: {full_path}")
        sys.exit(1)

    text = full_path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    params = extract_parameters(text)

    print(f"Skill: {meta.get('name', '(unnamed)')}")
    print(f"Description: {meta.get('description', '')}")
    print(f"Tools required: {meta.get('tools', '')}")
    print(f"Output: {meta.get('output', 'N/A')}\n")

    print("Parameters:")
    for p in params:
        req = "required" if p["required"] else "optional"
        print(f"  --{p['name']} ({req}): {p['description']}")

    print("\nInvocation example:")
    example_args = " ".join(
        f'{p["name"]}="<value>"' for p in params if p["required"]
    )
    print(f"  @OmniAgent run skill: {meta.get('name', 'skill')} {example_args}")


if __name__ == "__main__":
    main()

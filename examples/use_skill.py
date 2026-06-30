"""
Example: Use the OmniAgent skill runner to invoke a skill programmatically.

This shows how to call a skill from Python code instead of via Copilot Chat.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_skill(skill_name: str) -> dict:
    """Parse a .skill.md file and return its frontmatter + body."""
    skill_path = Path("skills") / f"{skill_name}.skill.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")

    text = skill_path.read_text(encoding="utf-8")
    # Simple frontmatter parser (--- delimited YAML block)
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {"name": skill_name, "body": text}

    import yaml  # pyyaml (third-party, listed in requirements.txt)

    frontmatter = yaml.safe_load(parts[1])
    frontmatter["body"] = parts[2].strip()
    return frontmatter


def build_prompt(skill: dict, inputs: dict) -> str:
    """Inject inputs into the skill body to produce a ready-to-send prompt."""
    body = skill.get("body", "")
    for key, value in inputs.items():
        body = body.replace(f"{{{key}}}", str(value))
    return body


if __name__ == "__main__":
    skill = load_skill("web-research")
    print("Loaded skill:", skill.get("skill"))
    print("Tools required:", skill.get("tools"))

    prompt = build_prompt(skill, {"topic": "Ollama streaming API", "depth": "shallow"})
    print("\n--- Prompt preview (first 400 chars) ---")
    print(prompt[:400])

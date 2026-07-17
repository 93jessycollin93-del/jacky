#!/usr/bin/env python3
"""
tests/agent_tests/test_skill_parsing.py — Tests for skill front-matter parsing
(uses the logic from examples/invoke_skill.py).
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from examples.invoke_skill import parse_frontmatter, extract_parameters, main

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_parse_frontmatter_web_research():
    text = (_ROOT / "skills" / "web-research.skill.md").read_text()
    meta = parse_frontmatter(text)
    assert meta.get("name") == "web-research"
    assert "web_search" in meta.get("tools", "")


def test_parse_frontmatter_code_refactor():
    text = (_ROOT / "skills" / "code-refactor.skill.md").read_text()
    meta = parse_frontmatter(text)
    assert meta.get("name") == "code-refactor"


def test_extract_parameters_web_research():
    text = (_ROOT / "skills" / "web-research.skill.md").read_text()
    params = extract_parameters(text)
    names = [p["name"] for p in params]
    assert "query" in names
    required = {p["name"]: p["required"] for p in params}
    assert required["query"] is True
    assert required.get("depth") is False


def test_extract_parameters_code_refactor():
    text = (_ROOT / "skills" / "code-refactor.skill.md").read_text()
    params = extract_parameters(text)
    names = [p["name"] for p in params]
    assert "target" in names
    assert "goal" in names


def test_all_skill_files_have_required_sections():
    """Every skill file must have name, description, tools, Steps, and Acceptance Criteria."""
    skill_dir = _ROOT / "skills"
    for skill_file in skill_dir.glob("*.skill.md"):
        text = skill_file.read_text()
        meta = parse_frontmatter(text)
        assert meta.get("name"), f"{skill_file.name} missing 'name' in front-matter"
        assert meta.get("description"), f"{skill_file.name} missing 'description'"
        assert meta.get("tools"), f"{skill_file.name} missing 'tools'"
        assert "## Steps" in text, f"{skill_file.name} missing '## Steps' section"
        assert "## Acceptance Criteria" in text, f"{skill_file.name} missing '## Acceptance Criteria'"


# ── main() CLI entry point ───────────────────────────────────────────────────

def test_main_missing_file_exits_with_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["invoke_skill.py", "skills/does-not-exist.skill.md"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    assert "Skill file not found" in capsys.readouterr().out


def test_main_prints_skill_summary_for_web_research(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["invoke_skill.py", "skills/web-research.skill.md"])
    main()

    out = capsys.readouterr().out
    assert "Skill: web-research" in out
    assert "Parameters:" in out
    assert "--query (required):" in out
    assert "--depth (optional):" in out
    assert '@OmniAgent run skill: web-research query="<value>"' in out


def test_main_defaults_to_web_research_when_no_arg_given(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["invoke_skill.py"])
    main()
    assert "Skill: web-research" in capsys.readouterr().out

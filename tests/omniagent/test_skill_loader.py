"""
Tests for OmniAgent skill loader (examples/use_skill.py helper).
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from examples.use_skill import load_skill, build_prompt


class TestLoadSkill:
    def test_load_web_research_skill(self):
        skill = load_skill("web-research")
        assert skill["skill"] == "web-research"
        assert isinstance(skill["tools"], list)
        assert len(skill["tools"]) > 0

    def test_load_code_refactor_skill(self):
        skill = load_skill("code-refactor")
        assert skill["skill"] == "code-refactor"

    def test_load_nonexistent_skill_raises(self):
        with pytest.raises(FileNotFoundError):
            load_skill("does-not-exist")

    def test_skill_has_body(self):
        skill = load_skill("debug-issue")
        assert len(skill.get("body", "")) > 50


class TestBuildPrompt:
    def test_substitution(self):
        skill = {"body": "Research {topic} at depth {depth}."}
        result = build_prompt(skill, {"topic": "Ollama", "depth": "shallow"})
        assert "Ollama" in result
        assert "shallow" in result
        assert "{topic}" not in result

    def test_missing_key_leaves_placeholder(self):
        skill = {"body": "Research {topic}."}
        result = build_prompt(skill, {})
        assert "{topic}" in result

    def test_empty_inputs(self):
        skill = {"body": "No placeholders here."}
        result = build_prompt(skill, {})
        assert result == "No placeholders here."

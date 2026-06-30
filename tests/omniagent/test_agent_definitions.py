"""
Tests for OmniAgent agent definition files.

Validates that every .agent.md file in .github/agents/ has valid YAML
frontmatter and required fields.
"""
import os
import pytest
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

AGENTS_DIR = Path(__file__).parent.parent.parent / ".github" / "agents"
REQUIRED_FIELDS = {"name", "description"}


def get_agent_files():
    return list(AGENTS_DIR.glob("*.agent.md"))


@pytest.mark.skipif(not HAS_YAML, reason="pyyaml not installed")
class TestAgentDefinitions:
    @pytest.mark.parametrize("agent_file", get_agent_files())
    def test_agent_has_frontmatter(self, agent_file):
        text = agent_file.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        assert len(parts) >= 3, f"{agent_file.name} missing YAML frontmatter"

    @pytest.mark.parametrize("agent_file", get_agent_files())
    def test_agent_frontmatter_valid_yaml(self, agent_file):
        text = agent_file.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict), f"{agent_file.name} frontmatter is not a dict"

    @pytest.mark.parametrize("agent_file", get_agent_files())
    def test_agent_has_required_fields(self, agent_file):
        text = agent_file.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        for field in REQUIRED_FIELDS:
            assert field in frontmatter, f"{agent_file.name} missing field: {field}"

    @pytest.mark.parametrize("agent_file", get_agent_files())
    def test_agent_has_markdown_body(self, agent_file):
        text = agent_file.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        body = parts[2].strip() if len(parts) >= 3 else ""
        assert len(body) > 100, f"{agent_file.name} body is too short (< 100 chars)"


class TestAgentDirectoryExists:
    def test_agents_dir_exists(self):
        assert AGENTS_DIR.exists(), ".github/agents/ directory not found"

    def test_at_least_one_agent(self):
        agents = get_agent_files()
        assert len(agents) >= 1, "No .agent.md files found"

    def test_omniagent_exists(self):
        omni = AGENTS_DIR / "OmniAgent.agent.md"
        assert omni.exists(), "OmniAgent.agent.md not found"

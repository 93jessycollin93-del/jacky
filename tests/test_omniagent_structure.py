from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_omniagent_core_files_exist():
    required = [
        ".github/agents/OmniAgent.agent.md",
        "agents/coder.agent.md",
        "agents/researcher.agent.md",
        "agents/tester.agent.md",
        "agents/devops.agent.md",
        "agents/accessibility.agent.md",
        "skills/web-research/SKILL.md",
        "skills/code-refactor/SKILL.md",
        "skills/security-review/SKILL.md",
        "mcp-servers/omniagent.mcp.json",
        "tools/sample_file_tool.py",
        "docs/omniagent-architecture.md",
        "assets/templates/task-plan.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_skill_frontmatter_present():
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{skill} is missing YAML frontmatter"
        assert "description:" in text
        assert "# " in text

# OmniAgent test suite

This directory contains tests for the OmniAgent infrastructure added to Jacky.

## Running

```bash
# From repo root
pytest tests/omniagent/ -v
```

## Test files

| File | Tests |
|------|-------|
| `test_skill_loader.py` | Skill file parsing and prompt building |
| `test_agent_definitions.py` | Frontmatter validation for all .agent.md files |

## Requirements

```
pytest>=7.0
pyyaml>=6.0
```

Both are already in `requirements.txt`.

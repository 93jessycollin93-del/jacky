# Tools and MCP Integration

OmniAgent assumes access to native Copilot tools plus optional MCP servers.

## Built-in Tool Categories

- File and repository operations
- Terminal and package manager commands
- GitHub issues, PRs, commits, checks, and workflows
- Code and semantic search
- Web fetch and browser automation
- Static analysis, dependency advisory, and secret scanning

## MCP Configuration

Use `mcp-servers/omniagent.mcp.json` as a starting point. Configure tokens through environment variables only. Never commit real credentials.

## Adding a Tool

1. Put implementation in `tools/`.
2. Document inputs, outputs, errors, and security constraints.
3. Add tests or examples.
4. Register the tool through MCP or the host agent configuration.

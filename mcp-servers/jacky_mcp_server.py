#!/usr/bin/env python3
"""
mcp-servers/jacky_mcp_server.py

Minimal MCP (Model Context Protocol) server that exposes Jacky's core
orchestration capabilities as tools callable by OmniAgent and VS Code Copilot.

Protocol: MCP over stdio (JSON-RPC 2.0 framing).
"""

from __future__ import annotations

import json
import sys
import os
import pathlib

# Add repo root to path so we can import Jacky modules
_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def _send(obj: dict) -> None:
    """Write a single JSON-RPC message to stdout."""
    line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _error(id_: int | str | None, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _ok(id_: int | str | None, result: object) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


# ── Tool implementations ─────────────────────────────────────────────────────

def _tool_get_system_status(_params: dict) -> dict:
    try:
        from situation_assessor import SituationAssessor
        assessor = SituationAssessor()
        status = assessor.assess()
        return status
    except Exception as exc:
        return {"error": str(exc), "note": "situation_assessor unavailable"}


def _tool_list_models(_params: dict) -> dict:
    try:
        from ollama_client import OllamaClient
        client = OllamaClient()
        models = client.list_models()
        return {"models": models}
    except Exception as exc:
        return {"error": str(exc), "note": "ollama_client unavailable"}


def _tool_route_task(params: dict) -> dict:
    task = params.get("task", "")
    max_cost_tier = params.get("max_cost_tier", "any")
    try:
        from jacky_core import JackyCore
        core = JackyCore()
        response = core.route(task, max_cost_tier=max_cost_tier)
        return {"response": response}
    except Exception as exc:
        return {"error": str(exc), "task": task}


_TOOL_MAP = {
    "jacky_get_system_status": _tool_get_system_status,
    "jacky_list_models": _tool_list_models,
    "jacky_route_task": _tool_route_task,
}

# ── MCP capabilities declaration ─────────────────────────────────────────────

_CAPABILITIES = {
    "tools": {
        "jacky_route_task": {
            "description": "Route a task to the cheapest capable AI model.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "max_cost_tier": {
                        "type": "string",
                        "enum": ["local", "free_cloud", "paid_cloud", "any"],
                    },
                },
                "required": ["task"],
            },
        },
        "jacky_get_system_status": {
            "description": "Return GPU temp, CPU %, RAM %, active models.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        "jacky_list_models": {
            "description": "List locally available Ollama models.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    }
}


# ── Main request-response loop ────────────────────────────────────────────────

def main() -> None:
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            _send(_error(None, -32700, f"Parse error: {exc}"))
            continue

        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "initialize":
            _send(_ok(msg_id, {"capabilities": _CAPABILITIES, "serverInfo": {"name": "jacky-mcp-server", "version": "1.0"}}))
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_params = params.get("arguments", {})
            handler = _TOOL_MAP.get(tool_name)
            if handler is None:
                _send(_error(msg_id, -32601, f"Unknown tool: {tool_name}"))
            else:
                result = handler(tool_params)
                _send(_ok(msg_id, {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}))
        elif method == "tools/list":
            _send(_ok(msg_id, {"tools": list(_CAPABILITIES["tools"].keys())}))
        else:
            _send(_error(msg_id, -32601, f"Method not found: {method}"))


if __name__ == "__main__":
    main()

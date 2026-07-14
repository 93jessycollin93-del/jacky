#!/usr/bin/env python3
"""
tests/agent_tests/test_jacky_mcp_server.py — Unit tests for
mcp-servers/jacky_mcp_server.py

The `mcp-servers` directory is not a valid Python package name (it contains a
hyphen), so we add it directly to sys.path and import the module by its
top-level name.
"""

import io
import json
import pathlib
import sys
import types

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "mcp-servers"))

import jacky_mcp_server as mcp_server  # noqa: E402


# ── _send / _ok / _error ─────────────────────────────────────────────────────

def test_send_writes_single_json_line(capsys):
    mcp_server._send({"jsonrpc": "2.0", "id": 1, "result": "ok"})
    out = capsys.readouterr().out
    assert out == '{"jsonrpc": "2.0", "id": 1, "result": "ok"}\n'


def test_ok_shape():
    msg = mcp_server._ok(1, {"foo": "bar"})
    assert msg == {"jsonrpc": "2.0", "id": 1, "result": {"foo": "bar"}}


def test_error_shape():
    msg = mcp_server._error(2, -32601, "Method not found")
    assert msg == {
        "jsonrpc": "2.0",
        "id": 2,
        "error": {"code": -32601, "message": "Method not found"},
    }


def test_ok_and_error_accept_none_id():
    assert mcp_server._ok(None, {})["id"] is None
    assert mcp_server._error(None, -32700, "parse error")["id"] is None


# ── _tool_get_system_status ──────────────────────────────────────────────────

def test_tool_get_system_status_success(monkeypatch):
    fake_module = types.ModuleType("situation_assessor")

    class FakeAssessor:
        def assess(self):
            return {"level": "safe_for_local", "gpu_temp_c": 55}

    fake_module.SituationAssessor = FakeAssessor
    monkeypatch.setitem(sys.modules, "situation_assessor", fake_module)

    result = mcp_server._tool_get_system_status({})
    assert result == {"level": "safe_for_local", "gpu_temp_c": 55}


def test_tool_get_system_status_failure(monkeypatch):
    fake_module = types.ModuleType("situation_assessor")

    class FakeAssessor:
        def __init__(self):
            raise RuntimeError("no GPU telemetry")

    fake_module.SituationAssessor = FakeAssessor
    monkeypatch.setitem(sys.modules, "situation_assessor", fake_module)

    result = mcp_server._tool_get_system_status({})
    assert result == {
        "error": "no GPU telemetry",
        "note": "situation_assessor unavailable",
    }


# ── _tool_list_models ─────────────────────────────────────────────────────────

def test_tool_list_models_success(monkeypatch):
    fake_module = types.ModuleType("ollama_client")

    class FakeClient:
        def list_models(self):
            return [{"name": "llama3.2:3b"}]

    fake_module.OllamaClient = FakeClient
    monkeypatch.setitem(sys.modules, "ollama_client", fake_module)

    result = mcp_server._tool_list_models({})
    assert result == {"models": [{"name": "llama3.2:3b"}]}


def test_tool_list_models_failure(monkeypatch):
    fake_module = types.ModuleType("ollama_client")

    class FakeClient:
        def list_models(self):
            raise ConnectionError("ollama not running")

    fake_module.OllamaClient = FakeClient
    monkeypatch.setitem(sys.modules, "ollama_client", fake_module)

    result = mcp_server._tool_list_models({})
    assert result == {
        "error": "ollama not running",
        "note": "ollama_client unavailable",
    }


# ── _tool_route_task ──────────────────────────────────────────────────────────

def test_tool_route_task_success(monkeypatch):
    fake_module = types.ModuleType("jacky_core")

    class FakeCore:
        def route(self, task, max_cost_tier="any"):
            return f"routed:{task}:{max_cost_tier}"

    fake_module.JackyCore = FakeCore
    monkeypatch.setitem(sys.modules, "jacky_core", fake_module)

    result = mcp_server._tool_route_task({"task": "do X", "max_cost_tier": "local"})
    assert result == {"response": "routed:do X:local"}


def test_tool_route_task_failure(monkeypatch):
    fake_module = types.ModuleType("jacky_core")

    class FakeCore:
        pass  # no .route() -> AttributeError, matching the real JackyCore today

    fake_module.JackyCore = FakeCore
    monkeypatch.setitem(sys.modules, "jacky_core", fake_module)

    result = mcp_server._tool_route_task({"task": "do X"})
    assert result["task"] == "do X"
    assert "error" in result


def test_tool_route_task_uses_defaults_when_params_missing(monkeypatch):
    fake_module = types.ModuleType("jacky_core")
    captured = {}

    class FakeCore:
        def route(self, task, max_cost_tier="any"):
            captured["task"] = task
            captured["max_cost_tier"] = max_cost_tier
            return "ok"

    fake_module.JackyCore = FakeCore
    monkeypatch.setitem(sys.modules, "jacky_core", fake_module)

    result = mcp_server._tool_route_task({})
    assert captured == {"task": "", "max_cost_tier": "any"}
    assert result == {"response": "ok"}


# ── main() request/response loop ─────────────────────────────────────────────

def _run_main_with_lines(monkeypatch, lines):
    monkeypatch.setattr(sys, "stdin", io.StringIO("\n".join(lines) + "\n"))
    mcp_server.main()


def test_main_initialize(monkeypatch, capsys):
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    _run_main_with_lines(monkeypatch, [request])

    response = json.loads(capsys.readouterr().out.strip())
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "jacky-mcp-server"
    assert "jacky_route_task" in response["result"]["capabilities"]["tools"]


def test_main_tools_list(monkeypatch, capsys):
    request = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    _run_main_with_lines(monkeypatch, [request])

    response = json.loads(capsys.readouterr().out.strip())
    assert set(response["result"]["tools"]) == {
        "jacky_route_task",
        "jacky_get_system_status",
        "jacky_list_models",
    }


def test_main_tools_call_unknown_tool(monkeypatch, capsys):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "not_a_real_tool", "arguments": {}},
    })
    _run_main_with_lines(monkeypatch, [request])

    response = json.loads(capsys.readouterr().out.strip())
    assert response["error"]["code"] == -32601
    assert "not_a_real_tool" in response["error"]["message"]


def test_main_tools_call_known_tool(monkeypatch, capsys):
    fake_module = types.ModuleType("ollama_client")

    class FakeClient:
        def list_models(self):
            return []

    fake_module.OllamaClient = FakeClient
    monkeypatch.setitem(sys.modules, "ollama_client", fake_module)

    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "jacky_list_models", "arguments": {}},
    })
    _run_main_with_lines(monkeypatch, [request])

    response = json.loads(capsys.readouterr().out.strip())
    assert response["id"] == 4
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload == {"models": []}


def test_main_unknown_method(monkeypatch, capsys):
    request = json.dumps({"jsonrpc": "2.0", "id": 5, "method": "bogus/method"})
    _run_main_with_lines(monkeypatch, [request])

    response = json.loads(capsys.readouterr().out.strip())
    assert response["error"]["code"] == -32601
    assert "bogus/method" in response["error"]["message"]


def test_main_parse_error_returns_null_id(monkeypatch, capsys):
    _run_main_with_lines(monkeypatch, ["not valid json{{{"])

    response = json.loads(capsys.readouterr().out.strip())
    assert response["error"]["code"] == -32700
    assert response["id"] is None


def test_main_skips_blank_lines(monkeypatch, capsys):
    request = json.dumps({"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
    _run_main_with_lines(monkeypatch, ["", "   ", request, ""])

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == 6


def test_main_processes_multiple_requests_in_order(monkeypatch, capsys):
    req1 = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    req2 = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "initialize"})
    _run_main_with_lines(monkeypatch, [req1, req2])

    lines = capsys.readouterr().out.strip().splitlines()
    assert [json.loads(line)["id"] for line in lines] == [1, 2]


def test_main_missing_id_defaults_to_none(monkeypatch, capsys):
    request = json.dumps({"jsonrpc": "2.0", "method": "tools/list"})
    _run_main_with_lines(monkeypatch, [request])

    response = json.loads(capsys.readouterr().out.strip())
    assert response["id"] is None


# ── mcp-config.json consistency ──────────────────────────────────────────────

def test_mcp_config_declares_every_implemented_tool():
    """Every tool the server actually implements/advertises must also be
    declared in mcp-servers/mcp-config.json, so OmniAgent clients discover it."""
    config_path = _REPO_ROOT / "mcp-servers" / "mcp-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    server_cfg = config["mcpServers"]["jacky-mcp-server"]
    declared_tools = {tool["name"] for tool in server_cfg["tools"]}

    assert set(mcp_server._TOOL_MAP.keys()).issubset(declared_tools)
    assert set(mcp_server._CAPABILITIES["tools"].keys()).issubset(declared_tools)
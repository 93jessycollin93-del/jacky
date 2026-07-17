#!/usr/bin/env python3
"""
tests/agent_tests/test_shell_tool.py — Unit tests for tools/shell_tool.py
"""

import pathlib
import subprocess
import pytest
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.shell_tool import run_command


# ── Happy path ────────────────────────────────────────────────────────────────

def test_echo_command():
    result = run_command("echo hello")
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]


def test_python_version():
    result = run_command("python --version")
    assert result["returncode"] == 0
    assert "Python" in result["stdout"] or "Python" in result["stderr"]


# ── Blocklist ────────────────────────────────────────────────────────────────

def test_blocklist_rm_rf():
    with pytest.raises(PermissionError, match="blocked"):
        run_command("rm -rf /", check_allowlist=False)


def test_blocklist_shutdown():
    with pytest.raises(PermissionError, match="blocked"):
        run_command("shutdown now", check_allowlist=False)


# ── Allowlist ────────────────────────────────────────────────────────────────

def test_allowlist_blocks_unknown_command():
    with pytest.raises(PermissionError, match="not in allowlist"):
        run_command("docker ps")


def test_allowlist_blocks_rm():
    with pytest.raises(PermissionError, match="not in allowlist"):
        run_command("rm tests/agent_tests/test_shell_tool.py")


def test_allowlist_override():
    # With check_allowlist=False an arbitrary (safe) command works
    result = run_command("ls -1 .", check_allowlist=False)
    assert result["returncode"] == 0


# ── Blocklist takes priority ─────────────────────────────────────────────────

def test_blocklist_checked_even_for_allowlisted_prefix():
    """A command that starts with an allowlisted prefix (e.g. 'echo') but
    contains a blocked substring (e.g. 'shutdown') must still be blocked."""
    with pytest.raises(PermissionError, match="blocked"):
        run_command("echo hi; shutdown now")


# ── cwd handling ─────────────────────────────────────────────────────────────

def test_run_command_respects_cwd(tmp_path):
    (tmp_path / "marker.txt").write_text("x")
    result = run_command("ls -1 .", cwd=str(tmp_path), check_allowlist=False)
    assert result["returncode"] == 0
    assert "marker.txt" in result["stdout"]


# ── timeout handling ─────────────────────────────────────────────────────────

def test_run_command_raises_on_timeout():
    with pytest.raises(subprocess.TimeoutExpired):
        run_command("find / -name nonexistent_xyz", check_allowlist=False, timeout=0.01)


# ── stderr capture ───────────────────────────────────────────────────────────

def test_stderr_is_captured_on_failure():
    result = run_command("ls /path/does/not/exist_xyz")
    assert result["returncode"] != 0
    assert result["stderr"] != ""

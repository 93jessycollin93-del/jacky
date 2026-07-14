#!/usr/bin/env python3
"""
tools/shell_tool.py — Controlled shell command execution for OmniAgent.

Provides a whitelist-based approach to running terminal commands safely,
with timeout enforcement and output capture.
"""

from __future__ import annotations

import subprocess
import shlex
import pathlib
from typing import Optional

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Commands that are always blocked regardless of whitelist
_BLOCKLIST = frozenset([
    "rm -rf /",
    "dd if=",
    "mkfs",
    "> /dev/sda",
    "shutdown",
    "reboot",
    "halt",
])

# Allowed command prefixes (extend as needed)
_ALLOWLIST_PREFIXES = [
    "python",
    "pytest",
    "pip",
    "git status",
    "git diff",
    "git log",
    "git add",
    "git commit",
    "git checkout -b",
    "flake8",
    "black",
    "isort",
    "mypy",
    "echo",
    "cat",
    "ls",
    "find",
    "grep",
    "head",
    "tail",
    "wc",
    "curl",
    "wget",
]


def run_command(
    cmd: str,
    *,
    cwd: Optional[str] = None,
    timeout: int = 120,
    check_allowlist: bool = True,
) -> dict:
    """Run *cmd* as a shell command.

    Returns a dict with keys: ``returncode``, ``stdout``, ``stderr``.

    Raises:
        PermissionError: if the command matches the blocklist or (when
            *check_allowlist* is True) does not match the allowlist.
        subprocess.TimeoutExpired: if the command runs longer than *timeout*
            seconds.
    """
    cmd_stripped = cmd.strip()

    # Blocklist check (always)
    for blocked in _BLOCKLIST:
        if blocked in cmd_stripped:
            raise PermissionError(f"Command blocked (blocklist match): {cmd!r}")

    # Allowlist check (optional but default)
    if check_allowlist:
        allowed = any(
            cmd_stripped.startswith(prefix) for prefix in _ALLOWLIST_PREFIXES
        )
        if not allowed:
            raise PermissionError(
                f"Command not in allowlist: {cmd!r}\n"
                f"Pass check_allowlist=False to override (use with caution)."
            )

    work_dir = pathlib.Path(cwd).resolve() if cwd else _REPO_ROOT

    result = subprocess.run(
        shlex.split(cmd_stripped),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=work_dir,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


if __name__ == "__main__":
    out = run_command("python --version")
    print(out)
    out2 = run_command("echo 'OmniAgent shell tool ready'")
    print(out2["stdout"])

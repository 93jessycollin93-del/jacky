#!/usr/bin/env python3
"""
SHELL-TX - the /api/shell body, with consent and an undo.

Today /api/shell checks a command against a regex allow-list and runs it. The
allow-list decides WHICH commands may run; nothing decides what happens when
one runs and goes wrong. This composes ttt + approval + transactions into a
drop-in that keeps the allow-list and adds the missing half.

Deliberately NOT wired into jacky_api.py by this change. That endpoint faces
the internet through the Cloudflare tunnel and you depend on it working right
now; switching its behaviour is your call, not a side effect of adding a
module. When you want it, the edit is one import and one call -- see
adopt_in_jacky_api() at the bottom for the exact diff.

Frame: It's Jacky's PC. Same allow-list, plus a way back.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Callable, Optional

from approval import GATE, Risk
from transactions import TransactionManager, TxState

log = logging.getLogger("ShellTx")

DEFAULT_TIMEOUT_S = 30


def powershell_runner(command: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    """Run one PowerShell command. Raises on non-zero exit, so the transaction
    manager sees a failure and can roll back -- subprocess.run does not raise
    on its own, which is the trap here."""
    proc = subprocess.run(
        ["powershell", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"exit {proc.returncode}: {(proc.stderr or proc.stdout or '').strip()[:400]}"
        )
    return {
        "stdout": proc.stdout[:8000],
        "stderr": proc.stderr[:2000],
        "exit_code": proc.returncode,
    }


def build_manager(guard: Callable[[str], tuple],
                  runner: Optional[Callable[[str], dict]] = None,
                  approval_timeout_s: float = 300.0) -> TransactionManager:
    """Compose the pieces. `guard` should be jacky_api._shell_allowed."""
    return TransactionManager(
        runner or powershell_runner,
        gate=GATE,
        guard=guard,
        approval_timeout_s=approval_timeout_s,
    )


def run_shell_transaction(manager: TransactionManager, command: str, *,
                          rollback: Optional[str] = None,
                          risk: str = "medium",
                          actor: str = "owner") -> tuple:
    """Execute one command as a transaction.

    Returns (payload, http_status) shaped like the existing /api/shell reply,
    so the endpoint's contract does not change for callers that were already
    sending reversible or low-risk commands.
    """
    try:
        risk_enum = Risk(risk)
    except ValueError:
        return {"status": "error", "error": f"unknown risk {risk!r}; "
                f"expected one of {[r.value for r in Risk]}"}, 400

    tx = manager.execute(manager.create(
        command, rollback=rollback, risk=risk_enum, actor=actor,
    ))

    payload = {
        "tx_id": tx.id,
        "command": tx.command,
        "state": tx.state.value,
        "reversible": tx.reversible,
        "risk": tx.risk.value,
    }
    if tx.approval_id:
        payload["approval_id"] = tx.approval_id

    if tx.state is TxState.COMMITTED:
        payload.update({"status": "ok", **(tx.result or {})})
        return payload, 200
    if tx.state is TxState.BLOCKED:
        payload.update({"status": "blocked", "reason": tx.error})
        return payload, 403
    if tx.state is TxState.DENIED:
        payload.update({"status": "denied", "reason": tx.error})
        return payload, 403
    if tx.state is TxState.ROLLED_BACK:
        payload.update({"status": "rolled_back", "error": tx.error,
                        "rollback": tx.rollback_result})
        return payload, 500
    # ROLLBACK_FAILED: the command failed AND the undo failed. Nobody designed
    # this state; say so plainly rather than returning a generic 500.
    payload.update({
        "status": "rollback_failed",
        "error": tx.error,
        "rollback": tx.rollback_result,
        "action_required": "System state is undefined. Inspect before retrying.",
    })
    return payload, 500


def adopt_in_jacky_api() -> str:
    """The exact change to make when you want this live. Returns it as text so
    it lives next to the code it describes instead of rotting in a doc."""
    return '''
In jacky_api.py, above the route:

    from shell_tx import build_manager, run_shell_transaction
    SHELL_TX = build_manager(_shell_allowed)

Then replace the body of api_shell() after the auth check with:

    data     = request.get_json(silent=True) or {}
    command  = (data.get("command") or "").strip()
    if not command:
        return jsonify({"error": "command is required"}), 400

    payload, status = run_shell_transaction(
        SHELL_TX, command,
        rollback=(data.get("rollback") or "").strip() or None,
        risk=data.get("risk", "medium"),
        actor=session.get("user", "owner"),
    )
    return jsonify(payload), status

Behaviour change to expect, so nothing surprises you:
  * A command with no `rollback` and risk high/critical now needs approval and
    will 403 with status="denied" if nobody answers inside the timeout.
  * Existing callers that send only {"command": ...} default to risk=medium
    and reversible=False, so they WILL start requiring approval. Send
    "risk": "low" for the read-only ones (Get-Date, Get-Process) to keep them
    running untouched.
  * Approvals are served by GATE; expose them with two small routes
    (GET /api/approvals -> GATE.pending(), POST /api/approvals/<id> ->
    GATE.decide(...)) or nothing will ever be approved.
'''.strip()

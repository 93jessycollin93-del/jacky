#!/usr/bin/env python3
"""
TRANSACTIONS - reversible commands, with rollback that is actually attempted.

/api/shell runs PowerShell against a regex allow-list. That gates WHICH
commands run; it says nothing about undoing one that ran and went wrong.
This adds the missing half.

Every state-changing command becomes a Transaction carrying its own undo. The
manager, not the caller, owns the sequence:

    approve (if needed) -> verify -> run -> commit
                                       \\-> rollback under TTT -> escalate

Three rules worth stating, because the tempting shortcuts are all wrong:

  * A command with no rollback is IRREVERSIBLE and needs human approval.
    Not a warning in a log nobody reads -- a decision someone makes.

  * Rollback failure is louder than the original failure. The system is now in
    a state nobody designed. It escalates; it does not retry forever, and it
    does not pretend the rollback worked.

  * The audit log is hash-chained. An entry edited or removed after the fact
    breaks verify() at exactly that position.

Stdlib only. Windows-safe (os.replace is atomic on NTFS as well as POSIX).

Frame: It's Jacky's PC. If it can't be undone, you get asked first.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from approval import GATE, ApprovalGate, Decision, Risk
from ttt import Outcome, TTTPolicy, resolve

log = logging.getLogger("Transactions")

JACKY_HOME = Path(__file__).parent


class TxState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    RUNNING = "running"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"   # the one that wakes somebody up
    DENIED = "denied"
    BLOCKED = "blocked"


@dataclass
class Transaction:
    id: str
    command: str
    rollback: Optional[str]
    risk: Risk
    actor: str
    created_at: float
    state: TxState = TxState.PENDING
    result: Optional[dict] = None
    rollback_result: Optional[dict] = None
    approval_id: Optional[str] = None
    error: Optional[str] = None
    context: dict = field(default_factory=dict)

    @property
    def reversible(self) -> bool:
        return bool(self.rollback)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["risk"] = self.risk.value
        d["state"] = self.state.value
        d["reversible"] = self.reversible
        return d


class AuditLog:
    """Append-only, hash-chained. Optionally mirrored to disk."""

    GENESIS = hashlib.blake2b(b"jacky/tx-audit/v1", digest_size=16).hexdigest()

    def __init__(self, path: Optional[Path] = None):
        self._entries: List[dict] = []
        self._lock = threading.RLock()
        self.path = Path(path) if path else None

    def append(self, tx_id: str, op: str, detail: dict) -> dict:
        with self._lock:
            prev = self._entries[-1]["entry_hash"] if self._entries else self.GENESIS
            body = {"ts": time.time(), "tx_id": tx_id, "op": op,
                    "detail": detail, "prev": prev}
            body["entry_hash"] = hashlib.blake2b(
                json.dumps(body, sort_keys=True, default=str).encode(), digest_size=16
            ).hexdigest()
            self._entries.append(body)
            self._flush()
            return body

    def verify(self) -> bool:
        prev = self.GENESIS
        with self._lock:
            for e in self._entries:
                body = {k: v for k, v in e.items() if k != "entry_hash"}
                if body["prev"] != prev:
                    return False
                expect = hashlib.blake2b(
                    json.dumps(body, sort_keys=True, default=str).encode(), digest_size=16
                ).hexdigest()
                if expect != e["entry_hash"]:
                    return False
                prev = e["entry_hash"]
        return True

    def entries(self, tx_id: Optional[str] = None) -> List[dict]:
        with self._lock:
            if tx_id is None:
                return list(self._entries)
            return [e for e in self._entries if e["tx_id"] == tx_id]

    def _flush(self) -> None:
        if not self.path:
            return
        tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(self._entries, default=str), encoding="utf-8")
        os.replace(tmp, self.path)          # atomic on NTFS and POSIX alike

    def __len__(self) -> int:
        return len(self._entries)


class TransactionManager:
    """Owns the run/rollback sequence. Callers supply only the runner."""

    def __init__(self, runner: Callable[[str], dict], *,
                 gate: Optional[ApprovalGate] = None,
                 policy: Optional[TTTPolicy] = None,
                 audit: Optional[AuditLog] = None,
                 approval_timeout_s: float = 300.0,
                 guard: Optional[Callable[[str], tuple]] = None):
        """runner(command) -> dict; must raise on failure.

        guard(command) -> (allowed: bool, reason: str). Wire jacky_api's
        _shell_allowed in here so the allow-list still applies -- to the
        rollback command too, which is the easy one to forget.
        """
        self.runner = runner
        self.gate = gate or GATE
        self.policy = policy or TTTPolicy()
        self.audit = audit or AuditLog()
        self.approval_timeout_s = approval_timeout_s
        self.guard = guard
        self._txs: Dict[str, Transaction] = {}
        self._lock = threading.RLock()

    # -- create --------------------------------------------------------
    def create(self, command: str, *, rollback: Optional[str] = None,
               risk: Risk = Risk.MEDIUM, actor: str = "owner",
               context: Optional[dict] = None) -> Transaction:
        tx = Transaction(
            id="tx_" + uuid.uuid4().hex[:12],
            command=command,
            rollback=rollback,
            risk=risk,
            actor=actor,
            created_at=time.time(),
            context=dict(context or {}),
        )
        with self._lock:
            self._txs[tx.id] = tx
        self.audit.append(tx.id, "create", {
            "command": command[:400], "reversible": tx.reversible,
            "risk": risk.value, "actor": actor,
        })
        return tx

    # -- execute -------------------------------------------------------
    def execute(self, tx: Transaction) -> Transaction:
        """Approve if needed, guard, run, and roll back on failure."""
        # 1. allow-list, for the forward command AND its undo
        if self.guard is not None:
            for label, cmd in (("command", tx.command), ("rollback", tx.rollback)):
                if not cmd:
                    continue
                allowed, reason = self.guard(cmd)
                if not allowed:
                    tx.state = TxState.BLOCKED
                    tx.error = f"{label} blocked: {reason}"
                    self.audit.append(tx.id, "blocked", {"which": label, "reason": reason})
                    return tx

        # 2. consent. Irreversible always asks, whatever its risk band.
        if not tx.reversible or tx.risk in (Risk.HIGH, Risk.CRITICAL):
            req = self.gate.request(
                tx.command, risk=tx.risk, reversible=tx.reversible,
                timeout_s=self.approval_timeout_s,
                context={"tx_id": tx.id, "rollback": tx.rollback},
            )
            tx.approval_id = req.id
            decision = self.gate.wait(req.id)
            self.audit.append(tx.id, "approval", {
                "approval_id": req.id, "decision": decision.value,
            })
            if not self.gate.is_granted(decision):
                tx.state = TxState.DENIED
                tx.error = f"not approved ({decision.value})"
                return tx
            tx.state = TxState.APPROVED

        # 3. run
        tx.state = TxState.RUNNING
        try:
            tx.result = self.runner(tx.command)
            tx.state = TxState.COMMITTED
            self.audit.append(tx.id, "commit", {"command": tx.command[:400]})
            return tx
        except Exception as exc:
            tx.error = f"{type(exc).__name__}: {exc}"
            self.audit.append(tx.id, "failed", {"error": tx.error})
            return self._rollback(tx)

    # -- rollback ------------------------------------------------------
    def _rollback(self, tx: Transaction) -> Transaction:
        """Undo under TTT. A failed rollback escalates rather than looping."""
        if not tx.reversible:
            tx.state = TxState.ROLLBACK_FAILED
            self.audit.append(tx.id, "rollback_impossible", {
                "error": tx.error,
                "note": "irreversible command failed; no undo exists",
            })
            log.error("tx %s failed with no rollback available: %s", tx.id, tx.error)
            return tx

        outcome = resolve(
            lambda cmd: self.runner(cmd),
            subject=tx.rollback,
            policy=self.policy,
        )
        tx.rollback_result = outcome.summary()

        if outcome.succeeded:
            tx.state = TxState.ROLLED_BACK
            self.audit.append(tx.id, "rolled_back", {
                "executions": outcome.executions, "cycles": outcome.cycles_used,
            })
            log.info("tx %s rolled back after %d execution(s)", tx.id, outcome.executions)
        else:
            tx.state = TxState.ROLLBACK_FAILED
            self.audit.append(tx.id, "rollback_failed", {
                "outcome": outcome.outcome.value, "reason": outcome.reason,
                "executions": outcome.executions,
            })
            log.error("tx %s ROLLBACK FAILED (%s) -- state is undefined, escalating",
                      tx.id, outcome.reason)
        return tx

    # -- inspect -------------------------------------------------------
    def get(self, tx_id: str) -> Optional[Transaction]:
        with self._lock:
            return self._txs.get(tx_id)

    def needs_attention(self) -> List[Transaction]:
        """Transactions a human should look at. Rollback failures first."""
        with self._lock:
            txs = list(self._txs.values())
        rank = {TxState.ROLLBACK_FAILED: 0, TxState.BLOCKED: 1, TxState.DENIED: 2}
        return sorted((t for t in txs if t.state in rank), key=lambda t: rank[t.state])

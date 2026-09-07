#!/usr/bin/env python3
"""
APPROVAL GATE - human consent for risky actions, without blocking the server.

The obvious implementation is input(). It is also wrong here. jacky_api runs
under waitress with 8 worker threads (serve.py); a blocking read on stdin in a
request thread hangs that worker forever, there is no stdin to read from when
running as a service, and nothing about it survives a restart. An approval
system that cannot run headless is not an approval system.

So: a request registers a pending decision and returns immediately. The owner
approves or denies out of band -- the SAS dashboard, a CLI, any caller of
decide(). The executor waits with a deadline it chose, and an unanswered
request EXPIRES.

Expiry denies. That is the direction that fails safe: if nobody is watching,
the destructive thing does not happen.

Stdlib only, thread-safe, no third-party deps.

Frame: It's Jacky's PC. Nothing irreversible happens without you saying so.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("Approval")

JACKY_HOME = Path(__file__).parent


class Decision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"      # nobody answered in time -> treated as denied
    AUTO = "auto_approved"   # matched a standing low-risk rule


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"    # never auto-approved, ever


@dataclass
class ApprovalRequest:
    id: str
    action: str
    risk: Risk
    reversible: bool
    requested_at: float
    expires_at: float
    context: dict = field(default_factory=dict)
    decision: Decision = Decision.PENDING
    decided_at: Optional[float] = None
    decided_by: Optional[str] = None
    note: str = ""

    def fingerprint(self) -> str:
        """Stable across processes and restarts.

        Deliberately blake2b and not hash(): Python randomises string hashing
        per process (PYTHONHASHSEED), so hash() would give this request a
        different identity after every restart.
        """
        return hashlib.blake2b(self.action.encode("utf-8"), digest_size=8).hexdigest()

    def is_open(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        return self.decision is Decision.PENDING and now < self.expires_at

    def to_dict(self) -> dict:
        d = asdict(self)
        d["risk"] = self.risk.value
        d["decision"] = self.decision.value
        d["fingerprint"] = self.fingerprint()
        return d


class ApprovalGate:
    """Pending-decision registry. Non-blocking by construction."""

    def __init__(self, default_timeout_s: float = 300.0,
                 auto_approve_low_risk_reversible: bool = False):
        self._lock = threading.RLock()
        self._requests: Dict[str, ApprovalRequest] = {}
        self._events: Dict[str, threading.Event] = {}
        self.default_timeout_s = default_timeout_s
        self.auto_approve_low_risk_reversible = auto_approve_low_risk_reversible

    # -- request -------------------------------------------------------
    def request(self, action: str, *, risk: Risk = Risk.MEDIUM,
                reversible: bool = True, timeout_s: Optional[float] = None,
                context: Optional[dict] = None) -> ApprovalRequest:
        """Register a decision. Returns immediately; never blocks."""
        now = time.time()
        timeout = self.default_timeout_s if timeout_s is None else timeout_s
        req = ApprovalRequest(
            id="apr_" + uuid.uuid4().hex[:12],
            action=action,
            risk=risk,
            reversible=reversible,
            requested_at=now,
            expires_at=now + timeout,
            context=dict(context or {}),
        )

        # Standing rule for the boring cases -- never for CRITICAL, and never
        # for anything that cannot be undone.
        if (self.auto_approve_low_risk_reversible
                and risk is Risk.LOW and reversible):
            req.decision = Decision.AUTO
            req.decided_at = now
            req.decided_by = "policy:auto_low_risk_reversible"

        with self._lock:
            self._requests[req.id] = req
            ev = threading.Event()
            self._events[req.id] = ev
            if req.decision is not Decision.PENDING:
                ev.set()

        log.info("approval %s [%s risk=%s reversible=%s] %s",
                 req.id, req.decision.value, risk.value, reversible, action[:120])
        return req

    # -- decide --------------------------------------------------------
    def decide(self, request_id: str, approve: bool, *,
               actor: str = "owner", note: str = "") -> ApprovalRequest:
        """Approve or deny. Idempotent: a settled request is never re-decided."""
        with self._lock:
            req = self._requests.get(request_id)
            if req is None:
                raise KeyError(f"unknown approval request {request_id!r}")
            if req.decision is not Decision.PENDING:
                return req                      # already settled; first answer wins
            if time.time() >= req.expires_at:
                req.decision = Decision.EXPIRED
                req.decided_at = time.time()
                req.note = "expired before a decision arrived"
            else:
                req.decision = Decision.APPROVED if approve else Decision.DENIED
                req.decided_at = time.time()
                req.decided_by = actor
                req.note = note
            self._events[request_id].set()
        log.info("approval %s -> %s by %s", request_id, req.decision.value, req.decided_by)
        return req

    # -- wait ----------------------------------------------------------
    def wait(self, request_id: str, timeout_s: Optional[float] = None) -> Decision:
        """Block THIS caller (not the registry) until decided or expired.

        Callers choose their own patience. Nothing else in the process is held
        up, and an unanswered request expires to a denial.
        """
        with self._lock:
            req = self._requests.get(request_id)
            if req is None:
                raise KeyError(f"unknown approval request {request_id!r}")
            ev = self._events[request_id]

        budget = req.expires_at - time.time()
        if timeout_s is not None:
            budget = min(budget, timeout_s)

        if budget > 0:
            ev.wait(budget)

        with self._lock:
            if req.decision is Decision.PENDING and time.time() >= req.expires_at:
                req.decision = Decision.EXPIRED
                req.decided_at = time.time()
                req.note = "expired before a decision arrived"
                ev.set()
            return req.decision

    def is_granted(self, decision: Decision) -> bool:
        """Only two states permit execution. Expiry is not one of them."""
        return decision in (Decision.APPROVED, Decision.AUTO)

    # -- inspect -------------------------------------------------------
    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            return self._requests.get(request_id)

    def pending(self) -> List[ApprovalRequest]:
        """Open requests, expiring any that have aged out."""
        now = time.time()
        out = []
        with self._lock:
            for req in self._requests.values():
                if req.decision is Decision.PENDING and now >= req.expires_at:
                    req.decision = Decision.EXPIRED
                    req.decided_at = now
                    req.note = "expired before a decision arrived"
                    self._events[req.id].set()
                elif req.is_open(now):
                    out.append(req)
        return sorted(out, key=lambda r: r.requested_at)

    def history(self, limit: int = 100) -> List[dict]:
        with self._lock:
            reqs = sorted(self._requests.values(), key=lambda r: r.requested_at, reverse=True)
        return [r.to_dict() for r in reqs[:limit]]

    def purge_settled(self, older_than_s: float = 3600.0) -> int:
        """Drop long-settled requests so the registry does not grow forever."""
        cutoff = time.time() - older_than_s
        with self._lock:
            drop = [rid for rid, r in self._requests.items()
                    if r.decision is not Decision.PENDING
                    and (r.decided_at or 0) < cutoff]
            for rid in drop:
                self._requests.pop(rid, None)
                self._events.pop(rid, None)
        return len(drop)


# Process-wide gate, so the API layer and the executor share one registry.
GATE = ApprovalGate()

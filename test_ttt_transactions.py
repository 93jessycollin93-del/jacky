#!/usr/bin/env python3
"""
Tests for the TTT doctrine, the approval gate, and reversible transactions.

Runs under pytest, or standalone (`python test_ttt_transactions.py`) so it
works on the Windows box without installing pytest.

Every test here is meant to FAIL if the behaviour regresses. In particular the
three properties that are easy to write and easy to get wrong:

  * TTT is bounded, and stops early when a cycle learns nothing.
  * Approval never blocks the server, and an unanswered request denies.
  * A failed rollback is surfaced, not swallowed.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from approval import ApprovalGate, Decision, Risk          # noqa: E402
from transactions import (                                  # noqa: E402
    AuditLog, Transaction, TransactionManager, TxState,
)
from shell_tx import adopt_in_jacky_api, run_shell_transaction  # noqa: E402
from ttt import Outcome, TTTPolicy, resolve                 # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
class Recorder:
    """A runner that succeeds or fails on command, and remembers what it ran."""

    def __init__(self, fail_on=(), fail_times=None):
        self.ran = []
        self.fail_on = set(fail_on)
        self.fail_times = dict(fail_times or {})

    def __call__(self, command: str) -> dict:
        self.ran.append(command)
        if command in self.fail_times:
            if self.fail_times[command] > 0:
                self.fail_times[command] -= 1
                raise RuntimeError(f"transient failure running {command!r}")
            return {"stdout": "ok after retry", "exit_code": 0}
        if command in self.fail_on:
            raise RuntimeError(f"command failed: {command!r}")
        return {"stdout": "ok", "exit_code": 0}


def allow_all(cmd):
    return True, "ok"


# ---------------------------------------------------------------------------
# TTT
# ---------------------------------------------------------------------------
class TestTTTDoctrine:
    def test_budget_is_36_at_the_documented_defaults(self):
        assert TTTPolicy().budget == 36

    def test_success_short_circuits_immediately(self):
        calls = []
        r = resolve(lambda s: calls.append(s) or "done", subject="x")
        assert r.outcome is Outcome.SUCCESS
        assert r.executions == 1, "a working command must run exactly once"

    def test_never_exceeds_its_ceiling(self):
        """The property the transcript's version lacked: a hard ceiling."""
        policy = TTTPolicy(stop_without_advancement=False)
        n = 0

        def fail(_s):
            nonlocal n
            n += 1
            raise RuntimeError(f"distinct failure {n}")   # always novel

        r = resolve(fail, subject="x", policy=policy,
                    propose=lambda s, t: ["a", "b", "c"])
        assert r.executions == policy.budget == 36
        assert r.outcome is Outcome.ESCALATE

    def test_stops_early_when_a_cycle_learns_nothing(self):
        """'If no reasoning of advancement is met, report back.'"""
        r = resolve(lambda s: (_ for _ in ()).throw(RuntimeError("same every time")),
                    subject="x")
        assert r.outcome is Outcome.NO_ADVANCEMENT
        assert r.cycles_used == 2, "should stop at cycle 2, not burn all 3"
        assert r.executions == 6, "6 executions, not the full 36"

    def test_keeps_going_while_it_is_still_learning(self):
        seen = {"n": 0}

        def novel(_s):
            seen["n"] += 1
            raise RuntimeError(f"new failure {seen['n']}")

        r = resolve(novel, subject="x")
        assert r.cycles_used == 3, "novel failures each cycle means keep trying"
        assert r.outcome is Outcome.ESCALATE

    def test_candidates_are_tried_after_direct_attempts(self):
        tried = []

        def only_c_works(s):
            tried.append(s)
            if s != "c":
                raise RuntimeError("nope")
            return "worked"

        r = resolve(only_c_works, subject="a",
                    propose=lambda s, t: ["b", "c", "d"])
        assert r.outcome is Outcome.SUCCESS
        assert r.value == "worked"
        assert tried[:3] == ["a", "a", "a"], "direct attempts come first"
        assert "c" in tried

    def test_a_broken_proposer_does_not_mask_the_real_failure(self):
        def bad_proposer(s, t):
            raise ValueError("proposer itself is broken")

        r = resolve(lambda s: (_ for _ in ()).throw(RuntimeError("real problem")),
                    subject="x", propose=bad_proposer)
        assert r.outcome in (Outcome.NO_ADVANCEMENT, Outcome.ESCALATE)
        assert any("real problem" in (t.error or "") for t in r.trials)

    def test_escalation_handler_is_called(self):
        got = []
        resolve(lambda s: (_ for _ in ()).throw(RuntimeError("x")),
                subject="s", on_escalate=got.append)
        assert len(got) == 1 and got[0].outcome is Outcome.NO_ADVANCEMENT

    def test_rejects_a_nonsense_policy(self):
        try:
            resolve(lambda s: s, subject="x", policy=TTTPolicy(max_attempts=0))
        except ValueError:
            return
        raise AssertionError("max_attempts=0 must be rejected")


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------
class TestApprovalGate:
    def test_request_does_not_block(self):
        g = ApprovalGate()
        t0 = time.perf_counter()
        g.request("Remove-Item -Recurse C:\\x", risk=Risk.CRITICAL, reversible=False)
        assert (time.perf_counter() - t0) < 0.1, "request() must return immediately"

    def test_decision_arrives_out_of_band(self):
        g = ApprovalGate(default_timeout_s=5.0)
        req = g.request("Restart-Service Jacky", risk=Risk.HIGH)
        threading.Timer(0.1, lambda: g.decide(req.id, True, actor="eru")).start()
        assert g.wait(req.id) is Decision.APPROVED
        assert g.is_granted(Decision.APPROVED)

    def test_unanswered_request_expires_and_is_denied(self):
        """Fail-safe: if nobody is watching, the destructive thing waits."""
        g = ApprovalGate(default_timeout_s=0.2)
        req = g.request("Format-Volume -DriveLetter D", risk=Risk.CRITICAL,
                        reversible=False)
        d = g.wait(req.id)
        assert d is Decision.EXPIRED
        assert not g.is_granted(d), "expiry must never grant execution"

    def test_denial_is_not_granted(self):
        g = ApprovalGate(default_timeout_s=5.0)
        req = g.request("shutdown /s", risk=Risk.CRITICAL, reversible=False)
        g.decide(req.id, False, actor="eru", note="not now")
        assert not g.is_granted(g.wait(req.id))

    def test_first_decision_wins(self):
        g = ApprovalGate(default_timeout_s=5.0)
        req = g.request("Stop-Process -Name ollama", risk=Risk.HIGH)
        g.decide(req.id, False, actor="eru")
        g.decide(req.id, True, actor="someone_else")     # must not override
        assert g.get(req.id).decision is Decision.DENIED
        assert g.get(req.id).decided_by == "eru"

    def test_critical_is_never_auto_approved(self):
        g = ApprovalGate(auto_approve_low_risk_reversible=True)
        assert g.request("Get-Date", risk=Risk.LOW).decision is Decision.AUTO
        crit = g.request("rm -rf /", risk=Risk.CRITICAL, reversible=False)
        assert crit.decision is Decision.PENDING, "CRITICAL must always ask"

    def test_irreversible_is_never_auto_approved(self):
        g = ApprovalGate(auto_approve_low_risk_reversible=True)
        req = g.request("Clear-EventLog", risk=Risk.LOW, reversible=False)
        assert req.decision is Decision.PENDING

    def test_fingerprint_is_stable_not_pythons_randomised_hash(self):
        """Regression guard: hash() varies per process; blake2b does not."""
        g = ApprovalGate()
        a = g.request("Get-Process").fingerprint()
        b = g.request("Get-Process").fingerprint()
        assert a == b, "same action must fingerprint identically"
        # Pinned literal: this is the value blake2b produces on ANY machine, in
        # any process. hash("Get-Process") would differ on every interpreter
        # start, which is what silently broke the transcript's identity kernel.
        assert a == "f1d0199446399be3"

    def test_pending_list_expires_stale_entries(self):
        g = ApprovalGate(default_timeout_s=0.15)
        g.request("Get-Service", risk=Risk.HIGH)
        assert len(g.pending()) == 1
        time.sleep(0.25)
        assert g.pending() == []

    def test_purge_settled_bounds_the_registry(self):
        g = ApprovalGate(default_timeout_s=5.0)
        req = g.request("Get-Date", risk=Risk.HIGH)
        g.decide(req.id, True)
        assert g.purge_settled(older_than_s=-1) == 1


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
class TestTransactions:
    def _mgr(self, runner, **kw):
        """Short approval budget by default.

        TransactionManager.approval_timeout_s overrides the gate's own default
        (the manager decides how long *it* is willing to wait), so a test that
        sets only the gate timeout would sit here for the full 300s.
        """
        gate = kw.pop("gate", ApprovalGate(default_timeout_s=1.0))
        kw.setdefault("approval_timeout_s", 1.0)
        return TransactionManager(runner, gate=gate, guard=allow_all, **kw)

    def test_successful_command_commits(self):
        r = Recorder()
        m = self._mgr(r)
        tx = m.execute(m.create("Get-Date", rollback="echo noop", risk=Risk.LOW))
        assert tx.state is TxState.COMMITTED
        assert r.ran == ["Get-Date"], "no rollback on success"

    def test_failure_triggers_rollback(self):
        r = Recorder(fail_on=["New-Item bad"])
        m = self._mgr(r)
        tx = m.execute(m.create("New-Item bad", rollback="Remove-Item bad",
                                risk=Risk.LOW))
        assert tx.state is TxState.ROLLED_BACK
        assert "Remove-Item bad" in r.ran

    def test_rollback_retries_under_ttt_then_succeeds(self):
        r = Recorder(fail_on=["do"], fail_times={"undo": 2})
        m = self._mgr(r)
        tx = m.execute(m.create("do", rollback="undo", risk=Risk.LOW))
        assert tx.state is TxState.ROLLED_BACK
        assert r.ran.count("undo") == 3, "two transient failures then success"

    def test_failed_rollback_is_surfaced_not_swallowed(self):
        """The state nobody designed. It must be loud."""
        r = Recorder(fail_on=["do", "undo"])
        m = self._mgr(r)
        tx = m.execute(m.create("do", rollback="undo", risk=Risk.LOW))
        assert tx.state is TxState.ROLLBACK_FAILED
        assert tx in m.needs_attention()
        assert m.needs_attention()[0].state is TxState.ROLLBACK_FAILED

    def test_irreversible_failure_has_no_undo_and_says_so(self):
        r = Recorder(fail_on=["Format-Volume"])
        gate = ApprovalGate(default_timeout_s=5.0)
        m = self._mgr(r, gate=gate, approval_timeout_s=5.0)
        tx = m.create("Format-Volume", rollback=None, risk=Risk.CRITICAL)
        threading.Timer(0.05, lambda: gate.decide(tx_approval(gate), True)).start()
        tx = m.execute(tx)
        assert tx.state is TxState.ROLLBACK_FAILED
        ops = [e["op"] for e in m.audit.entries(tx.id)]
        assert "rollback_impossible" in ops

    def test_irreversible_command_requires_approval(self):
        r = Recorder()
        gate = ApprovalGate(default_timeout_s=0.2)     # nobody answers
        m = self._mgr(r, gate=gate, approval_timeout_s=0.2)
        tx = m.execute(m.create("Clear-EventLog", rollback=None, risk=Risk.HIGH))
        assert tx.state is TxState.DENIED
        assert r.ran == [], "an unapproved command must never run"

    def test_low_risk_reversible_runs_without_asking(self):
        r = Recorder()
        m = self._mgr(r)
        tx = m.execute(m.create("Get-Date", rollback="echo noop", risk=Risk.LOW))
        assert tx.approval_id is None
        assert tx.state is TxState.COMMITTED

    def test_guard_blocks_the_forward_command(self):
        r = Recorder()
        m = TransactionManager(r, gate=ApprovalGate(),
                               guard=lambda c: (False, "not in allow-list"))
        tx = m.execute(m.create("anything", rollback="undo", risk=Risk.LOW))
        assert tx.state is TxState.BLOCKED and r.ran == []

    def test_guard_also_checks_the_rollback_command(self):
        """The easy one to forget: an undo that itself is not permitted."""
        r = Recorder()
        m = TransactionManager(
            r, gate=ApprovalGate(),
            guard=lambda c: (c != "rm -rf /", "rollback not in allow-list"),
        )
        tx = m.execute(m.create("Get-Date", rollback="rm -rf /", risk=Risk.LOW))
        assert tx.state is TxState.BLOCKED
        assert r.ran == [], "must be caught before the forward command runs"
        assert "rollback" in (tx.error or "")


class TestAuditLog:
    def test_records_the_whole_sequence(self):
        r = Recorder(fail_on=["do"])
        m = TransactionManager(r, gate=ApprovalGate(), guard=allow_all)
        tx = m.execute(m.create("do", rollback="undo", risk=Risk.LOW))
        ops = [e["op"] for e in m.audit.entries(tx.id)]
        assert ops == ["create", "failed", "rolled_back"]

    def test_chain_verifies(self):
        log = AuditLog()
        for i in range(5):
            log.append(f"tx{i}", "create", {"n": i})
        assert log.verify()

    def test_tampering_breaks_the_chain(self):
        log = AuditLog()
        for i in range(5):
            log.append(f"tx{i}", "create", {"n": i})
        log._entries[2]["detail"]["n"] = 999
        assert not log.verify()

    def test_deletion_breaks_the_chain(self):
        log = AuditLog()
        for i in range(5):
            log.append(f"tx{i}", "create", {"n": i})
        del log._entries[2]
        assert not log.verify()

    def test_survives_a_disk_round_trip(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "audit.json"
            log = AuditLog(path=p)
            log.append("tx1", "create", {"command": "Get-Date"})
            assert p.exists()
            import json as _json
            assert _json.loads(p.read_text())[0]["op"] == "create"


# ---------------------------------------------------------------------------
# shell_tx adapter
# ---------------------------------------------------------------------------
class TestShellTxAdapter:
    def _mgr(self, runner, guard=allow_all):
        return TransactionManager(runner, gate=ApprovalGate(default_timeout_s=0.2),
                                  guard=guard, approval_timeout_s=0.2)

    def test_low_risk_reversible_returns_200_ok(self):
        payload, status = run_shell_transaction(
            self._mgr(Recorder()), "Get-Date", rollback="echo x", risk="low")
        assert status == 200 and payload["status"] == "ok"
        assert payload["tx_id"].startswith("tx_")

    def test_failure_reports_rolled_back_with_500(self):
        r = Recorder(fail_on=["break"])
        payload, status = run_shell_transaction(
            self._mgr(r), "break", rollback="undo", risk="low")
        assert status == 500 and payload["status"] == "rolled_back"
        assert "undo" in r.ran

    def test_rollback_failure_says_state_is_undefined(self):
        r = Recorder(fail_on=["break", "undo"])
        payload, status = run_shell_transaction(
            self._mgr(r), "break", rollback="undo", risk="low")
        assert status == 500 and payload["status"] == "rollback_failed"
        assert "action_required" in payload, "a failed undo must not look like a normal 500"

    def test_guard_rejection_is_403_blocked(self):
        mgr = self._mgr(Recorder(), guard=lambda c: (False, "not in allow-list"))
        payload, status = run_shell_transaction(mgr, "anything", risk="low")
        assert status == 403 and payload["status"] == "blocked"

    def test_unanswered_approval_is_403_denied_and_nothing_ran(self):
        r = Recorder()
        payload, status = run_shell_transaction(
            self._mgr(r), "Clear-EventLog", risk="high")
        assert status == 403 and payload["status"] == "denied"
        assert r.ran == [], "denied command must never execute"

    def test_unknown_risk_is_rejected_before_anything_runs(self):
        r = Recorder()
        payload, status = run_shell_transaction(self._mgr(r), "x", risk="nonsense")
        assert status == 400 and r.ran == []

    def test_adoption_notes_exist_and_name_the_gotcha(self):
        """The behaviour change is the thing a reader must not miss."""
        notes = adopt_in_jacky_api()
        assert "_shell_allowed" in notes
        assert "risk" in notes and "low" in notes
        assert "GATE.pending()" in notes, "must say how approvals get answered"


def tx_approval(gate):
    """The id of the single pending request (test helper)."""
    for _ in range(50):
        p = gate.pending()
        if p:
            return p[0].id
        time.sleep(0.01)
    raise AssertionError("no approval request appeared")


# ---------------------------------------------------------------------------
# standalone runner (no pytest needed)
# ---------------------------------------------------------------------------
def main() -> int:
    import traceback
    classes = [TestTTTDoctrine, TestApprovalGate, TestTransactions,
               TestAuditLog, TestShellTxAdapter]
    passed, failed = 0, []
    for cls in classes:
        inst = cls()
        for name in sorted(n for n in dir(cls) if n.startswith("test_")):
            try:
                getattr(inst, name)()
                passed += 1
            except Exception:
                failed.append(f"{cls.__name__}.{name}\n{traceback.format_exc()}")
    print(f"\n{passed} passed, {len(failed)} failed")
    for f in failed:
        print("\nFAIL:", f)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

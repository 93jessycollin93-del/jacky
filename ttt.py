#!/usr/bin/env python3
"""
TTT - the three-strikes doctrine, with a real budget.

The rule, as stated by the owner:

    3 attempts. If unsuccessful, theorize and/or implement 3 known solutions.
    Test all solutions 3 times each. Use the most logical result. If successful,
    move on. If unsuccessful, loop this process 3 times. If no reasoning of
    advancement is met, report back to your commanding human.

Two things that phrasing implies, and that a naive implementation drops:

  * The work is BOUNDED. cycles x (attempts + solutions x tests) is the whole
    budget: 3 x (3 + 3x3) = 36 executions, worst case. Never more. A retry
    policy without a ceiling is not a policy, it is a way to hang.

  * "If no reasoning of advancement is met" is a STOP condition, not a
    formality at the end. A cycle that learned nothing new -- same failures,
    no candidate getting further than before -- is not worth repeating two
    more times. TTT stops there and escalates, which is the whole point of
    having a commanding human.

Stdlib only. No recursion: depth is an integer this module owns, so a fallback
chain cannot nest its way past the ceiling.

Frame: It's Jacky's PC. Three strikes, then you ask.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional, Sequence

log = logging.getLogger("TTT")


class Outcome(str, Enum):
    SUCCESS = "success"
    ESCALATE = "escalate_to_human"
    EXHAUSTED = "budget_exhausted"
    NO_ADVANCEMENT = "no_advancement"


@dataclass(frozen=True)
class TTTPolicy:
    """The 3/3/3/3 budget. Defaults are the doctrine; raise them deliberately."""

    max_attempts: int = 3           # direct tries per cycle
    max_solutions: int = 3          # alternatives theorized after direct tries fail
    max_tests_per_solution: int = 3 # trials per alternative
    max_cycles: int = 3             # repeats of the whole process
    stop_without_advancement: bool = True

    @property
    def budget(self) -> int:
        """Worst-case number of executions. 36 at the defaults."""
        per_cycle = self.max_attempts + self.max_solutions * self.max_tests_per_solution
        return self.max_cycles * per_cycle

    def validate(self) -> None:
        for name in ("max_attempts", "max_solutions", "max_tests_per_solution", "max_cycles"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1")


@dataclass
class Trial:
    """One execution and what came back."""

    cycle: int
    phase: str                      # "direct" | "candidate"
    candidate: Optional[Any]
    ok: bool
    error: Optional[str]
    progress: float = 0.0           # how far this got; used for advancement
    elapsed_s: float = 0.0


@dataclass
class TTTResult:
    outcome: Outcome
    value: Any = None
    trials: List[Trial] = field(default_factory=list)
    cycles_used: int = 0
    reason: str = ""

    @property
    def executions(self) -> int:
        return len(self.trials)

    @property
    def succeeded(self) -> bool:
        return self.outcome is Outcome.SUCCESS

    def summary(self) -> dict:
        return {
            "outcome": self.outcome.value,
            "cycles_used": self.cycles_used,
            "executions": self.executions,
            "reason": self.reason,
            "distinct_errors": sorted({t.error for t in self.trials if t.error}),
            "best_progress": max((t.progress for t in self.trials), default=0.0),
        }


def resolve(
    action: Callable[[Any], Any],
    *,
    subject: Any,
    policy: Optional[TTTPolicy] = None,
    propose: Optional[Callable[[Any, List[Trial]], Sequence[Any]]] = None,
    progress_of: Optional[Callable[[Any], float]] = None,
    on_escalate: Optional[Callable[[TTTResult], None]] = None,
) -> TTTResult:
    """Run `action` under the TTT doctrine.

    action(subject) -> value, or raises. A raise is a failure; anything
    returned (including None) is a success.

    propose(subject, trials) -> up to max_solutions alternative subjects to
    try once the direct attempts are spent. Called once per cycle, and given
    the trial history so it can propose something informed by what failed. If
    omitted, TTT has no alternatives to test and will spend only its direct
    attempts before escalating -- which is honest, not a bug: inventing
    alternatives is a judgement call this module does not make on its own.

    progress_of(value_or_error) -> float. Optional. Lets the caller say how
    far a trial got, so advancement can be measured on something better than
    "did the error string change".
    """
    policy = policy or TTTPolicy()
    policy.validate()

    result = TTTResult(outcome=Outcome.EXHAUSTED)
    seen_errors: set = set()
    best_progress = 0.0

    for cycle in range(1, policy.max_cycles + 1):
        result.cycles_used = cycle
        cycle_start_errors = set(seen_errors)
        cycle_start_best = best_progress

        # --- direct attempts -------------------------------------------
        for _ in range(policy.max_attempts):
            trial = _run(action, subject, cycle, "direct", None, progress_of)
            result.trials.append(trial)
            if trial.ok:
                result.outcome = Outcome.SUCCESS
                result.value = trial.candidate
                result.reason = f"direct attempt succeeded in cycle {cycle}"
                return result
            seen_errors.add(trial.error)
            best_progress = max(best_progress, trial.progress)

        # --- theorize and test alternatives ----------------------------
        candidates: Sequence[Any] = ()
        if propose is not None:
            try:
                candidates = tuple(propose(subject, list(result.trials)))[: policy.max_solutions]
            except Exception as exc:  # a broken proposer must not mask the real failure
                log.warning("TTT proposer raised, continuing without candidates: %s", exc)
                candidates = ()

        for cand in candidates:
            for _ in range(policy.max_tests_per_solution):
                trial = _run(action, cand, cycle, "candidate", cand, progress_of)
                result.trials.append(trial)
                if trial.ok:
                    result.outcome = Outcome.SUCCESS
                    result.value = trial.candidate
                    result.reason = f"candidate succeeded in cycle {cycle}"
                    return result
                seen_errors.add(trial.error)
                best_progress = max(best_progress, trial.progress)

        # --- advancement check -----------------------------------------
        # Nothing new learned and nothing got further: two more identical
        # cycles will not help. Stop and hand it to the human now.
        learned_something = seen_errors != cycle_start_errors
        got_further = best_progress > cycle_start_best
        if policy.stop_without_advancement and not (learned_something or got_further):
            result.outcome = Outcome.NO_ADVANCEMENT
            result.reason = (
                f"cycle {cycle} produced no new failure mode and no further progress; "
                f"stopping early rather than repeating {policy.max_cycles - cycle} identical cycles"
            )
            _escalate(result, on_escalate)
            return result

    result.outcome = Outcome.ESCALATE
    result.reason = (
        f"exhausted {policy.max_cycles} cycles "
        f"({result.executions} executions, ceiling {policy.budget})"
    )
    _escalate(result, on_escalate)
    return result


def _run(action, subject, cycle, phase, candidate, progress_of) -> Trial:
    t0 = time.perf_counter()
    try:
        value = action(subject)
        return Trial(cycle, phase, value, True, None,
                     _progress(progress_of, value), time.perf_counter() - t0)
    except Exception as exc:
        return Trial(cycle, phase, candidate, False, f"{type(exc).__name__}: {exc}",
                     _progress(progress_of, exc), time.perf_counter() - t0)


def _progress(progress_of, x) -> float:
    if progress_of is None:
        return 0.0
    try:
        return float(progress_of(x))
    except Exception:
        return 0.0


def _escalate(result: TTTResult, on_escalate) -> None:
    log.warning("TTT escalating to human: %s", result.reason)
    if on_escalate is not None:
        try:
            on_escalate(result)
        except Exception as exc:  # pragma: no cover - notifier must not mask the result
            log.error("TTT escalation handler raised: %s", exc)

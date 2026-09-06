"""SAS Superstation - envelope construction, validation, forward-compatible parse.

Python mirror of ``kernel/ts/envelope.ts``. Normative source: ``SPEC.md`` §3-§6.

Three jobs, in order of importance:

1. Make it impossible to emit a reading without saying how real it is.
2. Make an old reader lossless over new data (the ``ext`` sidecar, §6).
3. Make degradation monotonic, so a chain of pods cannot launder a simulated
   number into a live one (:func:`derive`, §4).
"""

from __future__ import annotations

import json
import random
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .contract import (
    KERNEL_VERSION,
    KNOWN_ENVELOPE_KEYS,
    KNOWN_PROVENANCE_KEYS,
    TRUST_THRESHOLD,
    Envelope,
    Provenance,
    compatibility,
    is_capability_id,
    is_fidelity,
    is_pod_id,
    rank_of,
    weakest,
)

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def stamp(at: Optional[float] = None) -> str:
    """RFC 3339 UTC, millisecond precision - the only format §3 allows."""
    dt = datetime.now(timezone.utc) if at is None else datetime.fromtimestamp(at, timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def is_stamp(value: Any) -> bool:
    return isinstance(value, str) and bool(_TS_RE.match(value))


def _parse_stamp_ms(value: str) -> Optional[float]:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        ).timestamp() * 1000.0
    except ValueError:
        return None


def envelope_id() -> str:
    """Unique, not unguessable - nothing authenticates on an envelope id."""
    try:
        return str(uuid.uuid4())
    except Exception:  # pragma: no cover - uuid4 does not realistically fail
        return f"env-{int(datetime.now(timezone.utc).timestamp() * 1000):x}-{random.randrange(1 << 24):06x}"


# --------------------------------------------------------------------------- #
# Provenance constructors
# --------------------------------------------------------------------------- #
#
# These five are the only supported way to build provenance. Each takes exactly
# the fields §4 requires for its rung, so the required-field rules are enforced
# at the call site rather than by a validator after the fact.


def live(source: str, observed_at: Optional[str] = None) -> Provenance:
    return {"fidelity": "live", "source": source, "observedAt": observed_at or stamp()}


def cached(source: str, observed_at: str, stale_ms: Optional[int] = None) -> Provenance:
    if stale_ms is None:
        ms = _parse_stamp_ms(observed_at)
        now = datetime.now(timezone.utc).timestamp() * 1000.0
        stale_ms = max(0, int(now - ms)) if ms is not None else 0
    return {
        "fidelity": "cached",
        "source": source,
        "observedAt": observed_at,
        "staleMs": stale_ms,
    }


def degraded(source: str, reason: str, observed_at: Optional[str] = None) -> Provenance:
    p: Provenance = {"fidelity": "degraded", "source": source, "reason": reason}
    if observed_at:
        p["observedAt"] = observed_at
    return p


def simulated(source: str, reason: str) -> Provenance:
    return {"fidelity": "simulated", "source": source, "reason": reason}


def absent(source: str, reason: str) -> Provenance:
    return {"fidelity": "absent", "source": source, "reason": reason}


# --------------------------------------------------------------------------- #
# Trust
# --------------------------------------------------------------------------- #


def trustworthy(env: Dict[str, Any]) -> bool:
    """Whether a surface may render this value unlabelled.

    The honesty rule in one function: everything below ``cached`` is display-only
    and must be marked.
    """
    prov = env.get("provenance") or {}
    fid = prov.get("fidelity")
    return is_fidelity(fid) and rank_of(fid) >= TRUST_THRESHOLD


_BADGES = {"degraded": "PARTIAL", "simulated": "SIMULATED", "absent": "NO DATA"}


def badge(env: Dict[str, Any]) -> Optional[str]:
    """Badge text for an untrustworthy envelope. ``None`` when trusted."""
    if trustworthy(env):
        return None
    fid = (env.get("provenance") or {}).get("fidelity")
    return _BADGES.get(fid, "UNVERIFIED")


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

#: The §4 required-field rules, as data rather than branching.
REQUIRED_BY_FIDELITY = {
    "live": ("observedAt",),
    "cached": ("observedAt", "staleMs"),
    "degraded": ("reason",),
    "simulated": ("reason",),
    "absent": ("reason",),
}

_UNSET = object()


def _provenance_problems(prov: Any, payload: Any = _UNSET) -> List[str]:
    if not isinstance(prov, dict):
        return ["provenance must be an object"]
    fid = prov.get("fidelity")
    if not is_fidelity(fid):
        return [f"invalid fidelity: {fid!r}"]
    out: List[str] = []
    if not isinstance(prov.get("source"), str) or not prov.get("source"):
        out.append("provenance.source is required")
    for key in REQUIRED_BY_FIDELITY[fid]:
        if prov.get(key) in (None, ""):
            out.append(f'fidelity "{fid}" requires provenance.{key}')
    if "observedAt" in prov and not is_stamp(prov["observedAt"]):
        out.append(f"invalid provenance.observedAt: {prov['observedAt']!r}")
    if "staleMs" in prov:
        stale = prov["staleMs"]
        if isinstance(stale, bool) or not isinstance(stale, int) or stale < 0:
            out.append(f"invalid provenance.staleMs: {stale!r}")
    if fid == "absent" and payload is not _UNSET:
        if not (isinstance(payload, dict) and not payload):
            out.append('fidelity "absent" requires an empty payload')
    return out


def validate(env: Any) -> List[str]:
    """Every §3-§4 rule, as a list. Empty means valid."""
    if not isinstance(env, dict):
        return ["envelope must be an object"]
    out: List[str] = []
    compat = compatibility(env.get("kernel"))
    if compat == "malformed":
        out.append(f"invalid kernel version: {env.get('kernel')!r}")
    elif compat == "incompatible":
        out.append(f"incompatible kernel major: {env.get('kernel')!r}")
    if not is_capability_id(env.get("kind")):
        out.append(f"invalid kind: {env.get('kind')!r}")
    if not is_pod_id(env.get("pod")):
        out.append(f"invalid pod: {env.get('pod')!r}")
    if not isinstance(env.get("id"), str) or not env.get("id"):
        out.append("id is required")
    if not is_stamp(env.get("ts")):
        out.append(f"invalid ts: {env.get('ts')!r}")
    if "payload" not in env:
        out.append("payload is required")
    out.extend(_provenance_problems(env.get("provenance"), env.get("payload", _UNSET)))
    return out


# --------------------------------------------------------------------------- #
# Construction
# --------------------------------------------------------------------------- #


def seal(
    kind: str,
    pod: str,
    payload: Any,
    provenance: Provenance,
    ts: Optional[str] = None,
    ext: Optional[Dict[str, Any]] = None,
) -> Envelope:
    """Build a valid envelope, or raise.

    Raising is deliberate and is the one place this kernel does it: a malformed
    *emit* is a bug in the emitting pod and should fail loudly at the source.
    Malformed *input* is the normal case and goes through :func:`parse`, which
    never raises.
    """
    problems = _provenance_problems(provenance, payload)
    if not is_capability_id(kind):
        problems.append(f"invalid capability id: {kind!r}")
    if not is_pod_id(pod):
        problems.append(f"invalid pod id: {pod!r}")
    if ts is not None and not is_stamp(ts):
        problems.append(f"invalid ts: {ts!r}")
    if problems:
        raise ValueError(f"superstation: cannot seal {kind!r} - {'; '.join(problems)}")
    env: Envelope = {
        "kernel": KERNEL_VERSION,
        "kind": kind,
        "id": envelope_id(),
        "ts": ts or stamp(),
        "pod": pod,
        "provenance": provenance,
        "payload": payload,
    }
    if ext:
        env["ext"] = dict(ext)
    return env


def derive(
    sources: Sequence[Dict[str, Any]],
    kind: str,
    pod: str,
    payload: Any,
    provenance: Provenance,
    ts: Optional[str] = None,
) -> Envelope:
    """Derive an envelope from others, carrying fidelity down.

    A pod cannot claim its output is fresher than the data it was computed from.
    ``absent`` inputs collapse the result to ``absent``: a value computed from
    nothing is nothing.
    """
    fid = provenance["fidelity"]
    reasons: List[str] = []
    for src in sources:
        src_prov = src.get("provenance") or {}
        src_fid = src_prov.get("fidelity")
        if not is_fidelity(src_fid):
            continue
        fid = weakest(fid, src_fid)
        if rank_of(src_fid) < TRUST_THRESHOLD and src_prov.get("reason"):
            reasons.append(src_prov["reason"])

    if fid == provenance["fidelity"]:
        return seal(kind, pod, payload, provenance, ts)

    prov: Provenance = dict(provenance)  # type: ignore[assignment]
    prov["fidelity"] = fid
    inherited = "; ".join(reasons) if reasons else f"derived from {fid} input"
    if rank_of(fid) < TRUST_THRESHOLD:
        existing = provenance.get("reason")
        prov["reason"] = f"{existing} ({inherited})" if existing else inherited
    if fid == "cached":
        observed = sorted(
            [
                s.get("provenance", {}).get("observedAt")
                for s in sources
                if is_stamp(s.get("provenance", {}).get("observedAt"))
            ]
        )
        chosen = observed[0] if observed else prov.get("observedAt") or stamp()
        prov["observedAt"] = chosen
        if "staleMs" not in prov:
            ms = _parse_stamp_ms(chosen)
            now = datetime.now(timezone.utc).timestamp() * 1000.0
            prov["staleMs"] = max(0, int(now - ms)) if ms is not None else 0
    if fid == "absent":
        return seal(kind, pod, {}, prov, ts)
    return seal(kind, pod, payload, prov, ts)


# --------------------------------------------------------------------------- #
# Forward-compatible parsing (SPEC.md §6)
# --------------------------------------------------------------------------- #


class ParseResult:
    """Result of :func:`parse`. Never raises; inspect ``ok``."""

    __slots__ = ("ok", "envelope", "errors", "warnings")

    def __init__(
        self,
        ok: bool,
        envelope: Optional[Envelope],
        errors: List[str],
        warnings: List[str],
    ) -> None:
        self.ok = ok
        self.envelope = envelope
        self.errors = errors
        self.warnings = warnings

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ParseResult(ok={self.ok}, errors={self.errors}, warnings={self.warnings})"


def parse(raw: Any) -> ParseResult:
    """Parse untrusted input into an envelope. Never raises.

    Unknown top-level keys and unknown provenance keys move into ``ext`` rather
    than being dropped, so ``serialize(parse(x)) == x`` for anything a newer
    producer sends. That round trip is the fleet's whole forward-compatibility
    story and is pinned by the conformance vectors.
    """
    warnings: List[str] = []
    if isinstance(raw, (str, bytes)):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return ParseResult(False, None, ["input is not valid JSON"], warnings)
    if not isinstance(raw, dict):
        return ParseResult(False, None, ["envelope must be an object"], warnings)

    if compatibility(raw.get("kernel")) == "forward":
        warnings.append(
            f"envelope kernel {raw.get('kernel')} is newer than reader "
            f"{KERNEL_VERSION}; unknown fields preserved"
        )

    errors = validate(raw)
    if errors:
        return ParseResult(False, None, errors, warnings)

    ext: Dict[str, Any] = dict(raw["ext"]) if isinstance(raw.get("ext"), dict) else {}
    for key in raw:
        if key not in KNOWN_ENVELOPE_KEYS:
            ext[key] = raw[key]
            warnings.append(f'unknown top-level key "{key}" preserved in ext')

    raw_prov = raw["provenance"]
    prov_ext: Dict[str, Any] = (
        dict(raw_prov["ext"]) if isinstance(raw_prov.get("ext"), dict) else {}
    )
    provenance: Provenance = {
        "fidelity": raw_prov["fidelity"],
        "source": raw_prov["source"],
    }
    for key in ("observedAt", "staleMs", "reason"):
        if key in raw_prov:
            provenance[key] = raw_prov[key]  # type: ignore[literal-required]
    for key in raw_prov:
        if key not in KNOWN_PROVENANCE_KEYS:
            prov_ext[key] = raw_prov[key]
            warnings.append(f'unknown provenance key "{key}" preserved in provenance.ext')
    if prov_ext:
        provenance["ext"] = prov_ext

    envelope: Envelope = {
        "kernel": raw["kernel"],
        "kind": raw["kind"],
        "id": raw["id"],
        "ts": raw["ts"],
        "pod": raw["pod"],
        "provenance": provenance,
        "payload": raw["payload"],
    }
    if ext:
        envelope["ext"] = ext
    return ParseResult(True, envelope, [], warnings)


def serialize(env: Envelope) -> Dict[str, Any]:
    """Inverse of :func:`parse`: lift ``ext`` back to the top level."""
    out: Dict[str, Any] = {k: v for k, v in env.items() if k not in ("ext", "provenance")}
    prov = dict(env.get("provenance") or {})
    prov_ext = prov.pop("ext", None)
    if isinstance(prov_ext, dict):
        prov.update(prov_ext)
    out["provenance"] = prov
    out.update(env.get("ext") or {})
    return out


def to_json(env: Envelope) -> str:
    return json.dumps(serialize(env), separators=(",", ":"))

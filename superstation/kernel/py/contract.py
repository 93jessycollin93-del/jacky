"""SAS Superstation - contract types and version rules (Python mirror).

Normative source: ``superstation/SPEC.md``. This module mirrors
``kernel/ts/contract.ts`` field for field; ``superstation/conformance/`` runs the
same vectors through both and fails if they diverge.

Standard library only. The engine has its own dependency budget and this must
not add to it.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, TypedDict

#: Contract version implemented by this kernel. Semver, per SPEC.md §5.
KERNEL_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# Identifiers (SPEC.md §2)
# --------------------------------------------------------------------------- #

CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9-]*){1,5}$")
POD_ID_RE = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z0-9-]+){1,3}$")


def is_capability_id(value: Any) -> bool:
    return isinstance(value, str) and bool(CAPABILITY_ID_RE.match(value))


def is_pod_id(value: Any) -> bool:
    return isinstance(value, str) and bool(POD_ID_RE.match(value))


def id_matches_prefix(cap_id: str, prefix: str) -> bool:
    """Segment-boundary prefix match.

    ``sas.telemetry`` matches ``sas.telemetry.thermal`` but never
    ``sas.telemetryx``.
    """
    if prefix == "*" or prefix == cap_id:
        return True
    return cap_id.startswith(prefix + ".")


# --------------------------------------------------------------------------- #
# Fidelity ladder (SPEC.md §4)
# --------------------------------------------------------------------------- #

Fidelity = Literal["live", "cached", "degraded", "simulated", "absent"]

#: Total order over the ladder. Consumers compare ranks, never strings.
FIDELITY_RANK: Dict[str, int] = {
    "live": 4,
    "cached": 3,
    "degraded": 2,
    "simulated": 1,
    "absent": 0,
}

FIDELITIES: List[str] = list(FIDELITY_RANK)

#: At or above this rank a reading came from the real source and may render
#: unlabelled. One constant, so no surface picks a friendlier threshold.
TRUST_THRESHOLD = FIDELITY_RANK["cached"]


def is_fidelity(value: Any) -> bool:
    return isinstance(value, str) and value in FIDELITY_RANK


def rank_of(fidelity: str) -> int:
    return FIDELITY_RANK[fidelity]


def weakest(a: str, b: str) -> str:
    """The weaker of two fidelities. Degradation through a chain is monotonic."""
    return a if rank_of(a) <= rank_of(b) else b


class Provenance(TypedDict, total=False):
    fidelity: str
    source: str
    observedAt: str
    staleMs: int
    reason: str
    ext: Dict[str, Any]


class Envelope(TypedDict, total=False):
    kernel: str
    kind: str
    id: str
    ts: str
    pod: str
    provenance: Provenance
    payload: Any
    ext: Dict[str, Any]


#: Keys the kernel understands. Everything else round-trips through ``ext``.
KNOWN_ENVELOPE_KEYS = ("kernel", "kind", "id", "ts", "pod", "provenance", "payload", "ext")
KNOWN_PROVENANCE_KEYS = ("fidelity", "source", "observedAt", "staleMs", "reason", "ext")

PodRole = Literal["engine", "surface", "vault", "bot", "knowledge"]
POD_ROLES = ("engine", "surface", "vault", "bot", "knowledge")

# --------------------------------------------------------------------------- #
# Version compatibility (SPEC.md §5)
# --------------------------------------------------------------------------- #

Compatibility = Literal["compatible", "forward", "incompatible", "malformed"]

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_semver(value: Any) -> Optional[Dict[str, int]]:
    if not isinstance(value, str):
        return None
    m = _SEMVER_RE.match(value)
    if not m:
        return None
    return {"major": int(m.group(1)), "minor": int(m.group(2)), "patch": int(m.group(3))}


def compatibility(data_version: Any, reader_version: str = KERNEL_VERSION) -> str:
    """How a reader should treat data at ``data_version``.

    ``forward`` is why the fleet needs no lockstep upgrade: newer-minor data is
    accepted, with its unknown fields preserved rather than dropped.
    """
    d = parse_semver(data_version)
    r = parse_semver(reader_version)
    if d is None or r is None:
        return "malformed"
    if d["major"] != r["major"]:
        return "incompatible"
    if d["minor"] > r["minor"]:
        return "forward"
    return "compatible"


_RANGE_RE = re.compile(r"^(\d+)\.(x|\d+)$")


def satisfies_range(version: str, range_: Optional[str] = None) -> bool:
    """Does a payload-contract ``version`` satisfy a range like ``1.x``?"""
    if not range_:
        return True
    v = parse_semver(version)
    if v is None:
        return False
    m = _RANGE_RE.match(range_)
    if not m:
        return False
    if v["major"] != int(m.group(1)):
        return False
    return m.group(2) == "x" or v["minor"] == int(m.group(2))

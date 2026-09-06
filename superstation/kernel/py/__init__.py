"""SAS Superstation kernel - Python reference implementation.

    from superstation.kernel.py import Station, live

    station = Station(manifest)
    station.publish("sas.telemetry.thermal", {"gpuC": 61}, live("jacky:/api/metrics"))

Contract: ``superstation/SPEC.md``. Cross-language agreement with the TypeScript
kernel is pinned by ``superstation/conformance/``.
"""

from .contract import (  # noqa: F401
    CAPABILITY_ID_RE,
    FIDELITIES,
    FIDELITY_RANK,
    KERNEL_VERSION,
    POD_ID_RE,
    POD_ROLES,
    TRUST_THRESHOLD,
    compatibility,
    id_matches_prefix,
    is_capability_id,
    is_fidelity,
    is_pod_id,
    parse_semver,
    rank_of,
    satisfies_range,
    weakest,
)
from .envelope import (  # noqa: F401
    ParseResult,
    absent,
    badge,
    cached,
    degraded,
    derive,
    envelope_id,
    is_stamp,
    live,
    parse,
    seal,
    serialize,
    simulated,
    stamp,
    to_json,
    trustworthy,
    validate,
)
from .registry import Registry, Resolution  # noqa: F401
from .station import Bus, Station  # noqa: F401

__all__ = [
    "KERNEL_VERSION", "FIDELITIES", "FIDELITY_RANK", "TRUST_THRESHOLD",
    "CAPABILITY_ID_RE", "POD_ID_RE", "POD_ROLES",
    "compatibility", "id_matches_prefix", "is_capability_id", "is_fidelity",
    "is_pod_id", "parse_semver", "rank_of", "satisfies_range", "weakest",
    "ParseResult", "absent", "badge", "cached", "degraded", "derive",
    "envelope_id", "is_stamp", "live", "parse", "seal", "serialize",
    "simulated", "stamp", "to_json", "trustworthy", "validate",
    "Registry", "Resolution", "Bus", "Station",
]

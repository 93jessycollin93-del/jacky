#!/usr/bin/env python3
"""Conformance suite for the Python kernel.

Runs ``vectors/kernel.vectors.json`` - the same file ``conformance.mjs`` runs
against the TypeScript kernel. Two implementations, one set of expectations: a
behaviour that only one of them satisfies fails here rather than drifting
quietly, which is what happened the last time this fleet shared code by copying
files and hoping.

Runs two ways, because the engine repo has no pytest:

    python3 superstation/conformance/test_conformance.py    # standalone
    pytest superstation/conformance/test_conformance.py     # if available
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from superstation.kernel.py import (  # noqa: E402
    KERNEL_VERSION,
    Station,
    badge,
    compatibility,
    derive,
    id_matches_prefix,
    is_capability_id,
    is_pod_id,
    parse,
    satisfies_range,
    serialize,
    trustworthy,
    validate,
)

VECTORS = json.loads((Path(__file__).parent / "vectors" / "kernel.vectors.json").read_text())


def canonical(value: Any) -> str:
    """Order-independent JSON, so key order is never mistaken for a difference."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _env(provenance: Dict[str, Any], payload: Any = None) -> Dict[str, Any]:
    return {"provenance": provenance, "payload": {} if payload is None else payload}


# --------------------------------------------------------------------------- #
# Each check returns a list of failure strings. Empty means the section passed.
# --------------------------------------------------------------------------- #


def check_kernel_version() -> List[str]:
    if VECTORS["kernel"] != KERNEL_VERSION:
        return [f"vectors target kernel {VECTORS['kernel']}, implementation is {KERNEL_VERSION}"]
    return []


def check_compatibility() -> List[str]:
    out = []
    for case in VECTORS["compatibility"]:
        got = compatibility(case["data"], case["reader"])
        if got != case["expect"]:
            out.append(f"compatibility/{case['name']}: expected {case['expect']}, got {got}")
    return out


def check_prefix() -> List[str]:
    out = []
    for case in VECTORS["prefix"]:
        got = id_matches_prefix(case["id"], case["prefix"])
        if got != case["expect"]:
            out.append(f"prefix/{case['id']} vs {case['prefix']}: expected {case['expect']}, got {got}")
    return out


def check_range() -> List[str]:
    out = []
    for case in VECTORS["range"]:
        got = satisfies_range(case["version"], case["range"])
        if got != case["expect"]:
            out.append(f"range/{case['version']} in {case['range']}: expected {case['expect']}, got {got}")
    return out


def check_identifiers() -> List[str]:
    out = []
    for case in VECTORS["identifiers"]:
        fn = is_capability_id if case["type"] == "capability" else is_pod_id
        got = fn(case["value"])
        if got != case["expect"]:
            out.append(f"identifiers/{case['type']} {case['value']!r}: expected {case['expect']}, got {got}")
    return out


def check_trust() -> List[str]:
    out = []
    for case in VECTORS["trust"]:
        env = _env(case["provenance"])
        if trustworthy(env) != case["trustworthy"]:
            out.append(f"trust/{case['name']}: trustworthy expected {case['trustworthy']}")
        if badge(env) != case["badge"]:
            out.append(f"trust/{case['name']}: badge expected {case['badge']!r}, got {badge(env)!r}")
    return out


def check_validate() -> List[str]:
    out = []
    for case in VECTORS["validate"]:
        errors = validate(case["envelope"])
        is_valid = not errors
        if is_valid != case["valid"]:
            out.append(f"validate/{case['name']}: expected valid={case['valid']}, got errors={errors}")
            continue
        needle = case.get("errorContains")
        if needle and not any(needle in e for e in errors):
            out.append(f"validate/{case['name']}: expected an error containing {needle!r}, got {errors}")
    return out


def check_roundtrip() -> List[str]:
    """serialize(parse(x)) == x, exactly, for anything a newer producer sends."""
    out = []
    for case in VECTORS["roundtrip"]:
        res = parse(case["input"])
        if not res.ok:
            out.append(f"roundtrip/{case['name']}: parse failed: {res.errors}")
            continue
        env = res.envelope
        for key in case.get("expectExt", []):
            if key not in (env.get("ext") or {}):
                out.append(f"roundtrip/{case['name']}: expected ext to hold {key!r}, got {list((env.get('ext') or {}))}")
        for key in case.get("expectProvExt", []):
            if key not in (env["provenance"].get("ext") or {}):
                out.append(f"roundtrip/{case['name']}: expected provenance.ext to hold {key!r}")
        again = serialize(env)
        if canonical(again) != canonical(case["input"]):
            out.append(
                f"roundtrip/{case['name']}: not lossless\n     in: {canonical(case['input'])}\n    out: {canonical(again)}"
            )
    return out


def check_derive() -> List[str]:
    out = []
    for case in VECTORS["derive"]:
        sources = [_env(p) for p in case["sources"]]
        env = derive(sources, "sas.test.derived", "sas.pod.test", {"v": 1}, dict(case["request"]))
        fid = env["provenance"]["fidelity"]
        if fid != case["expectFidelity"]:
            out.append(f"derive/{case['name']}: expected {case['expectFidelity']}, got {fid}")
        needle = case.get("expectReasonContains")
        if needle and needle not in (env["provenance"].get("reason") or ""):
            out.append(
                f"derive/{case['name']}: expected reason containing {needle!r}, "
                f"got {env['provenance'].get('reason')!r}"
            )
        if case.get("expectEmptyPayload") and env["payload"] != {}:
            out.append(f"derive/{case['name']}: expected an empty payload, got {env['payload']!r}")
        problems = validate(env)
        if problems:
            out.append(f"derive/{case['name']}: derived envelope is itself invalid: {problems}")
    return out


def check_resolve() -> List[str]:
    out = []
    for case in VECTORS["resolve"]:
        manifests = case["manifests"]
        station = Station(manifests[0], peers=manifests[1:])
        res = station.need(case["request"], case.get("range"))
        if res.status != case["expectStatus"]:
            out.append(
                f"resolve/{case['name']}: expected {case['expectStatus']}, got {res.status} "
                f"(chain={res.chain}, notes={res.notes})"
            )
        if case.get("expectPod") and (res.provider or {}).get("pod") != case["expectPod"]:
            out.append(
                f"resolve/{case['name']}: expected provider {case['expectPod']}, "
                f"got {(res.provider or {}).get('pod')}"
            )
        if case.get("expectChain") and res.chain != case["expectChain"]:
            out.append(f"resolve/{case['name']}: expected chain {case['expectChain']}, got {res.chain}")
    return out


SECTIONS = {
    "kernel version": check_kernel_version,
    "compatibility": check_compatibility,
    "prefix matching": check_prefix,
    "version ranges": check_range,
    "identifiers": check_identifiers,
    "trust + badges": check_trust,
    "validation": check_validate,
    "forward-compat round trip": check_roundtrip,
    "fidelity derivation": check_derive,
    "capability resolution": check_resolve,
}


# --------------------------------------------------------------------------- #
# pytest entry points - one test per section, so a failure names the section
# --------------------------------------------------------------------------- #


class TestConformance:
    def test_kernel_version(self):
        assert check_kernel_version() == []

    def test_compatibility(self):
        assert check_compatibility() == []

    def test_prefix(self):
        assert check_prefix() == []

    def test_range(self):
        assert check_range() == []

    def test_identifiers(self):
        assert check_identifiers() == []

    def test_trust(self):
        assert check_trust() == []

    def test_validate(self):
        assert check_validate() == []

    def test_roundtrip(self):
        assert check_roundtrip() == []

    def test_derive(self):
        assert check_derive() == []

    def test_resolve(self):
        assert check_resolve() == []


def main() -> int:
    print(f"SAS Superstation conformance — python kernel {KERNEL_VERSION}")
    print(f"vectors {VECTORS['vectorsVersion']} targeting kernel {VECTORS['kernel']}\n")
    failures: List[str] = []
    for name, fn in SECTIONS.items():
        problems = fn()
        count = len(VECTORS[_section_key(name)]) if _section_key(name) in VECTORS else 1
        mark = "PASS" if not problems else "FAIL"
        print(f"  [{mark}] {name}  ({count} cases)")
        for p in problems:
            print(f"         - {p}")
        failures.extend(problems)
    print()
    if failures:
        print(f"FAILED — {len(failures)} problem(s)")
        return 1
    total = sum(len(v) for v in VECTORS.values() if isinstance(v, list))
    print(f"OK — {total} vector cases pass against the python kernel")
    return 0


_KEYS = {
    "compatibility": "compatibility", "prefix matching": "prefix", "version ranges": "range",
    "identifiers": "identifiers", "trust + badges": "trust", "validation": "validate",
    "forward-compat round trip": "roundtrip", "fidelity derivation": "derive",
    "capability resolution": "resolve",
}


def _section_key(name: str) -> str:
    return _KEYS.get(name, name)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""station_doctor — validate pod manifests and audit the fleet's wiring.

    python3 superstation/tools/station_doctor.py                 # this repo
    python3 superstation/tools/station_doctor.py ..              # a fleet checkout
    python3 superstation/tools/station_doctor.py .. --json

Given a directory it finds every ``station.pod.json`` beneath it (skipping
``node_modules`` and the like), validates each against the contract, loads them
all into one registry and reports what the fleet as a whole can and cannot
serve.

Standard library only — deliberately no ``jsonschema`` dependency. The schemas
in ``spec/`` remain the machine-readable statement of the contract for external
tools; the checks here are the same rules expressed against the kernel's own
predicates, so a manifest that passes here passes the kernel at runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from superstation.kernel.py import (  # noqa: E402
    KERNEL_VERSION,
    POD_ROLES,
    Registry,
    compatibility,
    is_capability_id,
    is_pod_id,
    parse_semver,
)

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".venv", "venv",
    "__pycache__", ".turbo", "coverage", "public",
}


def find_manifests(root: Path) -> List[Path]:
    found: List[Path] = []
    for path in sorted(root.rglob("station.pod.json")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        found.append(path)
    return found


def validate_manifest(data: Any, where: str) -> List[str]:
    """Every rule from SPEC.md §7-§8, as a list. Empty means valid."""
    out: List[str] = []
    if not isinstance(data, dict):
        return [f"{where}: manifest must be a JSON object"]

    compat = compatibility(data.get("kernel"))
    if compat == "malformed":
        out.append(f"{where}: kernel {data.get('kernel')!r} is not semver")
    elif compat == "incompatible":
        out.append(
            f"{where}: kernel {data.get('kernel')!r} is a different major to "
            f"{KERNEL_VERSION}; this pod cannot join the station"
        )

    pod = data.get("pod")
    if not isinstance(pod, dict):
        out.append(f"{where}: missing 'pod' block")
    else:
        if not is_pod_id(pod.get("id")):
            out.append(f"{where}: invalid pod.id {pod.get('id')!r}")
        if not pod.get("name"):
            out.append(f"{where}: pod.name is required")
        if pod.get("role") not in POD_ROLES:
            out.append(f"{where}: pod.role {pod.get('role')!r} not in {sorted(POD_ROLES)}")
        repo = pod.get("repo") or ""
        if repo.count("/") != 1 or repo.startswith("/") or repo.endswith("/"):
            out.append(f"{where}: pod.repo {repo!r} must be 'owner/repo'")

    provides = data.get("provides")
    if not isinstance(provides, list):
        out.append(f"{where}: 'provides' must be an array (use [] if this pod provides nothing yet)")
        provides = []

    seen_ids = set()
    for i, cap in enumerate(provides):
        tag = f"{where}: provides[{i}]"
        if not isinstance(cap, dict):
            out.append(f"{tag} must be an object")
            continue
        cap_id = cap.get("id")
        if not is_capability_id(cap_id):
            out.append(f"{tag} invalid capability id {cap_id!r}")
        elif cap_id in seen_ids:
            out.append(f"{tag} declares {cap_id} twice in the same manifest")
        else:
            seen_ids.add(cap_id)
        if not parse_semver(cap.get("version", "")):
            out.append(f"{tag} version {cap.get('version')!r} is not semver")
        if "degradesTo" in cap and not is_capability_id(cap["degradesTo"]):
            out.append(f"{tag} invalid degradesTo {cap['degradesTo']!r}")
        if cap.get("degradesTo") == cap_id:
            out.append(f"{tag} degradesTo points at itself")
        for dep in cap.get("requires", []) or []:
            if not is_capability_id(dep):
                out.append(f"{tag} invalid requires entry {dep!r}")

    for i, req in enumerate(data.get("requires", []) or []):
        tag = f"{where}: requires[{i}]"
        if not isinstance(req, dict):
            out.append(f"{tag} must be an object")
            continue
        if not is_capability_id(req.get("id")):
            out.append(f"{tag} invalid capability id {req.get('id')!r}")
        rng = req.get("range")
        if rng is not None and not _valid_range(rng):
            out.append(f"{tag} range {rng!r} must look like '1.x' or '1.2'")

    return out


def _valid_range(rng: Any) -> bool:
    if not isinstance(rng, str):
        return False
    parts = rng.split(".")
    return len(parts) == 2 and parts[0].isdigit() and (parts[1] == "x" or parts[1].isdigit())


def find_cycles(manifests: List[Dict[str, Any]]) -> List[str]:
    """degradesTo cycles across the whole fleet, not just within one manifest.

    The runtime terminates on a cycle rather than hanging, so this is a manifest
    smell rather than a crash — but a capability that can only ever fall back to
    itself is never going to resolve, and saying so here beats discovering it
    from an empty panel.
    """
    edges: Dict[str, str] = {}
    for m in manifests:
        for cap in m.get("provides", []) or []:
            if isinstance(cap, dict) and isinstance(cap.get("degradesTo"), str):
                edges.setdefault(cap["id"], cap["degradesTo"])

    problems: List[str] = []
    for start in edges:
        seen = [start]
        node = edges[start]
        while node in edges and node not in seen:
            seen.append(node)
            node = edges[node]
        if node in seen:
            problems.append("degradesTo cycle: " + " -> ".join(seen[seen.index(node):] + [node]))
    return sorted(set(problems))


def run(root: Path, as_json: bool) -> int:
    paths = find_manifests(root)
    manifests: List[Dict[str, Any]] = []
    errors: List[str] = []

    for path in paths:
        where = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        try:
            data = json.loads(path.read_text())
        except (ValueError, OSError) as err:
            errors.append(f"{where}: unreadable ({err})")
            continue
        problems = validate_manifest(data, where)
        errors.extend(problems)
        if not problems:
            manifests.append(data)

    registry = Registry()
    for m in manifests:
        try:
            registry.add(m)
        except ValueError as err:
            errors.append(str(err))

    audit = registry.audit()
    cycles = find_cycles(manifests)
    unmet = [f"{u['pod']} requires {u['requirement']['id']} — nothing provides it" for u in audit["unmet"]]
    degraded = [
        f"{d['pod']} requires {d['requirement']['id']} — served via {' -> '.join(d['resolution'].chain)}"
        for d in audit["degraded"]
    ]

    result = {
        "kernel": KERNEL_VERSION,
        "root": str(root),
        "manifests": len(paths),
        "valid": len(manifests),
        "pods": sorted(m["pod"]["id"] for m in manifests),
        "capabilities": registry.capabilities(),
        "errors": errors,
        "unmet": unmet,
        "degraded": degraded,
        "cycles": cycles,
    }

    if as_json:
        print(json.dumps(result, indent=2))
        return 1 if errors or cycles else 0

    print(f"station_doctor — kernel {KERNEL_VERSION}")
    print(f"scanned {root}\n")
    if not paths:
        print("  no station.pod.json found — nothing to check")
        return 0
    print(f"  pods         {len(manifests)}/{len(paths)} manifests valid")
    for m in manifests:
        pod = m["pod"]
        caps = len(m.get("provides", []) or [])
        print(f"               {pod['id']:<34} {pod['role']:<10} {caps} capabilit{'y' if caps == 1 else 'ies'}")
    print(f"\n  capabilities {len(registry.capabilities())} distinct")
    for cap in registry.capabilities():
        providers = ", ".join(sorted(p["pod"] for p in registry.providers(cap)))
        print(f"               {cap:<34} {providers}")

    if degraded:
        print(f"\n  degraded     {len(degraded)} requirement(s) running on a fallback")
        for d in degraded:
            print(f"               {d}")
    if unmet:
        print(f"\n  unmet        {len(unmet)} requirement(s) with no provider")
        for u in unmet:
            print(f"               {u}")
    if cycles:
        print(f"\n  cycles       {len(cycles)}")
        for c in cycles:
            print(f"               {c}")
    if errors:
        print(f"\n  errors       {len(errors)}")
        for e in errors:
            print(f"               {e}")
        print("\nFAILED")
        return 1
    if cycles:
        print("\nFAILED")
        return 1

    # Unmet requirements are the normal state of a fleet whose engine lives on
    # someone's PC. They are reported, not fatal.
    print("\nOK — every manifest is valid" + (f" ({len(unmet)} requirement(s) unmet, which is not an error)" if unmet else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate SAS Superstation pod manifests.")
    ap.add_argument("root", nargs="?", default=".", help="directory to scan (default: cwd)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    return run(Path(args.root).resolve(), args.json)


if __name__ == "__main__":
    sys.exit(main())

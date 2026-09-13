"""SAS Superstation - capability registry and resolution (Python mirror).

``SPEC.md`` §7. This is the expandability mechanism: a new capability is a new
manifest entry - no kernel change, no registry change, and no change to
consumers that do not want it. Nothing here knows what a thermal reading *is*,
only who claims to provide one and whether that claim currently holds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .contract import (
    compatibility,
    is_capability_id,
    parse_semver,
    satisfies_range,
)


class Resolution:
    """Outcome of :meth:`Registry.resolve`."""

    __slots__ = ("status", "requested", "provider", "chain", "notes")

    def __init__(
        self,
        status: str,
        requested: str,
        provider: Optional[Dict[str, Any]],
        chain: List[str],
        notes: List[str],
    ) -> None:
        #: ``exact`` | ``degraded`` | ``unresolved``
        self.status = status
        self.requested = requested
        self.provider = provider
        #: Capability ids walked, requested first. Length > 1 means fallbacks were used.
        self.chain = chain
        self.notes = notes

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Resolution(status={self.status!r}, chain={self.chain!r})"


def _version_key(reg: Dict[str, Any]):
    v = parse_semver(reg.get("version", "")) or {"major": -1, "minor": -1, "patch": -1}
    # Negated version parts so a plain ascending sort puts the best first;
    # pod id breaks ties so resolution is deterministic across runs.
    return (-v["major"], -v["minor"], -v["patch"], reg.get("pod", ""))


class Registry:
    def __init__(self) -> None:
        self._by_id: Dict[str, List[Dict[str, Any]]] = {}
        self._pods: Dict[str, Dict[str, Any]] = {}

    def register(self, pod: str, cap: Dict[str, Any]) -> None:
        cap_id = cap.get("id")
        if not is_capability_id(cap_id):
            raise ValueError(f"superstation: invalid capability id {cap_id!r} from pod {pod}")
        if not parse_semver(cap.get("version", "")):
            raise ValueError(
                f"superstation: capability {cap_id} has invalid version {cap.get('version')!r}"
            )
        entry = dict(cap)
        entry["pod"] = pod
        self._by_id.setdefault(cap_id, []).append(entry)

    def add(self, manifest: Dict[str, Any]) -> List[str]:
        """Ingest a pod manifest. Returns non-fatal warnings.

        A manifest on an incompatible kernel major is rejected outright - its
        capability semantics are not ours. A *newer minor* is accepted, which is
        what lets one repo upgrade without waiting for the other eight.
        """
        warnings: List[str] = []
        pod = (manifest.get("pod") or {}).get("id")
        compat = compatibility(manifest.get("kernel"))
        if compat in ("incompatible", "malformed"):
            raise ValueError(
                f"superstation: pod {pod} declares kernel {manifest.get('kernel')!r}, "
                "which this kernel cannot interpret"
            )
        if compat == "forward":
            warnings.append(f"pod {pod} is on a newer kernel ({manifest.get('kernel')})")
        self._pods[pod] = manifest
        for cap in manifest.get("provides") or []:
            self.register(pod, cap)
        return warnings

    def known(self, cap_id: str) -> bool:
        return cap_id in self._by_id

    def providers(self, cap_id: str) -> List[Dict[str, Any]]:
        return list(self._by_id.get(cap_id, []))

    def capabilities(self) -> List[str]:
        return sorted(self._by_id)

    def manifests(self) -> List[Dict[str, Any]]:
        return list(self._pods.values())

    def resolve(self, cap_id: str, range_: Optional[str] = None) -> Resolution:
        """Resolve a capability, walking ``degradesTo`` when the exact request fails.

        A provider counts as usable only if its own ``requires`` also resolve,
        which stops a surface binding to telemetry whose engine link is missing.
        The walk is guarded: a ``degradesTo`` cycle terminates as ``unresolved``
        rather than hanging. ``station_doctor`` reports the cycle as a manifest
        error; the runtime just refuses to spin.
        """
        chain: List[str] = []
        notes: List[str] = []
        seen: Set[str] = set()
        current: Optional[str] = cap_id

        while current and current not in seen:
            seen.add(current)
            chain.append(current)
            candidates: List[Dict[str, Any]] = []
            for cand in self._by_id.get(current, []):
                effective_range = range_ if current == cap_id else None
                if not satisfies_range(cand.get("version", ""), effective_range):
                    notes.append(
                        f"{cand['pod']} provides {current}@{cand.get('version')}, "
                        f"outside range {effective_range}"
                    )
                    continue
                missing = [
                    dep
                    for dep in cand.get("requires", []) or []
                    if not self._satisfiable(dep, set(seen))
                ]
                if missing:
                    notes.append(
                        f"{cand['pod']} provides {current} but requires unmet {', '.join(missing)}"
                    )
                    continue
                candidates.append(cand)

            if candidates:
                candidates.sort(key=_version_key)
                return Resolution(
                    "exact" if len(chain) == 1 else "degraded",
                    cap_id,
                    candidates[0],
                    chain,
                    [] if len(chain) == 1 else notes,
                )
            if current not in self._by_id:
                notes.append(f"no pod provides {current}")

            current = next(
                (
                    c["degradesTo"]
                    for c in self._by_id.get(current, [])
                    if isinstance(c.get("degradesTo"), str)
                ),
                None,
            )

        if current and current in seen:
            notes.append(f"degradesTo cycle at {current}")
        return Resolution("unresolved", cap_id, None, chain, notes)

    def _satisfiable(self, cap_id: str, guard: Set[str]) -> bool:
        if cap_id in guard:
            return False
        guard.add(cap_id)
        for cand in self._by_id.get(cap_id, []):
            if all(self._satisfiable(dep, guard) for dep in cand.get("requires", []) or []):
                return True
        return False

    def audit(self) -> Dict[str, Any]:
        """The station's readiness report: wired, running-on-fallback, missing.

        Optional requirements that fail are reported but do not count as unmet.
        """
        unmet: List[Dict[str, Any]] = []
        degraded: List[Dict[str, Any]] = []
        for manifest in self._pods.values():
            pod = manifest["pod"]["id"]
            for req in manifest.get("requires") or []:
                res = self.resolve(req["id"], req.get("range"))
                row = {"pod": pod, "requirement": req, "resolution": res}
                if res.status == "unresolved":
                    if not req.get("optional"):
                        unmet.append(row)
                elif res.status == "degraded":
                    degraded.append(row)
        return {"ok": not unmet, "unmet": unmet, "degraded": degraded}

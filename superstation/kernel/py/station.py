"""SAS Superstation - the facade a pod actually holds (Python mirror).

A pod constructs one :class:`Station`, hands it its own manifest, and from then
on publishes through it and asks it for capabilities.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from .contract import KERNEL_VERSION, id_matches_prefix
from .envelope import ParseResult, absent, derive, parse, seal, trustworthy
from .registry import Registry, Resolution

Listener = Callable[[Dict[str, Any]], None]


class Bus:
    """Prefix-matched pub/sub over envelopes. No transport assumptions."""

    def __init__(self, on_error: Optional[Callable[[BaseException, Dict], None]] = None,
                 retain: bool = True) -> None:
        self._subs: List[Dict[str, Any]] = []
        self._retained: Dict[str, Dict[str, Any]] = {}
        self._retain = retain
        self._on_error = on_error

    def on(self, prefix: str, fn: Listener) -> Callable[[], None]:
        sub = {"prefix": prefix, "fn": fn}
        self._subs.append(sub)
        if self._retain:
            for env in list(self._retained.values()):
                if id_matches_prefix(env["kind"], prefix):
                    self._deliver(sub, env)

        def off() -> None:
            self._subs = [s for s in self._subs if s is not sub]

        return off

    def emit(self, env: Dict[str, Any]) -> int:
        if self._retain:
            self._retained[env["kind"]] = env
        # Snapshot: subscribing or unsubscribing mid-delivery must not change
        # who receives this envelope.
        targets = [s for s in self._subs if id_matches_prefix(env["kind"], s["prefix"])]
        for sub in targets:
            self._deliver(sub, env)
        return len(targets)

    def latest(self, kind: str) -> Optional[Dict[str, Any]]:
        return self._retained.get(kind)

    def snapshot(self) -> List[Dict[str, Any]]:
        return sorted(self._retained.values(), key=lambda e: e["kind"])

    def clear(self) -> None:
        self._subs = []
        self._retained.clear()

    def _deliver(self, sub: Dict[str, Any], env: Dict[str, Any]) -> None:
        try:
            sub["fn"](env)
        except BaseException as err:  # noqa: BLE001 - one bad panel must not stop the rest
            if self._on_error:
                self._on_error(err, env)
            else:
                print(f"superstation: subscriber threw on {env.get('kind')}: {err!r}")


class Station:
    def __init__(
        self,
        manifest: Dict[str, Any],
        peers: Optional[Sequence[Dict[str, Any]]] = None,
        on_error: Optional[Callable[[BaseException, Dict], None]] = None,
        retain: bool = True,
    ) -> None:
        self.manifest = manifest
        self.registry = Registry()
        self.bus = Bus(on_error=on_error, retain=retain)
        self.warnings: List[str] = list(self.registry.add(manifest))
        for peer in peers or []:
            try:
                self.warnings.extend(self.registry.add(peer))
            except ValueError as err:
                # A peer on an incompatible major is a fact about the fleet, not
                # a crash: this pod keeps running with one fewer peer.
                self.warnings.append(str(err))

    @property
    def pod_id(self) -> str:
        return self.manifest["pod"]["id"]

    def join(self, peer: Dict[str, Any]) -> List[str]:
        w = self.registry.add(peer)
        self.warnings.extend(w)
        return w

    def publish(self, kind: str, payload: Any, provenance: Dict[str, Any],
                ts: Optional[str] = None) -> Dict[str, Any]:
        env = seal(kind, self.pod_id, payload, provenance, ts)
        self.bus.emit(env)
        return env

    def publish_derived(self, sources: Sequence[Dict[str, Any]], kind: str, payload: Any,
                        provenance: Dict[str, Any]) -> Dict[str, Any]:
        env = derive(sources, kind, self.pod_id, payload, provenance)
        self.bus.emit(env)
        return env

    def publish_absent(self, kind: str, source: str, reason: str) -> Dict[str, Any]:
        """Publish the fact that a capability has no data.

        The station's answer to a dead engine link. An ``absent`` envelope is a
        real envelope: panels get told "nothing, because X" instead of waiting
        forever on a tick that is never coming.
        """
        return self.publish(kind, {}, absent(source, reason))

    def ingest(self, raw: Any) -> ParseResult:
        res = parse(raw)
        if res.ok and res.envelope is not None:
            self.bus.emit(res.envelope)
        return res

    def on(self, prefix: str, fn: Listener) -> Callable[[], None]:
        return self.bus.on(prefix, fn)

    def need(self, cap_id: str, range_: Optional[str] = None) -> Resolution:
        return self.registry.resolve(cap_id, range_)

    def is_live(self, kind: str) -> bool:
        env = self.bus.latest(kind)
        return env is not None and trustworthy(env)

    def report(self) -> Dict[str, Any]:
        """The honest answer to "is any of this real right now?"."""
        audit = self.registry.audit()
        trusted: List[str] = []
        untrusted: List[Dict[str, Any]] = []
        for env in self.bus.snapshot():
            if trustworthy(env):
                trusted.append(env["kind"])
            else:
                row = {"kind": env["kind"], "fidelity": env["provenance"]["fidelity"]}
                if env["provenance"].get("reason"):
                    row["reason"] = env["provenance"]["reason"]
                untrusted.append(row)
        return {
            "kernel": KERNEL_VERSION,
            "pod": self.pod_id,
            "capabilities": self.registry.capabilities(),
            "unmet": [f"{u['pod']} needs {u['requirement']['id']}" for u in audit["unmet"]],
            "degraded": [
                f"{d['pod']} needs {d['requirement']['id']}, "
                f"served by {' -> '.join(d['resolution'].chain)}"
                for d in audit["degraded"]
            ],
            "trusted": trusted,
            "untrusted": untrusted,
            "warnings": self.warnings,
        }

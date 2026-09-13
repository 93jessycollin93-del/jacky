# SAS Superstation — Kernel Contract v1.0.0

> `pqbd_[}-_0_-SAS/\/Jacky's\/\eYe\/\Pod/\/HUB-_0_-{]_qpdb`

The station is not an app. It is the **contract** that lets a fleet of unrelated
apps — a Flask engine, five Lovable/Vite React apps, a TanStack app, and PC's
90-window desktop — behave as one system without any of them depending on each
other.

This document is normative. `kernel/ts` and `kernel/py` are reference
implementations of it; `conformance/` is the proof they agree.

---

## 0. Why a contract and not a library

The fleet already tried the library answer. `jackyClient.ts` and `eye-theme.css`
were copied byte-identical into four repos, and the parity matrix verified them
"by checksum, not by inspection." That works exactly until someone edits one
copy. There is no version, no compatibility rule, and no way for a consumer to
ask *what does this pod actually speak?* — only "is the file the same as mine."

A contract inverts that. Pods declare what they provide and require; the kernel
resolves. Adding a capability never edits the kernel. Two pods on different
kernel versions still interoperate because the compatibility rules below are
written down and tested, rather than being an emergent property of a diff.

## 1. Design tenets

1. **Chaos is the normal case.** The engine is on someone's PC behind a
   Cloudflare quick tunnel. It is *usually* unreachable. Every structure here
   assumes absence, staleness and partial data as ordinary states — not errors.
2. **Honesty is structural, not cultural.** The existing client's honesty rule
   ("a demo that admits it beats a dashboard that lies") is promoted from a
   comment into a required field. You cannot emit a reading without saying how
   real it is.
3. **Additive-only evolution.** v1 readers must survive v1.9 data. Unknown
   fields are preserved, never dropped.
4. **Capability negotiation, not version sniffing.** Ask for what you need; do
   not branch on who you are talking to.
5. **Zero dependencies.** The nine repos share no dependency in common. The
   kernel imports nothing.

---

## 2. Identifiers

A **capability ID** is a dotted, lowercase, reverse-scoped string:

```
sas.telemetry.thermal
sas.route.ask
sas.vault.secret
```

Grammar: `^[a-z][a-z0-9]*(\.[a-z][a-z0-9-]*){1,5}$`. The first segment is the
namespace (`sas` is reserved for this station; anything else is free for
third-party pods). Prefix matching is meaningful: `sas.telemetry` is a valid
subscription that receives `sas.telemetry.thermal`.

A **pod ID** is `^[a-z][a-z0-9-]*(\.[a-z0-9-]+){1,3}$`, conventionally
`sas.pod.<name>`.

## 3. The Envelope

Every piece of data that crosses a pod boundary is wrapped. This is the single
most important structure in the station.

```jsonc
{
  "kernel":  "1.0.0",              // contract version that produced this
  "kind":    "sas.telemetry.thermal", // capability ID
  "id":      "01J8X...",           // unique per envelope
  "ts":      "2026-09-06T22:31:00.000Z", // when this envelope was emitted
  "pod":     "sas.pod.jacky",      // who emitted it
  "provenance": { /* §4 */ },
  "payload": { /* capability-defined */ },
  "ext":     { /* §6 forward-compat sidecar */ }
}
```

`kernel`, `kind`, `id`, `ts`, `pod`, `provenance` and `payload` are REQUIRED.
`ext` is OPTIONAL and MUST be omitted when empty.

`ts` MUST be RFC 3339 / ISO 8601 with a `Z` suffix and millisecond precision.

## 4. Provenance and the fidelity ladder

```jsonc
"provenance": {
  "fidelity":   "live",                  // REQUIRED, see ladder
  "source":     "jacky:/api/metrics",    // REQUIRED, free-form but stable
  "observedAt": "2026-09-06T22:30:58.000Z", // when the reading was TAKEN
  "staleMs":    2000,
  "reason":     "engine unreachable; last good reading 4m old"
}
```

The **fidelity ladder** is totally ordered. Consumers compare rather than
string-match:

| rank | fidelity    | meaning                                                        |
|-----:|-------------|----------------------------------------------------------------|
| 4    | `live`      | measured now, from the real source                              |
| 3    | `cached`    | really measured, but earlier; `staleMs` says how much earlier   |
| 2    | `degraded`  | real but partial/lossy — a subset of fields, a coarser sample   |
| 1    | `simulated` | invented for display. Never to be shown without a label         |
| 0    | `absent`    | no data at all; `payload` MUST be `{}`                          |

Normative rules, all conformance-tested:

- `live` MUST carry `observedAt`.
- `cached` MUST carry `observedAt` **and** `staleMs`.
- `degraded`, `simulated` and `absent` MUST carry `reason`.
- `absent` MUST have an empty `payload`.
- A pod MUST NOT emit `live` or `cached` for a value it did not obtain from the
  named `source`. This is the honesty rule, and it is the one rule the kernel
  cannot enforce for you — everything else in this section it checks.

**Trust predicate.** `trustworthy(env) === rank(fidelity) >= 3`. UI that renders
an untrustworthy envelope MUST mark it visibly. The kernel exposes this as one
function so no surface has to re-derive the threshold.

**Degradation is monotonic.** When a value passes through pods, fidelity may
only fall. `Envelope.derive()` enforces this: deriving `live` from a `cached`
input yields `cached`. Chains cannot launder simulated data into live data.

## 5. Version compatibility

`kernel` is semver. Given a reader at `R` and an envelope at `E`:

- **`E.major !== R.major`** → INCOMPATIBLE. Reader MUST reject.
- **`E.major === R.major`, `E.minor > R.minor`** → FORWARD. Reader MUST accept
  and MUST preserve unknown fields (§6). This is the case that keeps the fleet
  from needing a lockstep upgrade.
- **`E.minor <= R.minor`** → COMPATIBLE.

Patch is never load-bearing. Nothing may branch on it.

A minor bump MAY add optional fields and new capability IDs. It MUST NOT add a
required field, remove a field, narrow a type, or change fidelity semantics.
Any of those is a major bump.

## 6. Forward-compatibility: the `ext` sidecar

When a v1.0 reader parses an envelope containing top-level keys it does not
know, it MUST move them into `ext` rather than discarding them, and MUST write
them back out at top level when re-serializing. A round trip through an old
reader is therefore lossless.

```
v1.4 producer  ──▶  {..., "trace": {...}}
v1.0 reader    ──▶  {..., ext: { trace: {...} }}       // understood: nothing
v1.0 re-emit   ──▶  {..., "trace": {...}}              // preserved exactly
```

The same rule applies inside `provenance`. It deliberately does **not** apply to
`payload`, which is opaque to the kernel and preserved wholesale anyway.

## 7. Capabilities

A pod declares capabilities rather than endpoints:

```jsonc
{
  "id":        "sas.telemetry.thermal",
  "version":   "1.0.0",        // semver of the PAYLOAD contract, independent of kernel
  "title":     "GPU/CPU thermals",
  "degradesTo": "sas.telemetry.coarse",   // optional fallback capability
  "requires":  ["sas.link.engine"]        // optional capability dependencies
}
```

Resolution: `registry.resolve(id)` returns the highest-`version` provider whose
`requires` are themselves resolvable. If none is, it follows `degradesTo` and
tries again, returning the fallback plus the chain that was walked. A cycle in
`degradesTo` is a manifest error, detected by `station_doctor`, and at runtime
terminates the walk rather than hanging.

This is the expandability mechanism: a new capability is a new manifest entry.
No kernel change, no registry change, no consumer change for consumers that do
not want it.

## 8. Pod manifest

Each repo in the fleet carries exactly one `station.pod.json` at its root,
validated by `spec/pod.manifest.schema.json`:

```jsonc
{
  "kernel": "1.0.0",
  "pod": {
    "id":   "sas.pod.jacky",
    "name": "Jacky Engine",
    "role": "engine",
    "repo": "93jessycollin93-del/jacky"
  },
  "provides": [ /* CapabilityDescriptor[] */ ],
  "requires": [ /* { id, range } */ ],
  "surfaces": [ { "kind": "http", "base": "/api", "note": "Flask" } ]
}
```

Roles are a closed set: `engine`, `surface`, `vault`, `bot`, `knowledge`.
They map onto the tags already in `repos.json` (`core`→engine,
`condenser`→knowledge, `bot`→bot, `knowledge-source`→knowledge), so the existing
fleet registry can be migrated rather than replaced.

## 9. What this contract deliberately does not do

- **No transport.** The station says nothing about HTTP, WebSocket or postMessage.
  `jackyClient.ts` remains the transport for the engine link; it produces
  envelopes, it is not replaced by them.
- **No auth.** The `/api/control` gating gap recorded in `PARITY_MATRIX.md` is a
  real, open problem and is not fixed by wrapping it in an envelope. The manifest
  can *declare* that a capability is privileged; enforcing it stays with each
  platform's auth layer.
- **No UI.** `fleet-ui` and `eye-theme.css` stay where they are.

Keeping these out is what makes the contract adoptable by nine repos that share
no stack.

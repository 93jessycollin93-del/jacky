# SAS Superstation — the fleet's foundation

```
pqbd_[}-_0_-SAS/\/Jacky's\/\eYe\/\Pod/\/HUB-_0_-{]_qpdb
```

Nine repositories, four stacks, no shared dependency. This is the layer that
lets them behave as one station without depending on each other.

It is a **contract with two reference implementations**, not a library. Read
[`SPEC.md`](SPEC.md) for the normative version; this file is the orientation.

---

## The problem it solves

The fleet's previous answer to sharing code was to copy `jackyClient.ts` and
`eye-theme.css` byte-identically into four repos and verify them "by checksum,
not by inspection" — with the checksums recorded in a prose document that
nothing ever executed. There was no version, no compatibility rule, and no way
for one pod to ask another *what do you actually speak?*

Separately, every dashboard in the fleet invented its own telemetry. PC's
monitors drifted random numbers; the others proxied straight to cloud LLMs. The
engine that actually knows the GPU temperature was never wired up, and nothing
in the data said which numbers were real.

Both of those are the same failure: **no structure that survives the absence of
the thing it describes.** The engine lives on someone's PC behind a quick
tunnel. It is usually unreachable. A foundation for this fleet has to treat that
as the normal case.

## What it gives you

| | |
|---|---|
| **Envelope** | Every value crossing a pod boundary is wrapped with a provenance block. You cannot emit a reading without saying how real it is. |
| **Fidelity ladder** | `live > cached > degraded > simulated > absent`, totally ordered. `trustworthy()` is one function, so no panel picks a friendlier threshold. |
| **Monotonic degradation** | `derive()` carries the weakest input fidelity into the output. A chain of pods cannot launder a simulated number into a live one. |
| **Forward compatibility** | A v1.0 reader parsing v1.7 data preserves the fields it does not understand and writes them back out unchanged. One repo can upgrade without the other eight. |
| **Capability registry** | Pods declare what they provide and require. Adding a capability is a manifest entry — no kernel change, no registry change, no consumer change. |
| **Graceful fallback** | `degradesTo` chains resolve automatically when a capability's dependencies are missing, so a surface renders something honest instead of nothing. |

## Layout

```
superstation/
  SPEC.md                 normative contract — read this one
  VERSION                 1.0.0
  spec/*.schema.json      machine-readable: envelope, capability, pod manifest
  kernel/ts/              TypeScript reference impl — zero dependencies
  kernel/py/              Python reference impl — standard library only
  conformance/            71 shared vectors, executed by BOTH kernels
  tools/station_doctor.py validate manifests, audit fleet wiring
  tools/station_sync.py   vendor the kernel into a repo, detect drift
```

## Run it

```bash
python3 superstation/conformance/test_conformance.py   # python kernel — 71 cases
node    superstation/conformance/conformance.mjs       # typescript kernel — same 71
python3 superstation/tools/station_doctor.py .         # validate this repo's manifest
python3 superstation/tools/station_doctor.py ..        # audit a whole fleet checkout
```

Neither runner needs an install step. Node ≥ 22.18 strips the types on import,
which is why the kernel's internal imports carry explicit `.ts` extensions —
every repo in the fleet already sets `allowImportingTsExtensions`, and Deno and
esbuild want them anyway.

The two kernels sharing one vector file is the point. A behaviour that only one
of them satisfies fails the suite instead of drifting quietly.

## Use it

```ts
import { Station, live, simulated } from './superstation/index.ts';
import manifest from '../station.pod.json';

const station = new Station({ manifest });

// A real reading from the engine.
station.publish('sas.telemetry.system', { gpuC: 61 }, live('jacky:/api/metrics'));

// The engine is down. Say so — do not invent a number and hope.
station.publishAbsent('sas.telemetry.system', 'jacky:/api/metrics', 'connection refused');

// A demo that admits it.
station.publish('sas.telemetry.system', { gpuC: 55 },
  simulated('synthetic', 'no engine configured — display only'));

station.on('sas.telemetry', (env) => {
  render(env.payload, { label: badge(env) });  // null when trustworthy
});
```

```python
from superstation.kernel.py import Station, live

station = Station(json.load(open("station.pod.json")))
station.publish("sas.telemetry.system", {"gpuC": 61}, live("jacky:/api/metrics"))
```

## Adopt it in another repo

1. `python3 superstation/tools/station_sync.py --to ../<repo>` — vendors the
   TypeScript kernel into `<repo>/src/superstation/` with a `station.lock.json`.
2. Add a `station.pod.json` at the repo root declaring what that pod provides
   and requires.
3. `python3 superstation/tools/station_doctor.py ..` to check the wiring.
4. `station_sync.py --check-all ..` in CI, so an edited copy is a failing check
   rather than a surprise six months later.

Vendoring rather than publishing a package is a deliberate concession: the nine
repos share no registry or build system, and three are edited by a hosted
builder that will not run `npm install` for us. A committed copy is the only
distribution mechanism all of them support. The lockfile is what makes it
survivable.

## What it deliberately leaves alone

No transport, no auth, no UI. `jackyClient.ts` stays the wire to the engine;
`fleet-ui` stays the look. The `/api/control` gating gap recorded in
`PARITY_MATRIX.md` is a real open problem and wrapping it in an envelope does
not fix it — a manifest can *declare* a capability `privileged`, but enforcement
belongs to each platform's auth layer.

Keeping those out is what makes this adoptable by nine repos that agree on
nothing else.

/**
 * Conformance suite for the TypeScript kernel.
 *
 * Runs `vectors/kernel.vectors.json` — the same file `test_conformance.py` runs
 * against the Python kernel. Two implementations, one set of expectations: a
 * behaviour that only one of them satisfies fails here rather than drifting
 * quietly, which is what happened the last time this fleet shared code by
 * copying files and hoping.
 *
 *     node superstation/conformance/conformance.mjs
 *
 * No build step and no dependencies: Node ≥ 22.18 strips the types on import,
 * which is why the kernel's own imports carry explicit `.ts` extensions.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

const {
  KERNEL_VERSION, Station, badge, compatibility, derive, idMatchesPrefix,
  isCapabilityId, isPodId, parse, satisfiesRange, serialize, trustworthy, validate,
} = await import(join(here, '..', 'kernel', 'ts', 'index.ts'));

const V = JSON.parse(readFileSync(join(here, 'vectors', 'kernel.vectors.json'), 'utf8'));

/** Order-independent JSON, so key order is never mistaken for a difference. */
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value) ?? 'null';
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
}

const env = (provenance, payload) => ({ provenance, payload: payload ?? {} });

const checks = {
  'kernel version': () =>
    V.kernel === KERNEL_VERSION
      ? []
      : [`vectors target kernel ${V.kernel}, implementation is ${KERNEL_VERSION}`],

  compatibility: () => V.compatibility.flatMap((c) => {
    const got = compatibility(c.data, c.reader);
    return got === c.expect ? [] : [`compatibility/${c.name}: expected ${c.expect}, got ${got}`];
  }),

  prefix: () => V.prefix.flatMap((c) => {
    const got = idMatchesPrefix(c.id, c.prefix);
    return got === c.expect ? [] : [`prefix/${c.id} vs ${c.prefix}: expected ${c.expect}, got ${got}`];
  }),

  range: () => V.range.flatMap((c) => {
    const got = satisfiesRange(c.version, c.range ?? undefined);
    return got === c.expect ? [] : [`range/${c.version} in ${c.range}: expected ${c.expect}, got ${got}`];
  }),

  identifiers: () => V.identifiers.flatMap((c) => {
    const got = c.type === 'capability' ? isCapabilityId(c.value) : isPodId(c.value);
    return got === c.expect ? [] : [`identifiers/${c.type} "${c.value}": expected ${c.expect}, got ${got}`];
  }),

  trust: () => V.trust.flatMap((c) => {
    const e = env(c.provenance);
    const out = [];
    if (trustworthy(e) !== c.trustworthy) out.push(`trust/${c.name}: trustworthy expected ${c.trustworthy}`);
    if (badge(e) !== c.badge) out.push(`trust/${c.name}: badge expected ${JSON.stringify(c.badge)}, got ${JSON.stringify(badge(e))}`);
    return out;
  }),

  validate: () => V.validate.flatMap((c) => {
    const errors = validate(c.envelope);
    const isValid = errors.length === 0;
    if (isValid !== c.valid) {
      return [`validate/${c.name}: expected valid=${c.valid}, got errors=${JSON.stringify(errors)}`];
    }
    if (c.errorContains && !errors.some((e) => e.includes(c.errorContains))) {
      return [`validate/${c.name}: expected an error containing "${c.errorContains}", got ${JSON.stringify(errors)}`];
    }
    return [];
  }),

  /** serialize(parse(x)) === x, exactly, for anything a newer producer sends. */
  roundtrip: () => V.roundtrip.flatMap((c) => {
    const res = parse(c.input);
    if (!res.ok) return [`roundtrip/${c.name}: parse failed: ${JSON.stringify(res.errors)}`];
    const out = [];
    for (const key of c.expectExt ?? []) {
      if (!(key in (res.envelope.ext ?? {}))) {
        out.push(`roundtrip/${c.name}: expected ext to hold "${key}", got ${JSON.stringify(Object.keys(res.envelope.ext ?? {}))}`);
      }
    }
    for (const key of c.expectProvExt ?? []) {
      if (!(key in (res.envelope.provenance.ext ?? {}))) {
        out.push(`roundtrip/${c.name}: expected provenance.ext to hold "${key}"`);
      }
    }
    const again = serialize(res.envelope);
    if (canonical(again) !== canonical(c.input)) {
      out.push(`roundtrip/${c.name}: not lossless\n      in: ${canonical(c.input)}\n     out: ${canonical(again)}`);
    }
    return out;
  }),

  derive: () => V.derive.flatMap((c) => {
    const sources = c.sources.map((p) => env(p));
    const e = derive(sources, {
      kind: 'sas.test.derived', pod: 'sas.pod.test', payload: { v: 1 }, provenance: { ...c.request },
    });
    const out = [];
    if (e.provenance.fidelity !== c.expectFidelity) {
      out.push(`derive/${c.name}: expected ${c.expectFidelity}, got ${e.provenance.fidelity}`);
    }
    if (c.expectReasonContains && !(e.provenance.reason ?? '').includes(c.expectReasonContains)) {
      out.push(`derive/${c.name}: expected reason containing "${c.expectReasonContains}", got ${JSON.stringify(e.provenance.reason)}`);
    }
    if (c.expectEmptyPayload && canonical(e.payload) !== '{}') {
      out.push(`derive/${c.name}: expected an empty payload, got ${canonical(e.payload)}`);
    }
    const problems = validate(e);
    if (problems.length) out.push(`derive/${c.name}: derived envelope is itself invalid: ${JSON.stringify(problems)}`);
    return out;
  }),

  resolve: () => V.resolve.flatMap((c) => {
    const [manifest, ...peers] = c.manifests;
    const station = new Station({ manifest, peers });
    const res = station.need(c.request, c.range);
    const out = [];
    if (res.status !== c.expectStatus) {
      out.push(`resolve/${c.name}: expected ${c.expectStatus}, got ${res.status} (chain=${JSON.stringify(res.chain)}, notes=${JSON.stringify(res.notes)})`);
    }
    if (c.expectPod && res.provider?.pod !== c.expectPod) {
      out.push(`resolve/${c.name}: expected provider ${c.expectPod}, got ${res.provider?.pod}`);
    }
    if (c.expectChain && canonical(res.chain) !== canonical(c.expectChain)) {
      out.push(`resolve/${c.name}: expected chain ${JSON.stringify(c.expectChain)}, got ${JSON.stringify(res.chain)}`);
    }
    return out;
  }),
};

const LABELS = {
  'kernel version': 'kernel version', compatibility: 'compatibility', prefix: 'prefix matching',
  range: 'version ranges', identifiers: 'identifiers', trust: 'trust + badges',
  validate: 'validation', roundtrip: 'forward-compat round trip', derive: 'fidelity derivation',
  resolve: 'capability resolution',
};

console.log(`SAS Superstation conformance — typescript kernel ${KERNEL_VERSION}`);
console.log(`vectors ${V.vectorsVersion} targeting kernel ${V.kernel}\n`);

let failures = 0;
for (const [key, fn] of Object.entries(checks)) {
  const problems = fn();
  const count = Array.isArray(V[key]) ? V[key].length : 1;
  console.log(`  [${problems.length ? 'FAIL' : 'PASS'}] ${LABELS[key]}  (${count} cases)`);
  for (const p of problems) console.log(`         - ${p}`);
  failures += problems.length;
}

console.log();
if (failures) {
  console.log(`FAILED — ${failures} problem(s)`);
  process.exit(1);
}
const total = Object.values(V).filter(Array.isArray).reduce((n, a) => n + a.length, 0);
console.log(`OK — ${total} vector cases pass against the typescript kernel`);

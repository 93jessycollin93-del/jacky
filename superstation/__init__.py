"""SAS Superstation — the fleet's shared foundation.

Layout:
  SPEC.md          normative contract
  spec/            JSON Schemas for envelope, capability, pod manifest
  kernel/ts/       TypeScript reference implementation (zero dependencies)
  kernel/py/       Python reference implementation (standard library only)
  conformance/     shared vectors both kernels must pass
  tools/           station_doctor (manifest validation), station_sync (vendoring)

Importable from the repo root as::

    from superstation.kernel.py import Station, live
"""

#!/usr/bin/env python3
"""
SITUATION ASSESSOR - the engine's "are we safe to run this locally?" brain.

Combines CPU, GPU (temp / load / VRAM), and RAM into a single, cheap-to-read
verdict that /api/ask and the ensemble use to decide WHERE a task runs:

    safe_for_local      -> run the local Ollama ensemble (free, preferred)
    safe_for_light_cloud-> GPU getting warm; small local model OR free cloud
    escalate_to_free    -> too hot / loaded for local; use the free cloud tier
    escalate_to_heavy   -> local unavailable AND escalation warranted

Frame: It's Jacky's PC. Local-first and free, but never cook the GPU. When the
RTX 3090 is hot or slammed, step aside and let the free cloud tier carry it.

Thermal logic (mirrors the prompt spec):
    gpu_temp >= max                -> escalate_to_free
    gpu_temp >= max - margin       -> safe_for_light_cloud
    gpu_load >= load_high          -> safe_for_light_cloud (prefer small/cloud)
    gpu_mem_free < task_needs_mb   -> escalate_to_free
    else                           -> safe_for_local

Note: the 980 Pro NVMe is a *separate* component that throttles under heavy
sustained I/O. We don't read its temperature here — that throttle is handled by
loading models sequentially (see ollama_ensemble.query_ensemble). This module
is purely about CPU/GPU/RAM compute pressure.
"""

import json
import logging
from pathlib import Path
from typing import Optional

try:
    import psutil
except Exception:  # pragma: no cover - psutil should be present
    psutil = None

from resource_policy import ResourcePolicy

log = logging.getLogger("SituationAssessor")

JACKY_HOME = Path(__file__).parent

# Assessment levels, ordered from most to least local-friendly.
SAFE_FOR_LOCAL = "safe_for_local"
SAFE_FOR_LIGHT_CLOUD = "safe_for_light_cloud"
ESCALATE_TO_FREE = "escalate_to_free"
ESCALATE_TO_HEAVY = "escalate_to_heavy"

# Rough VRAM a task "needs" if the caller doesn't say. Conservative so we don't
# kick off a big load that OOMs the card.
DEFAULT_TASK_VRAM_MB = 2000


def _load_assessment_cfg() -> dict:
    try:
        with open(JACKY_HOME / "config.json") as f:
            return json.load(f).get("situation_assessment", {})
    except Exception:
        return {}


class SituationAssessor:
    """Read the machine's live state and return a routing-grade verdict."""

    def __init__(self, policy: Optional[ResourcePolicy] = None):
        self.policy = policy or ResourcePolicy()
        cfg = _load_assessment_cfg()
        self.monitor_interval = cfg.get("monitor_interval_sec", 5)
        # Pressure thresholds (sane defaults; tunable via config later).
        self.cpu_high = cfg.get("cpu_high_percent", 90)
        self.ram_high = cfg.get("ram_high_percent", 90)

    # ------------------------------------------------------------------ #
    def _cpu_percent(self) -> Optional[float]:
        if not psutil:
            return None
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return None

    def _ram_percent(self) -> Optional[float]:
        if not psutil:
            return None
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    def assess(self, task_needs_mb: int = DEFAULT_TASK_VRAM_MB) -> dict:
        """Return a full situation report + a single routing verdict.

        Shape:
        {
          "level": "safe_for_local" | ...,
          "safe_to_run_local": bool,
          "reason": "human-readable why",
          "cpu_percent", "ram_percent",
          "gpu_available", "gpu_temp_c", "gpu_load_percent",
          "gpu_mem_free_mb", "thermal_headroom_c",
          "gpu_max_temp_c", "thermal_margin",
        }
        """
        p = self.policy
        snap = p.gpu_snapshot()
        cpu = self._cpu_percent()
        ram = self._ram_percent()

        report = {
            "cpu_percent": cpu,
            "ram_percent": ram,
            "gpu_available": snap is not None,
            "gpu_max_temp_c": p.gpu_max_temp,
            "thermal_margin": p.thermal_margin,
        }

        # --- No GPU telemetry: lean on CPU/RAM only, stay local if calm. ---
        if snap is None:
            report["gpu_temp_c"] = None
            report["gpu_load_percent"] = None
            report["gpu_mem_free_mb"] = None
            report["thermal_headroom_c"] = None
            if (ram is not None and ram >= self.ram_high) or \
               (cpu is not None and cpu >= self.cpu_high):
                report.update(level=ESCALATE_TO_FREE, safe_to_run_local=False,
                              reason="No GPU telemetry; CPU/RAM under heavy load.")
            else:
                report.update(level=SAFE_FOR_LOCAL, safe_to_run_local=True,
                              reason="No GPU telemetry; CPU/RAM calm — running local.")
            return report

        temp = snap["temp_c"]
        load = snap["util_percent"]
        mem_free = snap["mem_total_mb"] - snap["mem_used_mb"]
        headroom = p.gpu_max_temp - temp
        report.update({
            "gpu_temp_c": temp,
            "gpu_load_percent": load,
            "gpu_mem_free_mb": mem_free,
            "thermal_headroom_c": round(headroom, 1),
        })

        # --- Thermal + capacity gating, in priority order. ---
        if temp >= p.gpu_max_temp:
            report.update(level=ESCALATE_TO_FREE, safe_to_run_local=False,
                          reason=f"GPU {temp:.0f}°C >= max {p.gpu_max_temp}°C — too hot for local.")
        elif mem_free < task_needs_mb:
            report.update(level=ESCALATE_TO_FREE, safe_to_run_local=False,
                          reason=f"GPU VRAM low ({mem_free:.0f}MB free < {task_needs_mb}MB needed).")
        elif ram is not None and ram >= self.ram_high:
            report.update(level=ESCALATE_TO_FREE, safe_to_run_local=False,
                          reason=f"System RAM under pressure ({ram:.0f}%).")
        elif headroom <= p.thermal_margin:
            report.update(level=SAFE_FOR_LIGHT_CLOUD, safe_to_run_local=True,
                          reason=f"GPU warm ({temp:.0f}°C, {headroom:.0f}°C headroom) — "
                                 "prefer small local model or free cloud.")
        elif load >= p.gpu_load_high:
            report.update(level=SAFE_FOR_LIGHT_CLOUD, safe_to_run_local=True,
                          reason=f"GPU busy ({load:.0f}% load) — prefer small local model or free cloud.")
        else:
            report.update(level=SAFE_FOR_LOCAL, safe_to_run_local=True,
                          reason=f"GPU healthy ({temp:.0f}°C, {load:.0f}% load) — running local.")
        return report

    # ------------------------------------------------------------------ #
    def short_status(self) -> str:
        """One-word badge for the dashboard: 'Safe' / 'Warm' / 'Escalate'."""
        level = self.assess()["level"]
        return {
            SAFE_FOR_LOCAL: "Safe",
            SAFE_FOR_LIGHT_CLOUD: "Warm",
            ESCALATE_TO_FREE: "Escalate",
            ESCALATE_TO_HEAVY: "Escalate",
        }.get(level, "Unknown")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    a = SituationAssessor()
    print(json.dumps(a.assess(), indent=2))
    print("Badge:", a.short_status())

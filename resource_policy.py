#!/usr/bin/env python3
"""
RESOURCE POLICY - enforce the CPU budget for AI workloads.

Policy (from config.json resource_limits):
  - AI caps at 75% CPU (project baseline).
  - May burst to 90% when needed OR when the user is idle.

This module turns that policy into a concrete Ollama thread count, and
detects user idleness on Windows via GetLastInputInfo. Local-first; no deps.

Frame: It's Jacky's PC. The project gets 75%; AI borrows the rest when you're away.
"""

import os
import json
import ctypes
import logging
import shutil
import subprocess
from ctypes import wintypes
from pathlib import Path
from typing import Optional

log = logging.getLogger("ResourcePolicy")

JACKY_HOME = Path(__file__).parent
IDLE_THRESHOLD_S = 120  # user considered idle after 2 min of no input

# GPU thermal defaults (overridable via config.json -> gpu_thermal).
# The RTX 3090 is the compute device we gate on. Note: the 980 Pro NVMe is a
# *separate* component that throttles under heavy I/O — handled by pacing model
# loads sequentially (see ollama_ensemble.query_ensemble), not by these temps.
DEFAULT_GPU_MAX_TEMP_C = 75
DEFAULT_THERMAL_MARGIN = 5
DEFAULT_GPU_LOAD_HIGH = 85  # % utilization considered "loaded"


def _idle_seconds() -> float:
    """Seconds since last keyboard/mouse input (Windows). 0 on failure."""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0
    except Exception as e:
        log.debug(f"idle detect failed: {e}")
    return 0.0


def user_is_idle(threshold_s: int = IDLE_THRESHOLD_S) -> bool:
    return _idle_seconds() >= threshold_s


def _load_config() -> dict:
    try:
        with open(JACKY_HOME / "config.json") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_limits() -> dict:
    return _load_config().get("resource_limits", {})


# ---------------------------------------------------------------------------- #
# GPU monitoring (nvidia-smi, stdlib subprocess; no third-party deps)
# ---------------------------------------------------------------------------- #
_NVIDIA_SMI = shutil.which("nvidia-smi")


def _nvidia_smi_query() -> Optional[dict]:
    """One snapshot from nvidia-smi: temp/util/mem. None if unavailable.

    Returns {"temp_c", "util_percent", "mem_used_mb", "mem_total_mb"}.
    """
    if not _NVIDIA_SMI:
        return None
    try:
        out = subprocess.run(
            [_NVIDIA_SMI,
             "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        # First GPU line only (single-GPU rig).
        first = out.stdout.strip().splitlines()[0]
        temp, util, used, total = [p.strip() for p in first.split(",")]
        return {
            "temp_c": float(temp),
            "util_percent": float(util),
            "mem_used_mb": float(used),
            "mem_total_mb": float(total),
        }
    except Exception as e:
        log.debug(f"nvidia-smi query failed: {e}")
        return None


def gpu_available() -> bool:
    """True if an NVIDIA GPU is queryable via nvidia-smi."""
    return _nvidia_smi_query() is not None


class ResourcePolicy:
    """Decide the live CPU cap and Ollama thread budget."""

    def __init__(self):
        cfg = _load_config()
        limits = cfg.get("resource_limits", {})
        self.baseline = limits.get("cpu_percent_project", limits.get("cpu_percent_max", 75))
        self.burst = limits.get("cpu_percent_burst", 90)
        self.burst_when_idle = limits.get("burst_when_idle_or_needed", True)
        self.cores = os.cpu_count() or 8

        gpu = cfg.get("gpu_thermal", {})
        self.gpu_max_temp = gpu.get("gpu_max_temp_c", DEFAULT_GPU_MAX_TEMP_C)
        self.thermal_margin = gpu.get("thermal_margin", DEFAULT_THERMAL_MARGIN)
        self.gpu_load_high = gpu.get("gpu_load_high_percent", DEFAULT_GPU_LOAD_HIGH)

    # ------------------------------------------------------------------ #
    # GPU / thermal awareness
    # ------------------------------------------------------------------ #
    def gpu_snapshot(self) -> Optional[dict]:
        """Raw GPU metrics, or None if no GPU is queryable."""
        return _nvidia_smi_query()

    def gpu_temp(self) -> Optional[float]:
        """Current GPU temperature in °C, or None if unavailable."""
        snap = _nvidia_smi_query()
        return snap["temp_c"] if snap else None

    def gpu_load(self) -> Optional[float]:
        """Current GPU utilization %, or None if unavailable."""
        snap = _nvidia_smi_query()
        return snap["util_percent"] if snap else None

    def gpu_mem_free_mb(self) -> Optional[float]:
        """Free GPU VRAM in MB, or None if unavailable."""
        snap = _nvidia_smi_query()
        return (snap["mem_total_mb"] - snap["mem_used_mb"]) if snap else None

    def gpu_safe_to_use(self, snap: Optional[dict] = None) -> bool:
        """True when the GPU is cool enough to take new local work.

        If we can't read the GPU at all, we assume safe (CPU-only Ollama path).
        Unsafe once temp reaches the hard max, OR sits within the thermal
        margin AND is already heavily loaded (heading toward throttle).
        """
        snap = snap or _nvidia_smi_query()
        if snap is None:
            return True  # no GPU telemetry -> don't block local work
        temp = snap["temp_c"]
        if temp >= self.gpu_max_temp:
            return False
        if temp >= (self.gpu_max_temp - self.thermal_margin) \
                and snap["util_percent"] >= self.gpu_load_high:
            return False
        return True

    def thermal_headroom_c(self, snap: Optional[dict] = None) -> Optional[float]:
        """Degrees C below the hard max. None if no GPU telemetry."""
        snap = snap or _nvidia_smi_query()
        if snap is None:
            return None
        return round(self.gpu_max_temp - snap["temp_c"], 1)

    def ollama_threads_for_thermal(self, force_burst: bool = False) -> int:
        """Thread budget that also respects thermal headroom.

        Starts from the CPU-cap thread count, then halves it when the GPU is
        within the thermal margin (back off to let it cool), flooring at 1.
        """
        threads = self.ollama_threads(force_burst)
        snap = _nvidia_smi_query()
        if snap is not None:
            headroom = self.gpu_max_temp - snap["temp_c"]
            if headroom <= self.thermal_margin:
                threads = max(1, threads // 2)
        return threads

    def current_cap(self, force_burst: bool = False) -> int:
        """Live CPU % cap: baseline, or burst when idle / when forced."""
        if force_burst or (self.burst_when_idle and user_is_idle()):
            return self.burst
        return self.baseline

    def ollama_threads(self, force_burst: bool = False) -> int:
        """Translate the CPU cap into an Ollama num_thread count."""
        cap = self.current_cap(force_burst)
        threads = max(1, round(self.cores * cap / 100.0))
        return threads

    def status(self) -> dict:
        idle = _idle_seconds()
        snap = _nvidia_smi_query()
        out = {
            "cores": self.cores,
            "baseline_cap": self.baseline,
            "burst_cap": self.burst,
            "user_idle_s": round(idle, 1),
            "user_is_idle": idle >= IDLE_THRESHOLD_S,
            "active_cap": self.current_cap(),
            "ollama_threads": self.ollama_threads(),
            "ollama_threads_thermal": self.ollama_threads_for_thermal(),
            "gpu_available": snap is not None,
            "gpu_max_temp_c": self.gpu_max_temp,
            "thermal_margin": self.thermal_margin,
        }
        if snap is not None:
            out.update({
                "gpu_temp_c": snap["temp_c"],
                "gpu_load_percent": snap["util_percent"],
                "gpu_mem_used_mb": snap["mem_used_mb"],
                "gpu_mem_total_mb": snap["mem_total_mb"],
                "gpu_mem_free_mb": snap["mem_total_mb"] - snap["mem_used_mb"],
                "thermal_headroom_c": self.thermal_headroom_c(snap),
                "gpu_safe_to_use": self.gpu_safe_to_use(snap),
            })
        return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = ResourcePolicy()
    print(json.dumps(p.status(), indent=2))

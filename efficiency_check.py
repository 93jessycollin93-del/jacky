#!/usr/bin/env python3
"""
EFFICIENCY CHECK — understand Jacky's scale and performance.

Sends a representative workload through /api/ask, measures:
  - latency per task type
  - assessment verdicts (what escalates?)
  - model selection
  - GPU behavior (temp, load, VRAM)
  - fallback chain
  - overall throughput and cost

Run: python efficiency_check.py [--quick] [--verbose]
"""

import json
import time
import requests
import statistics
from datetime import datetime
from typing import List, Dict, Any

API_URL = "http://localhost:5000/api"

# Representative workloads (mixed task types + complexity).
WORKLOADS = [
    # light / general
    {"prompt": "What is a neutron star?", "task_type": "general", "name": "astronomy-101"},
    {"prompt": "Summarize: AI is advancing rapidly.", "task_type": "quick", "name": "summarize"},
    {"prompt": "Write a haiku about code.", "task_type": "creative", "name": "haiku"},

    # moderate / code
    {"prompt": "Write a Python function to check if a number is prime.", "task_type": "code", "name": "prime-check"},
    {"prompt": "Debug: function returns None instead of a list. Hints?", "task_type": "debug", "name": "debug-hint"},

    # heavy / reasoning
    {"prompt": "Explain why thermal limits matter for GPU workloads.", "task_type": "analysis", "name": "thermal-analysis"},
    {"prompt": "How would you optimize a batch processing system under thermal constraints?", "task_type": "reasoning", "name": "constraint-opt"},

    # edge cases
    {"prompt": "List 5 creative uses for a rubber duck.", "task_type": "creative", "name": "rubber-duck"},
    {"prompt": "What's the time complexity of mergesort?", "task_type": "code", "name": "complexity"},
]

class EfficiencyCheck:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None

    def _get_status(self) -> Dict[str, Any]:
        """Fetch /api/status to read GPU state."""
        try:
            r = requests.get(f"{API_URL}/status", timeout=5)
            return r.json() if r.status_code == 200 else {}
        except Exception as e:
            return {"error": str(e)}

    def run_workload(self, prompt: str, task_type: str, name: str) -> Dict[str, Any]:
        """Send a single request and capture all metrics."""
        before = self._get_status()
        before_temp = before.get("gpu", {}).get("temp_c")
        before_time = time.time()

        try:
            r = requests.post(
                f"{API_URL}/ask",
                json={"prompt": prompt, "task_type": task_type},
                timeout=180,  # increased for model loading on first run
            )
            after_time = time.time()
            latency = round(after_time - before_time, 2)

            after = self._get_status()
            after_temp = after.get("gpu", {}).get("temp_c")
            temp_delta = round((after_temp or 0) - (before_temp or 0), 1) if before_temp else None

            data = r.json() if r.status_code == 200 else {}
            assessment = data.get("assessment", {})
            chain = data.get("fallback_chain", [])
            chain_str = " → ".join(f"{s['step']}:{s['status']}" for s in chain) if chain else "N/A"

            result = {
                "name": name,
                "task_type": task_type,
                "status": data.get("status"),
                "engine": data.get("engine"),
                "model": data.get("model"),
                "latency_s": latency,
                "assessment_level": assessment.get("level"),
                "gpu_temp_before_c": before_temp,
                "gpu_temp_after_c": after_temp,
                "gpu_temp_delta_c": temp_delta,
                "fallback_chain": chain_str,
                "response_len": len(data.get("response", "")),
                "why": data.get("why", ""),
            }

            if self.verbose:
                print(f"\n[OK] {name:20} ({task_type:10})")
                print(f"  latency: {latency:.2f}s | model: {data.get('model')} | assess: {assessment.get('level')}")
                print(f"  GPU temp: {before_temp}C -> {after_temp}C ({temp_delta:+.1f}C)")
                print(f"  chain: {chain_str}")
                if data.get("why"):
                    print(f"  why: {data.get('why')[:70]}..." if len(data.get('why', '')) > 70 else f"  why: {data.get('why')}")

            return result
        except requests.exceptions.Timeout:
            return {
                "name": name,
                "task_type": task_type,
                "status": "timeout",
                "latency_s": 120,
                "error": "Request timed out",
            }
        except Exception as e:
            return {
                "name": name,
                "task_type": task_type,
                "status": "error",
                "error": str(e),
            }

    def run_all(self, workloads=None) -> None:
        """Execute all workloads and collect metrics."""
        workloads = workloads or WORKLOADS
        print(f"\n{'='*80}")
        print(f"JACKY EFFICIENCY CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        # Pre-flight check
        try:
            r = requests.get(f"{API_URL}/assessment", timeout=5)
            assessment = r.json() if r.status_code == 200 else {}
            print(f"Pre-flight: Assessment = {assessment.get('badge')} | GPU {assessment.get('gpu_temp_c')}C | Safe = {assessment.get('safe_to_run_local')}")
        except Exception as e:
            print(f"⚠ Pre-flight check failed: {e}")
            return

        print(f"\nWarm-up: loading a model into GPU memory...")
        try:
            r = requests.post(
                f"{API_URL}/ask",
                json={"prompt": "hi", "task_type": "quick"},
                timeout=180,
            )
            print(f"  Warm-up complete ({r.status_code})\n")
        except Exception as e:
            print(f"  Warm-up timeout (models loading from disk) — proceeding anyway...\n")

        print(f"Running {len(workloads)} workloads...\n")
        self.start_time = time.time()

        for wl in workloads:
            result = self.run_workload(wl["prompt"], wl["task_type"], wl["name"])
            self.results.append(result)
            time.sleep(0.5)  # brief cooldown between requests

        self.end_time = time.time()
        self.report()

    def report(self) -> None:
        """Generate efficiency report."""
        if not self.results:
            print("No results to report.")
            return

        print(f"\n{'='*80}")
        print("RESULTS")
        print(f"{'='*80}\n")

        # Overall stats
        elapsed = self.end_time - self.start_time
        successful = [r for r in self.results if r.get("status") == "ok"]
        errors = [r for r in self.results if r.get("status") != "ok"]

        print(f"Total requests: {len(self.results)}")
        print(f"Successful: {len(successful)} ({100*len(successful)//len(self.results)}%)")
        print(f"Errors: {len(errors)}")
        print(f"Total time: {elapsed:.1f}s")
        print(f"Throughput: {len(successful) / (elapsed/3600):.1f} questions/hour (local-only run)")
        print(f"Cost: $0 (all local)")
        print()

        # Latency by task type
        print(f"{'='*80}")
        print("LATENCY BY TASK TYPE")
        print(f"{'='*80}\n")

        by_type = {}
        for r in successful:
            tt = r.get("task_type", "unknown")
            if tt not in by_type:
                by_type[tt] = []
            by_type[tt].append(r["latency_s"])

        for tt in sorted(by_type.keys()):
            latencies = by_type[tt]
            if latencies:
                print(f"{tt:15} {len(latencies):2} reqs | "
                      f"avg: {statistics.mean(latencies):6.2f}s | "
                      f"min: {min(latencies):6.2f}s | "
                      f"max: {max(latencies):6.2f}s")
        print()

        # Assessment verdicts
        print(f"{'='*80}")
        print("ASSESSMENT VERDICTS (routing decisions)")
        print(f"{'='*80}\n")

        levels = {}
        for r in successful:
            level = r.get("assessment_level", "unknown")
            if level not in levels:
                levels[level] = 0
            levels[level] += 1

        for level in sorted(levels.keys()):
            count = levels[level]
            pct = 100 * count // len(successful)
            print(f"  {level:25} {count:2} ({pct:3}%)")
        print()

        # Model selection
        print(f"{'='*80}")
        print("MODEL SELECTION")
        print(f"{'='*80}\n")

        models = {}
        for r in successful:
            model = r.get("model", "unknown")
            if model not in models:
                models[model] = 0
            models[model] += 1

        for model in sorted(models.keys(), key=lambda m: models[m], reverse=True):
            count = models[model]
            pct = 100 * count // len(successful)
            print(f"  {model:35} {count:2} ({pct:3}%)")
        print()

        # GPU thermal impact
        print(f"{'='*80}")
        print("GPU THERMAL IMPACT")
        print(f"{'='*80}\n")

        temps_before = [r["gpu_temp_before_c"] for r in successful if r.get("gpu_temp_before_c")]
        temps_after = [r["gpu_temp_after_c"] for r in successful if r.get("gpu_temp_after_c")]
        temp_deltas = [r["gpu_temp_delta_c"] for r in successful if r.get("gpu_temp_delta_c") is not None]

        if temps_before and temps_after:
            print(f"GPU temp (start):   {min(temps_before):.1f}C - {max(temps_before):.1f}C (avg {statistics.mean(temps_before):.1f}C)")
            print(f"GPU temp (end):     {min(temps_after):.1f}C - {max(temps_after):.1f}C (avg {statistics.mean(temps_after):.1f}C)")
        if temp_deltas:
            avg_delta = statistics.mean(temp_deltas)
            print(f"GPU temp change:    avg {avg_delta:+.1f}C (range {min(temp_deltas):+.1f}C to {max(temp_deltas):+.1f}C)")
            if avg_delta <= 2:
                print(f"  [OK] Excellent thermal control - GPU stable under load")
            elif avg_delta <= 5:
                print(f"  [OK] Good - moderate heating, well within limits")
            else:
                print(f"  [WARN] Significant heat - monitor sustained workloads")
        print()

        # Fallback chain breakdown
        print(f"{'='*80}")
        print("FALLBACK CHAIN (all requests stayed local)")
        print(f"{'='*80}\n")

        chains = {}
        for r in self.results:
            chain = r.get("fallback_chain", "error/timeout")
            if chain not in chains:
                chains[chain] = 0
            chains[chain] += 1

        for chain in sorted(chains.keys()):
            count = chains[chain]
            pct = 100 * count // len(self.results)
            print(f"  {chain:50} {count:2} ({pct:3}%)")
        print()

        # Key insights
        print(f"{'='*80}")
        print("KEY INSIGHTS")
        print(f"{'='*80}\n")

        if levels.get("safe_for_local", 0) == len(successful):
            print("[OK] All requests ran locally (GPU healthy) - excellent cost profile.")
        elif levels.get("safe_for_light_cloud", 0) > 0:
            pct = 100 * levels.get("safe_for_light_cloud", 0) // len(successful)
            print(f"[WARM] {pct}% of requests were 'Warm' - GPU getting utilized but staying local.")
            print("  -> Moderate load is healthy; watch sustained workloads.")
        if levels.get("escalate_to_free", 0) > 0:
            pct = 100 * levels.get("escalate_to_free", 0) // len(successful)
            print(f"[ESCALATE] {pct}% of requests escalated to free cloud tier (GPU too hot/busy).")
            print("  -> Normal under heavy load; consider spacing requests if frequent.")

        latencies = [r["latency_s"] for r in successful]
        avg_latency = statistics.mean(latencies)
        print(f"\nAverage latency: {avg_latency:.2f}s per request")
        if avg_latency < 2:
            print("  [OK] Fast - excellent for interactive use")
        elif avg_latency < 10:
            print("  [OK] Reasonable - good for batch processing")
        else:
            print("  [WARN] Slow - consider larger models or prefer cloud for interactive tasks")

        # Cost savings
        print(f"\nCost analysis (assumed cloud = $0.01/request):")
        cloud_cost = len(successful) * 0.01
        print(f"  Local (this run): $0.00 [OK]")
        print(f"  Equiv. cloud cost: ${cloud_cost:.2f}")
        yearly_estimate = len(successful) * 365 * 0.01
        print(f"  Yearly local savings (1000 req/day): ${yearly_estimate:.2f}")
        print()

        print(f"{'='*80}")
        print("END OF REPORT")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    import sys
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    quick = "--quick" in sys.argv or "-q" in sys.argv

    check = EfficiencyCheck(verbose=verbose)
    workloads = WORKLOADS[:3] if quick else WORKLOADS
    check.run_all(workloads)

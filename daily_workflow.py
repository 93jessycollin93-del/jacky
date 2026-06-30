#!/usr/bin/env python3
"""
DAILY WORKFLOW ROUTINE - understand your Jacky system at a glance.

Run this each morning to:
  1. Check system readiness (Ollama + API + GPU)
  2. Run a quick efficiency pulse (5 representative tasks)
  3. Log metrics to CSV for trend tracking
  4. Show health summary
  5. (optional) Sync mirrored repos and summarize the result

Usage: python daily_workflow.py [--verbose] [--sync-repos]

Output: daily_efficiency_log.csv (appended with each run)

Scheduling: to keep repo mirrors fresh automatically, add a cron entry
(or Windows Task Scheduler job) that runs this script with --sync-repos,
e.g.:
  0 6 * * * cd /path/to/jacky && python daily_workflow.py --sync-repos
"""

import json
import csv
import sys
import time
import requests
import statistics
from datetime import datetime
from pathlib import Path

JACKY_HOME = Path(__file__).resolve().parent
sys.path.insert(0, str(JACKY_HOME / "scripts"))

API_URL = "http://localhost:5000/api"
LOG_FILE = Path(__file__).parent / "daily_efficiency_log.csv"

# Lightweight pulse tasks (5 quick ones, representative mix).
PULSE_TASKS = [
    {"prompt": "What is the capital of France?", "task_type": "general", "name": "trivia"},
    {"prompt": "Write a 10-line Python function to sum numbers.", "task_type": "code", "name": "coding"},
    {"prompt": "Explain why this matters for AI: batch processing.", "task_type": "analysis", "name": "analysis"},
    {"prompt": "Quick joke about programming.", "task_type": "creative", "name": "creative"},
    {"prompt": "List 3 tips for GPU optimization.", "task_type": "reasoning", "name": "tips"},
]

class DailyWorkflow:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = []
        self.start_time = None

    def _request(self, path, method="GET", json_data=None, timeout=10):
        """Make API request with friendly error handling."""
        try:
            # Determine full URL based on path
            if path.startswith("/api"):
                url = f"http://localhost:5000{path}"
            elif path.startswith("/"):
                url = f"http://localhost:5000{path}"
            else:
                url = f"http://localhost:11434/{path}"

            if method == "GET":
                r = requests.get(url, timeout=timeout)
            else:
                r = requests.post(url, json=json_data, timeout=timeout)
            return r.json() if r.status_code == 200 else None
        except requests.exceptions.Timeout:
            return {"error": "timeout"}
        except Exception as e:
            return {"error": str(e)}

    def check_system(self):
        """Verify all components are ready."""
        print("\n" + "="*70)
        print("SYSTEM CHECK")
        print("="*70)

        checks = {}

        # Ollama
        models = self._request("api/tags") or {}
        ollama_ok = "models" in models and len(models["models"]) > 0
        checks["ollama"] = ("OK" if ollama_ok else "FAIL")
        print(f"  Ollama:    {checks['ollama']:6} ({len(models.get('models', []))} models loaded)")

        # API health
        health = self._request("/health") or {}
        api_ok = health.get("status") == "healthy"
        checks["api"] = ("OK" if api_ok else "FAIL")
        print(f"  API:       {checks['api']:6} (http://localhost:5000)")

        # Assessment
        assess = self._request("/api/assessment") or {}
        assess_ok = "level" in assess
        checks["assessment"] = ("OK" if assess_ok else "FAIL")
        badge = assess.get("badge", "?")
        print(f"  Assessment:{checks['assessment']:6} ({badge})")

        # GPU
        gpu_temp = assess.get("gpu_temp_c", "?")
        gpu_ok = assess.get("gpu_available", False)
        checks["gpu"] = ("OK" if gpu_ok else "FAIL")
        print(f"  GPU:       {checks['gpu']:6} ({gpu_temp}C, headroom {assess.get('thermal_headroom_c', '?')}C)")

        all_ok = all(c == "OK" for c in checks.values())
        print(f"\n  Status: {'ALL OK' if all_ok else 'ISSUES FOUND'}\n")
        return all_ok, assess

    def run_pulse(self):
        """Run 5 quick, representative tasks."""
        print("="*70)
        print("PULSE RUN (5 tasks)")
        print("="*70 + "\n")

        self.start_time = time.time()
        successful = 0
        errors = 0

        for task in PULSE_TASKS:
            result = {
                "timestamp": datetime.now().isoformat(),
                "name": task["name"],
                "task_type": task["task_type"],
            }

            before_time = time.time()
            response = self._request(
                "/api/ask",
                method="POST",
                json_data={"prompt": task["prompt"], "task_type": task["task_type"]},
                timeout=90,
            )
            after_time = time.time()

            latency = round(after_time - before_time, 2)
            result["latency_s"] = latency

            if response and response.get("status") == "ok":
                result["status"] = "ok"
                result["model"] = response.get("model")
                result["assessment"] = response.get("assessment", {}).get("level")
                result["engine"] = response.get("engine")
                successful += 1
                if self.verbose:
                    print(f"  [{task['name']:10}] {latency:6.2f}s | {response.get('model'):20} | {result.get('assessment')}")
            else:
                result["status"] = "error"
                errors += 1
                if self.verbose:
                    print(f"  [{task['name']:10}] ERROR: {response.get('error', 'unknown')}")

            self.results.append(result)
            time.sleep(0.3)

        elapsed = time.time() - self.start_time
        print(f"\nResults: {successful}/5 OK, {errors} errors in {elapsed:.1f}s")
        print(f"Throughput: {successful / (elapsed/3600):.0f} questions/hour\n")

        return successful, errors

    def log_metrics(self, assess):
        """Append results to CSV for trend tracking."""
        if not self.results:
            return

        successful = [r for r in self.results if r["status"] == "ok"]
        if not successful:
            return

        latencies = [r["latency_s"] for r in successful]
        avg_latency = statistics.mean(latencies)

        row = {
            "date": datetime.now().isoformat()[:10],
            "time": datetime.now().isoformat()[11:19],
            "pulse_successful": len(successful),
            "pulse_avg_latency_s": round(avg_latency, 2),
            "pulse_min_latency_s": min(latencies),
            "pulse_max_latency_s": max(latencies),
            "assessment_level": assess.get("level", "?"),
            "gpu_temp_c": assess.get("gpu_temp_c", "?"),
            "gpu_load_percent": assess.get("gpu_load_percent", "?"),
            "gpu_safe": assess.get("gpu_safe_to_use", "?"),
            "models_used": len(set(r.get("model") for r in successful if r.get("model"))),
        }

        # Create file with header on first run.
        if not LOG_FILE.exists():
            with open(LOG_FILE, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=row.keys())
                w.writeheader()

        # Append row.
        with open(LOG_FILE, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=row.keys())
            w.writerow(row)

        print(f"[Logged to {LOG_FILE.name}]")

    def print_summary(self, assess):
        """Print health summary + actionable insights."""
        print("="*70)
        print("SUMMARY")
        print("="*70)

        successful = [r for r in self.results if r["status"] == "ok"]
        if not successful:
            print("No successful results to summarize.\n")
            return

        latencies = [r["latency_s"] for r in successful]
        avg_latency = statistics.mean(latencies)
        models_used = set(r.get("model") for r in successful if r.get("model"))

        print(f"\n  Success rate: {len(successful)}/5 ({100*len(successful)//5}%)")
        print(f"  Avg latency: {avg_latency:.2f}s per task")
        print(f"  Models used: {', '.join(sorted(models_used))}")
        print(f"  Assessment: {assess.get('level')} ({assess.get('badge')})")
        print(f"  GPU temp: {assess.get('gpu_temp_c')}C (headroom: {assess.get('thermal_headroom_c')}C)")

        # Insights
        print("\n  Insights:")
        if len(successful) == 5:
            print("    [OK] All pulse tasks completed.")
        elif len(successful) >= 3:
            print("    [WARN] Some tasks timed out - system under load?")
        else:
            print("    [ALERT] Multiple failures - check logs.")

        if avg_latency < 5:
            print("    [OK] Response time excellent for batch processing.")
        elif avg_latency < 15:
            print("    [OK] Response time reasonable.")
        else:
            print("    [WARN] Response time slow - monitor model selection.")

        if assess.get("gpu_temp_c", 0) < 70:
            print("    [OK] GPU running cool - plenty of headroom.")
        elif assess.get("gpu_temp_c", 0) < 75:
            print("    [WARN] GPU warming up - monitor for sustained loads.")
        else:
            print("    [ALERT] GPU hot - escalating to cloud tier.")

        # Check log trends if available.
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 100:
            with open(LOG_FILE, "r") as f:
                rows = list(csv.DictReader(f))
            if len(rows) >= 2:
                prev = rows[-2]
                curr = rows[-1]
                try:
                    prev_latency = float(prev.get("pulse_avg_latency_s", 0))
                    curr_latency = float(curr.get("pulse_avg_latency_s", 0))
                    delta = curr_latency - prev_latency
                    if abs(delta) > 1:
                        direction = "increased" if delta > 0 else "decreased"
                        print(f"    Latency {direction} {abs(delta):.1f}s vs yesterday.")
                except:
                    pass

        print()

    def run_repo_sync(self):
        """Run scripts/sync_repos.py and print a one-line summary.

        Network/git heavy, so this only runs when --sync-repos is passed
        (or scheduled separately via cron), never as part of the default
        morning pulse.
        """
        print("="*70)
        print("REPO MIRROR SYNC")
        print("="*70)
        sync_script = JACKY_HOME / "scripts" / "sync_repos.py"
        if not sync_script.exists():
            print(f"  [ALERT] {sync_script} not found — skipping repo sync.\n")
            return 1
        try:
            import sync_repos as sync_repos_module
        except Exception as e:
            print(f"  [ALERT] could not import sync_repos.py: {e}\n")
            return 1
        try:
            exit_code = sync_repos_module.main([])
        except Exception as e:
            print(f"  [ALERT] sync_repos.py raised an error while running: {e}\n")
            return 1

        from repo_mirror import load_status
        status = load_status()
        print(f"  {status.get('ok', 0)} ok, {status.get('errors', 0)} errors, "
              f"{status.get('total', 0)} total repos.\n")
        return exit_code


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    do_sync = "--sync-repos" in sys.argv

    wf = DailyWorkflow(verbose=verbose)

    if do_sync:
        wf.run_repo_sync()

    # System check
    all_ok, assess = wf.check_system()
    if not all_ok:
        print("[ALERT] System not ready. Fix issues above before running pulse.\n")
        return 1

    # Pulse
    successful, errors = wf.run_pulse()

    # Log + summary
    wf.log_metrics(assess)
    wf.print_summary(assess)

    print("="*70)
    print(f"Daily workflow complete. Log at {LOG_FILE}\n")

    return 0 if successful >= 3 else 1


if __name__ == "__main__":
    exit(main())

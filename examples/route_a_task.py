#!/usr/bin/env python3
"""
examples/route_a_task.py — Demonstrate OmniAgent task routing via Jacky.

Run: python examples/route_a_task.py
"""

import sys
import pathlib

# Add repo root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from situation_assessor import SituationAssessor
from cloud_router import CloudRouter


def main():
    print("=== OmniAgent Task Routing Example ===\n")

    # 1. Check system status
    assessor = SituationAssessor()
    try:
        status = assessor.assess()
        gpu_temp = status.get("gpu_temp_c", "N/A")
        print(f"System status: GPU={gpu_temp}°C  CPU={status.get('cpu_percent','?')}%"
              f"  RAM={status.get('ram_percent','?')}%")
        print(f"Recommended tier: {status.get('recommended_tier', 'unknown')}\n")
    except Exception as exc:
        print(f"[WARN] Could not read system status: {exc}\n")

    # 2. Route a simple task
    task = "Summarise the purpose of jacky_core.py in one sentence."
    print(f"Task: {task!r}\n")

    router = CloudRouter()
    try:
        response = router.route(task)
        print(f"Response:\n{response}\n")
    except Exception as exc:
        print(f"[ERROR] Routing failed: {exc}")
        print("Make sure at least one API key (GROQ/GEMINI/ANTHROPIC) is set.")


if __name__ == "__main__":
    main()

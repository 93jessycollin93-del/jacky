"""
Example: Demonstrate OmniAgent's economy-first model routing.

Shows how situation_assessor.py feeds into cloud_router.py to pick
the cheapest capable model for a given prompt.
"""
from __future__ import annotations

import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from situation_assessor import SituationAssessor
    from cloud_router import CloudRouter
except ImportError:
    print("Run from the repo root: python examples/routing_demo.py")
    sys.exit(1)


def demo_routing(prompt: str) -> None:
    assessor = SituationAssessor()
    situation = assessor.assess()

    print("=== Current Situation ===")
    print(f"  GPU temp   : {situation.get('gpu_temp', 'N/A')} °C")
    print(f"  CPU usage  : {situation.get('cpu_percent', 'N/A')} %")
    print(f"  RAM usage  : {situation.get('ram_percent', 'N/A')} %")
    print(f"  Routing to : {situation.get('recommended_tier', 'cloud')}")
    print()

    router = CloudRouter()
    print(f"Sending prompt ({len(prompt)} chars) to cloud router...")
    response = router.complete(prompt)
    print("Response:", response[:300], "..." if len(response) > 300 else "")


if __name__ == "__main__":
    demo_routing("Explain in one sentence why GPU thermal management matters for AI workloads.")

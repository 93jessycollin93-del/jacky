"""
Example: Submit a task to OmniAgent via the Jacky API.

Run this from the repo root after `python jacky_api.py` is running:
    python examples/submit_task.py
"""
import json
import urllib.request

BASE_URL = "http://localhost:5000"


def submit_task(name: str, payload: dict) -> dict:
    data = json.dumps({"name": name, "payload": payload}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/task",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get_status() -> dict:
    with urllib.request.urlopen(f"{BASE_URL}/api/status", timeout=5) as resp:
        return json.loads(resp.read())


if __name__ == "__main__":
    # 1. Check Jacky is running
    status = get_status()
    print("Jacky status:", json.dumps(status, indent=2))

    # 2. Submit a simple task
    result = submit_task("analyze_code", {"path": "jacky_core.py", "focus": "routing"})
    print("\nTask result:", json.dumps(result, indent=2))

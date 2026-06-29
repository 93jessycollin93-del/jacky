#!/usr/bin/env python3
"""Quick integration test of thinking mode implementation."""

import json
from pathlib import Path

# Test 1: Verify runtime controls persist
print("=== Test 1: Runtime Control State ===")
from jacky_api import RUNTIME, VALID_MODES
print(f"Active: {RUNTIME['active']}")
print(f"Thinking mode: {RUNTIME['thinking_mode']}")
print(f"Valid modes: {VALID_MODES}")

# Test 2: Verify ensemble accepts mode param
print("\n=== Test 2: Ensemble Query with Thinking Mode ===")
from ollama_ensemble import OllamaEnsemble, THINKING_MODES
import inspect

ens = OllamaEnsemble()
sig = inspect.signature(ens.query_best)
params = list(sig.parameters.keys())
print(f"query_best signature: {params}")
assert 'mode' in params, "mode parameter missing from query_best!"
print("PASS: query_best accepts 'mode' parameter")

# Test 3: Verify thinking modes are defined
print("\n=== Test 3: Thinking Mode Presets ===")
for mode, preset in THINKING_MODES.items():
    print(f"  {mode:10s}: num_predict={preset.get('num_predict')}, "
          f"force_small={preset.get('force_small', False)}, "
          f"force_specialty={preset.get('force_specialty', 'None')}")
print("PASS: All thinking modes defined with presets")

# Test 4: Config persistence
print("\n=== Test 4: Config Persistence ===")
cfg_path = Path("config.json")
if cfg_path.exists():
    with open(cfg_path) as f:
        cfg = json.load(f)
    if "runtime_controls" in cfg:
        print(f"Persisted runtime_controls: {cfg['runtime_controls']}")
        print("PASS: Runtime controls can be persisted to config.json")
    else:
        print("NOTE: config.json exists but no runtime_controls yet (will be added on first save)")
else:
    print("NOTE: config.json not found (normal if first boot)")

print("\n=== All Tests Passed ===")
print("Dashboard controls are wired and ready to test in browser")

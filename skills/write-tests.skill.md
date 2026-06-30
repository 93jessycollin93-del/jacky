---
skill: write-tests
description: Generate comprehensive pytest tests for a given Python module.
version: "1.0"
tools: [read_file, write_file, run_tests]
inputs:
  - name: module_path
    description: Path to the Python module to test
outputs:
  - name: test_file_path
    description: Path of the created test file
---

# Skill: Write Tests

## Purpose

Generate a complete pytest test file for a Python module, covering all public
functions and key edge cases.

## Steps

1. **Read** the module; list all public functions and classes.
2. **Identify** for each function:
   - Normal inputs → expected outputs.
   - Edge cases (empty, None, 0, large values).
   - Error paths (exceptions, invalid types).
3. **Write** test file at `tests/test_{module_name}.py`.
4. **Mock** external dependencies (API calls, file I/O, GPU queries).
5. **Run** `pytest tests/test_{module_name}.py -v` and fix failures.

## Test naming convention

```python
def test_{function_name}_{scenario}():
    # arrange
    # act
    # assert
```

## Mock patterns (use these for Jacky-specific dependencies)

```python
from unittest.mock import patch, MagicMock

@patch("situation_assessor.subprocess.run")
def test_gpu_temp_returns_float(mock_run):
    mock_run.return_value.stdout = "65.0"
    ...
```

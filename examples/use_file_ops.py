#!/usr/bin/env python3
"""
examples/use_file_ops.py — Demonstrate the OmniAgent file operations tool.

Run: python examples/use_file_ops.py
"""

import sys
import pathlib
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools.file_ops import read_file, write_file, list_files, edit_file


def main():
    print("=== OmniAgent File Ops Example ===\n")

    # 1. List Python files at repo root
    py_files = list_files(".", "*.py")
    print(f"Top-level Python files ({len(py_files)}):")
    for f in py_files[:5]:
        print(f"  {f}")
    if len(py_files) > 5:
        print(f"  ... and {len(py_files) - 5} more\n")
    else:
        print()

    # 2. Read a file
    content = read_file("config.json")
    print(f"config.json ({len(content)} chars):")
    print(content[:200], "...\n" if len(content) > 200 else "\n")

    # 3. Write a temporary scratch file
    scratch = "examples/scratch_demo.txt"
    write_file(scratch, "Hello from OmniAgent file_ops!\n", overwrite=True)
    print(f"Wrote '{scratch}'")

    # 4. Edit the scratch file
    n = edit_file(scratch, "Hello from OmniAgent", "Greetings from OmniAgent")
    print(f"Edit applied: {n} replacement(s)")

    # 5. Read it back
    result = read_file(scratch)
    print(f"Final content: {result.strip()}")

    # Cleanup
    pathlib.Path(scratch).unlink(missing_ok=True)
    print("\nDone. Scratch file cleaned up.")


if __name__ == "__main__":
    main()

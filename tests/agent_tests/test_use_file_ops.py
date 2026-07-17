#!/usr/bin/env python3
"""
tests/agent_tests/test_use_file_ops.py — Unit tests for examples/use_file_ops.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from examples import use_file_ops

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRATCH_FILE = _REPO_ROOT / "examples" / "scratch_demo.txt"


def test_main_happy_path(monkeypatch, capsys):
    calls = {}

    def fake_list_files(directory, pattern):
        calls["list_files"] = (directory, pattern)
        return ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"]

    def fake_read_file(path):
        calls.setdefault("read_file", []).append(path)
        if path == "config.json":
            return "{}"
        return "Greetings from OmniAgent file_ops!\n"

    def fake_write_file(path, content, overwrite=False):
        calls["write_file"] = (path, content, overwrite)

    def fake_edit_file(path, old, new):
        calls["edit_file"] = (path, old, new)
        return 1

    monkeypatch.setattr(use_file_ops, "list_files", fake_list_files)
    monkeypatch.setattr(use_file_ops, "read_file", fake_read_file)
    monkeypatch.setattr(use_file_ops, "write_file", fake_write_file)
    monkeypatch.setattr(use_file_ops, "edit_file", fake_edit_file)

    use_file_ops.main()

    out = capsys.readouterr().out
    assert "Top-level Python files (6):" in out
    assert "... and 1 more" in out
    assert "config.json (2 chars):" in out
    assert "Wrote 'examples/scratch_demo.txt'" in out
    assert "Edit applied: 1 replacement(s)" in out
    assert "Final content: Greetings from OmniAgent file_ops!" in out
    assert "Scratch file cleaned up." in out

    assert calls["list_files"] == (".", "*.py")
    assert calls["write_file"] == (
        "examples/scratch_demo.txt", "Hello from OmniAgent file_ops!\n", True,
    )
    assert calls["edit_file"] == (
        "examples/scratch_demo.txt",
        "Hello from OmniAgent",
        "Greetings from OmniAgent",
    )
    # write_file was mocked (never touched disk), so the real cleanup call
    # (`Path.unlink(missing_ok=True)`) must be a safe no-op, not an error.
    assert not _SCRATCH_FILE.exists()


def test_main_with_five_or_fewer_py_files(monkeypatch, capsys):
    monkeypatch.setattr(use_file_ops, "list_files", lambda d, p: ["a.py", "b.py"])
    monkeypatch.setattr(use_file_ops, "read_file",
                         lambda path: "{}" if path == "config.json" else "done")
    monkeypatch.setattr(use_file_ops, "write_file", lambda path, content, overwrite=False: None)
    monkeypatch.setattr(use_file_ops, "edit_file", lambda path, old, new: 1)

    use_file_ops.main()

    out = capsys.readouterr().out
    assert "Top-level Python files (2):" in out
    assert "more" not in out


def test_main_truncates_long_config_preview(monkeypatch, capsys):
    long_content = "x" * 500
    monkeypatch.setattr(use_file_ops, "list_files", lambda d, p: ["a.py"])
    monkeypatch.setattr(
        use_file_ops, "read_file",
        lambda path: long_content if path == "config.json" else "done",
    )
    monkeypatch.setattr(use_file_ops, "write_file", lambda path, content, overwrite=False: None)
    monkeypatch.setattr(use_file_ops, "edit_file", lambda path, old, new: 1)

    use_file_ops.main()

    out = capsys.readouterr().out
    assert "config.json (500 chars):" in out
    assert "x" * 200 in out
    assert "x" * 201 not in out


def test_main_reports_zero_replacements(monkeypatch, capsys):
    monkeypatch.setattr(use_file_ops, "list_files", lambda d, p: [])
    monkeypatch.setattr(use_file_ops, "read_file",
                         lambda path: "{}" if path == "config.json" else "unchanged")
    monkeypatch.setattr(use_file_ops, "write_file", lambda path, content, overwrite=False: None)
    monkeypatch.setattr(use_file_ops, "edit_file", lambda path, old, new: 0)

    use_file_ops.main()

    out = capsys.readouterr().out
    assert "Top-level Python files (0):" in out
    assert "Edit applied: 0 replacement(s)" in out
    assert "Final content: unchanged" in out
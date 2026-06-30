#!/usr/bin/env python3
"""
tests/agent_tests/test_file_ops.py — Unit tests for tools/file_ops.py
"""

import pathlib
import pytest
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.file_ops import (
    _safe_path,
    read_file,
    write_file,
    edit_file,
    list_files,
    delete_file,
    copy_file,
    _REPO_ROOT,
)

_SCRATCH = _REPO_ROOT / "tests" / "agent_tests" / "_scratch"


@pytest.fixture(autouse=True)
def cleanup_scratch():
    """Remove scratch files before and after each test."""
    import shutil
    if _SCRATCH.exists():
        shutil.rmtree(_SCRATCH)
    _SCRATCH.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(_SCRATCH, ignore_errors=True)


# ── _safe_path ───────────────────────────────────────────────────────────────

def test_safe_path_relative():
    p = _safe_path("config.json")
    assert p.is_absolute()
    assert p.parent == _REPO_ROOT


def test_safe_path_rejects_outside_root(tmp_path):
    with pytest.raises(PermissionError, match="outside the repository root"):
        _safe_path(str(tmp_path / "evil.txt"))


def test_safe_path_rejects_secrets():
    with pytest.raises(PermissionError, match="protected"):
        _safe_path("secrets/secrets.env")


# ── write_file / read_file ────────────────────────────────────────────────────

def test_write_and_read():
    path = str(_SCRATCH / "hello.txt")
    write_file(path, "Hello, OmniAgent!")
    assert read_file(path) == "Hello, OmniAgent!"


def test_write_raises_if_exists():
    path = str(_SCRATCH / "exists.txt")
    write_file(path, "first")
    with pytest.raises(FileExistsError):
        write_file(path, "second")


def test_write_overwrite():
    path = str(_SCRATCH / "overwrite.txt")
    write_file(path, "first")
    write_file(path, "second", overwrite=True)
    assert read_file(path) == "second"


def test_write_creates_parents():
    path = str(_SCRATCH / "deep" / "dir" / "file.txt")
    write_file(path, "deep")
    assert pathlib.Path(path).exists()


# ── edit_file ────────────────────────────────────────────────────────────────

def test_edit_replaces_first_occurrence():
    path = str(_SCRATCH / "edit.txt")
    write_file(path, "foo foo foo")
    count = edit_file(path, "foo", "bar")
    assert count == 1
    assert read_file(path) == "bar foo foo"


def test_edit_returns_zero_when_not_found():
    path = str(_SCRATCH / "edit2.txt")
    write_file(path, "hello")
    count = edit_file(path, "xyz", "abc")
    assert count == 0


# ── list_files ───────────────────────────────────────────────────────────────

def test_list_files_returns_py_files():
    files = list_files(".", "*.py")
    assert len(files) > 0
    assert all(f.endswith(".py") for f in files)


def test_list_files_excludes_hidden():
    files = list_files(".", "**/*")
    assert not any(part.startswith(".") for f in files for part in pathlib.Path(f).parts)


# ── delete_file ──────────────────────────────────────────────────────────────

def test_delete_existing_file():
    path = str(_SCRATCH / "del.txt")
    write_file(path, "bye")
    assert delete_file(path) is True
    assert not pathlib.Path(path).exists()


def test_delete_nonexistent_file():
    assert delete_file(str(_SCRATCH / "ghost.txt")) is False


# ── copy_file ────────────────────────────────────────────────────────────────

def test_copy_file():
    src = str(_SCRATCH / "src.txt")
    dst = str(_SCRATCH / "dst.txt")
    write_file(src, "copy me")
    copy_file(src, dst)
    assert read_file(dst) == "copy me"
    assert pathlib.Path(src).exists()  # original untouched


def test_copy_raises_if_dst_exists():
    src = str(_SCRATCH / "src2.txt")
    dst = str(_SCRATCH / "dst2.txt")
    write_file(src, "a")
    write_file(dst, "b")
    with pytest.raises(FileExistsError):
        copy_file(src, dst)

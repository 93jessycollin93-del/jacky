#!/usr/bin/env python3
"""
tools/file_ops.py — File-operation helpers used by OmniAgent tool calls.

These utilities wrap common filesystem operations with safety checks so the
agent cannot accidentally overwrite protected paths or write outside the
repository root.
"""

from __future__ import annotations

import os
import pathlib
import shutil
from typing import Optional

# Resolve the repository root once at import time
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

_PROTECTED = {
    ".git",
    "secrets",
    ".env",
    "secrets.env",
}


def _safe_path(rel_or_abs: str) -> pathlib.Path:
    """Resolve *rel_or_abs* and confirm it lives inside the repo root."""
    p = pathlib.Path(rel_or_abs)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    p = p.resolve()
    try:
        p.relative_to(_REPO_ROOT)
    except ValueError as exc:
        raise PermissionError(
            f"Path '{p}' is outside the repository root '{_REPO_ROOT}'"
        ) from exc
    for part in p.parts:
        if part in _PROTECTED:
            raise PermissionError(f"Path '{p}' touches a protected component: '{part}'")
    return p


def read_file(path: str) -> str:
    """Return the text content of *path*."""
    return _safe_path(path).read_text(encoding="utf-8")


def write_file(path: str, content: str, *, overwrite: bool = False) -> pathlib.Path:
    """Write *content* to *path*.

    Creates parent directories automatically.
    Raises FileExistsError if the file exists and *overwrite* is False.
    """
    p = _safe_path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(
            f"'{p}' already exists. Pass overwrite=True to replace it."
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def edit_file(path: str, old: str, new: str) -> int:
    """Replace the first occurrence of *old* with *new* in *path*.

    Returns the number of replacements made (0 or 1).
    """
    p = _safe_path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        return 0
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return 1


def list_files(
    directory: str = ".",
    pattern: str = "**/*",
    *,
    exclude_hidden: bool = True,
) -> list[str]:
    """Return relative paths of files matching *pattern* under *directory*."""
    d = _safe_path(directory)
    results: list[str] = []
    for p in d.glob(pattern):
        if not p.is_file():
            continue
        if exclude_hidden and any(part.startswith(".") for part in p.parts):
            continue
        results.append(str(p.relative_to(_REPO_ROOT)))
    return sorted(results)


def delete_file(path: str) -> bool:
    """Delete a single file.  Returns True on success."""
    p = _safe_path(path)
    if not p.exists():
        return False
    p.unlink()
    return True


def copy_file(src: str, dst: str, *, overwrite: bool = False) -> pathlib.Path:
    """Copy *src* to *dst* inside the repo."""
    s = _safe_path(src)
    d = _safe_path(dst)
    if d.exists() and not overwrite:
        raise FileExistsError(f"'{d}' already exists.")
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s, d)
    return d


if __name__ == "__main__":
    # Quick smoke-test
    print("Repo root:", _REPO_ROOT)
    files = list_files(".", "*.py")
    print(f"Found {len(files)} Python files at root")
    print(files[:5])

#!/usr/bin/env python3
"""
SECRETS LOADER - one place to read API keys, future-proofed.

Precedence (first hit wins):
  1. Real process environment variables (os.environ)
  2. Gitignored secret store:  E:\AI\Jacky\secrets\secrets.env
  3. Project .env  (placeholders only — NEVER real secrets)

Rules that keep this clean:
  - Real secrets live ONLY in secrets/secrets.env (gitignored via .gitignore).
  - .env in the project holds placeholders, so it is safe to back up / commit.
  - Nothing reads a secret at import time; keys are fetched lazily when used,
    so launching the app never surfaces real credentials.

Frame: It's Jacky's PC. Secrets stay in one gitignored vault; code reads, never embeds.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List

log = logging.getLogger("SecretsLoader")

JACKY_HOME = Path(__file__).parent
SECRET_STORE = JACKY_HOME / "secrets" / "secrets.env"
PROJECT_ENV = JACKY_HOME / ".env"

# Values that mean "not set yet" — treated as absent.
_PLACEHOLDER_PREFIXES = ("PASTE", "WAITING", "YOUR", "SET_THIS", "<")


def _parse_env_file(path: Path) -> dict:
    out = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    except Exception as e:
        log.warning(f"reading {path.name} failed: {e}")
    return out


def _is_real(val: Optional[str]) -> bool:
    if not val:
        return False
    return not val.upper().startswith(_PLACEHOLDER_PREFIXES)


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch one secret by name, honoring the precedence chain."""
    # 1. process env
    val = os.getenv(name)
    if _is_real(val):
        return val
    # 2. gitignored secret store
    store = _parse_env_file(SECRET_STORE)
    if _is_real(store.get(name)):
        return store[name]
    # 3. project .env (placeholders only, but allow real if user pasted there)
    proj = _parse_env_file(PROJECT_ENV)
    if _is_real(proj.get(name)):
        return proj[name]
    return default


def get_keys(names: List[str]) -> List[str]:
    """Resolve a list of key names to their real values (placeholders dropped)."""
    out = []
    for n in names:
        v = get_secret(n)
        if v:
            out.append(v)
    return out


def store_exists() -> bool:
    return SECRET_STORE.exists()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Secret store present: {store_exists()} ({SECRET_STORE})")
    # Report only which known names resolve — never print the values.
    for n in ["GROQ_API_KEY_1", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
              "XAI_API_KEY_1", "XAI_API_KEY_2", "XAI_API_KEY_3", "XAI_API_KEY_4"]:
        print(f"  {n}: {'set' if get_secret(n) else 'not set'}")

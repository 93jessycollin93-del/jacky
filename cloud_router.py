#!/usr/bin/env python3
"""
CLOUD ROUTER - free-first failover across cloud providers.

Reads the provider order + per-provider enabled flags from config.json,
loads each provider's key(s) from .env, and tries them in order until one
answers. Returns a structured result; signals local fallback if all fail
or none are enabled.

This is the free escalation tier (Groq -> Gemini -> OpenRouter) — the safety
net, not the primary. The xAI paid backup was removed from active routing; any
archived keys remain in the vault, untouched, for the user to manage.

Frame: It's Jacky's PC. Free clouds first, local last.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from secrets_loader import get_keys  # vault-aware, lazy secret resolution

log = logging.getLogger("CloudRouter")

JACKY_HOME = Path(__file__).parent

# Which key names feed each provider (resolved lazily via secrets_loader,
# which reads the gitignored vault — never slurps real secrets at boot).
PROVIDER_KEYS = {
    "groq":       ["GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3"],
    "gemini":     ["GEMINI_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
}


class CloudRouter:
    """Try enabled cloud providers in config order; first success wins."""

    def __init__(self):
        self.config = self._load_config()
        self.order = self._provider_order()

    def _load_config(self) -> dict:
        try:
            with open(JACKY_HOME / "config.json") as f:
                return json.load(f)
        except Exception:
            return {}

    def _provider_order(self) -> List[str]:
        """Ordered list of ENABLED providers from config.cloud_bots.providers."""
        cb = self.config.get("integrations", {}).get("cloud_bots", {})
        providers = cb.get("providers", [])
        order = []
        for p in providers:
            if isinstance(p, str):
                order.append(p)  # bare name = enabled
            elif isinstance(p, dict) and p.get("enabled", False):
                order.append(p.get("name"))
        return [p for p in order if p]

    def _keys_for(self, provider: str) -> List[str]:
        """Resolve a provider's keys via the vault-aware loader (lazy)."""
        return get_keys(PROVIDER_KEYS.get(provider, []))

    def available(self) -> List[dict]:
        """Which enabled providers actually have usable keys."""
        out = []
        for p in self.order:
            keys = self._keys_for(p)
            out.append({"provider": p, "has_keys": bool(keys), "key_count": len(keys)})
        return out

    def ask(self, prompt: str, system: Optional[str] = None,
            max_tokens: int = 512) -> dict:
        """Try each enabled provider with keys, in order. First success wins."""
        from cloud_client import CloudClient, CloudError  # local import; SSL via truststore

        tried = []
        for provider in self.order:
            keys = self._keys_for(provider)
            if not keys:
                tried.append({"provider": provider, "skipped": "no keys"})
                continue
            try:
                client = CloudClient(provider, keys)
                result = client.timed_generate(prompt, system=system, max_tokens=max_tokens)
                result["tried"] = tried
                if result.get("status") == "ok":
                    return result
                tried.append({"provider": provider, "error": result.get("response")})
            except Exception as e:
                tried.append({"provider": provider, "error": str(e)})

        return {"status": "error", "engine": "cloud", "tried": tried,
                "response": "All enabled cloud providers failed or have no keys."}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = CloudRouter()
    print("Enabled provider order:", r.order)
    print("Availability:")
    for a in r.available():
        print(f"  {a['provider']}: keys={a['key_count']}")

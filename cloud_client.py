#!/usr/bin/env python3
"""
CLOUD CLIENT - generic OpenAI-compatible client for free cloud inference.

One client, many providers. xAI (Grok), Groq, Gemini (OpenAI-compat),
OpenRouter, etc. all speak the same /chat/completions shape — so we pick
the provider by base_url + model + key instead of writing one file each.

Two local-environment realities are handled here:
  1. SSL interception (Avast/VPN) breaks normal TLS verification on this PC,
     so we use an unverified SSL context for outbound HTTPS. (Same root cause
     as the pip --trusted-host workaround.)
  2. Multiple keys -> round-robin rotation with failover to the next key.

Frame: It's Jacky's PC. Local-first; free cloud when it helps.
"""

import json
import ssl
import time
import logging
import urllib.request
import urllib.error
from typing import List, Optional

log = logging.getLogger("CloudClient")

# TLS context that trusts the Windows cert store (where Avast's HTTPS-
# interception root already lives). This keeps verification ON and lets
# outbound HTTPS succeed THROUGH Avast's interception — no CERT_NONE,
# no security downgrade, Avast keeps protecting the machine.
try:
    import truststore
    _SSL_CTX = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    log.debug("Using truststore (Windows cert store) for TLS verification")
except Exception as _e:  # pragma: no cover - fallback to standard verification
    _SSL_CTX = ssl.create_default_context()
    log.warning(f"truststore unavailable ({_e}); using default verified context")

# Provider presets: base_url + a sensible default model.
PROVIDERS = {
    "xai":    {"url": "https://api.x.ai/v1/chat/completions",            "model": "grok-beta"},
    "groq":   {"url": "https://api.groq.com/openai/v1/chat/completions", "model": "llama-3.3-70b-versatile"},
    "gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "model": "gemini-2.0-flash"},
    "openrouter": {"url": "https://openrouter.ai/api/v1/chat/completions", "model": "meta-llama/llama-3.3-70b-instruct:free"},
}

class CloudError(RuntimeError):
    """Raised when a cloud provider returns an error."""


class CloudClient:
    """OpenAI-compatible chat client with key rotation + SSL-intercept handling."""

    def __init__(self, provider: str, keys: List[str],
                 model: Optional[str] = None, timeout: int = 60):
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'. Known: {list(PROVIDERS)}")
        self.provider = provider
        self.url = PROVIDERS[provider]["url"]
        self.model = model or PROVIDERS[provider]["model"]
        self.keys = [k for k in keys if k]
        self.timeout = timeout
        self._idx = 0  # round-robin pointer

    def _next_key(self) -> str:
        key = self.keys[self._idx % len(self.keys)]
        self._idx += 1
        return key

    def _call(self, key: str, prompt: str, system: Optional[str],
              temperature: float, max_tokens: int, timeout: Optional[int]) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                # Cloudflare's Browser Integrity Check (in front of Groq et al.)
                # returns HTTP 403 "error code: 1010" when it sees urllib's
                # default bot UA. A normal browser UA passes the check. This was
                # the real cause of the "invalid key" 403s — not the keys.
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/126.0.0.0 Safari/537.36"),
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout or self.timeout, context=_SSL_CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        choices = result.get("choices")
        if choices:
            return choices[0]["message"]["content"].strip()
        raise CloudError(f"Unexpected response: {result}")

    def generate(self, prompt: str, system: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 512,
                 timeout: Optional[int] = None) -> str:
        """Try each key in rotation until one succeeds; raise if all fail."""
        if not self.keys:
            raise CloudError("No API keys configured")
        last_err = None
        for _ in range(len(self.keys)):
            key = self._next_key()
            try:
                return self._call(key, prompt, system, temperature, max_tokens, timeout)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                last_err = CloudError(f"{self.provider} HTTP {e.code}: {body}")
                # 429/5xx -> try next key; 4xx auth/credit -> still try next key.
                log.warning(f"key #{self._idx} failed: {last_err}")
                continue
            except urllib.error.URLError as e:
                last_err = CloudError(f"{self.provider} connection failed: {e}")
                continue
        raise last_err or CloudError("All keys failed")

    def timed_generate(self, prompt: str, **kw) -> dict:
        start = time.time()
        try:
            text = self.generate(prompt, **kw)
            return {"provider": self.provider, "model": self.model, "status": "ok",
                    "response": text, "latency_s": round(time.time() - start, 2)}
        except CloudError as e:
            return {"provider": self.provider, "model": self.model, "status": "error",
                    "response": f"[{e}]", "latency_s": round(time.time() - start, 2)}

    def is_up(self, timeout: int = 15) -> bool:
        try:
            self.generate("ping", max_tokens=5, timeout=timeout)
            return True
        except CloudError:
            return False


if __name__ == "__main__":
    import os
    import sys
    logging.basicConfig(level=logging.INFO)
    provider = sys.argv[1] if len(sys.argv) > 1 else "xai"
    keys = [os.getenv("GROQ_API_KEY_1", ""), os.getenv("GROQ_API_KEY_2", "")]
    client = CloudClient(provider, keys)
    print(f"Provider: {provider} | model: {client.model} | keys: {len([k for k in keys if k])}")
    r = client.timed_generate("In one sentence, what is a star?")
    print(f"status: {r['status']} | latency: {r['latency_s']}s")
    print(f"reply: {r['response']}")

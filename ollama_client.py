#!/usr/bin/env python3
"""
OLLAMA CLIENT - the real execution primitive for Jacky.

A thin, stdlib-only (urllib) HTTP client for a local Ollama server.
No third-party deps so it runs anywhere Python 3.9+ does.

This is the piece that was missing: bot_router decides "ollama_local",
the ensemble picks models, and THIS actually calls them.

Frame: It's Jacky's PC. Local-first, free, no cloud spend.
"""

import json
import time
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

log = logging.getLogger("OllamaClient")

DEFAULT_URL = "http://localhost:11434"
DEFAULT_TIMEOUT = 120  # seconds; local generation can be slow on big models


class OllamaError(RuntimeError):
    """Raised when the Ollama server is unreachable or returns an error."""


class OllamaClient:
    """Minimal HTTP client for a local Ollama server."""

    def __init__(self, base_url: str = DEFAULT_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # low-level transport
    # ------------------------------------------------------------------ #
    def _get(self, path: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise OllamaError(f"GET {path} failed: {e}") from e

    def _post(self, path: str, payload: Dict[str, Any],
              timeout: Optional[int] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise OllamaError(f"POST {path} HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise OllamaError(f"POST {path} failed: {e}") from e

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def is_up(self) -> bool:
        """True if the Ollama server answers /api/tags."""
        try:
            self._get("/api/tags", timeout=5)
            return True
        except OllamaError:
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        """Live list of pulled models: [{name, size_gb, modified}]."""
        data = self._get("/api/tags", timeout=10)
        models = []
        for m in data.get("models", []):
            size = m.get("size", 0)
            models.append({
                "name": m.get("name", "unknown"),
                "size_gb": round(size / (1024 ** 3), 2) if size else 0,
                "modified": m.get("modified_at", ""),
            })
        return models

    def model_names(self) -> List[str]:
        """Just the names of pulled models."""
        return [m["name"] for m in self.list_models()]

    def generate(self, model: str, prompt: str,
                 system: Optional[str] = None,
                 options: Optional[Dict[str, Any]] = None,
                 think: Optional[bool] = None,
                 timeout: Optional[int] = None) -> str:
        """Single-shot completion via /api/generate (non-streaming).

        For "thinking" models (qwen3, deepseek-r1) the visible answer is in
        `response`; if a short num_predict gets consumed by reasoning and
        `response` is empty, we fall back to the `thinking` field so callers
        always get something usable.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options
        if think is not None:
            payload["think"] = think
        data = self._post("/api/generate", payload, timeout=timeout)
        answer = (data.get("response") or "").strip()
        if not answer:
            answer = (data.get("thinking") or "").strip()
        return answer

    def chat(self, model: str, messages: List[Dict[str, str]],
             options: Optional[Dict[str, Any]] = None,
             timeout: Optional[int] = None) -> str:
        """Multi-turn chat via /api/chat (non-streaming).

        messages = [{"role": "user"|"assistant"|"system", "content": "..."}]
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        data = self._post("/api/chat", payload, timeout=timeout)
        return data.get("message", {}).get("content", "").strip()

    def timed_generate(self, model: str, prompt: str, **kw) -> Dict[str, Any]:
        """generate() plus latency + status, for the ensemble/dashboard."""
        start = time.time()
        try:
            text = self.generate(model, prompt, **kw)
            return {
                "model": model,
                "status": "ok",
                "response": text,
                "latency_s": round(time.time() - start, 2),
            }
        except OllamaError as e:
            return {
                "model": model,
                "status": "error",
                "response": f"[error: {e}]",
                "latency_s": round(time.time() - start, 2),
            }


# ---------------------------------------------------------------------- #
# self-test
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = OllamaClient()

    print(f"Ollama up: {client.is_up()}")
    models = client.list_models()
    print(f"Models online ({len(models)}):")
    for m in models:
        print(f"  - {m['name']}  ({m['size_gb']} GB)")

    if models:
        # Prefer the smallest/fastest model for the smoke test.
        smallest = min(models, key=lambda m: m["size_gb"] or 999)["name"]
        print(f"\nSmoke test against {smallest}: 'say hi in 5 words'")
        result = client.timed_generate(smallest, "Say hi in exactly 5 words.")
        print(f"  status : {result['status']}")
        print(f"  latency: {result['latency_s']}s")
        print(f"  reply  : {result['response']}")
    else:
        print("No models pulled yet — run ai_download_queue.cmd first.")

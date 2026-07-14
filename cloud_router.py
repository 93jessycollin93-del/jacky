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
import re
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta, date

from secrets_loader import get_keys  # vault-aware, lazy secret resolution

log = logging.getLogger("CloudRouter")

JACKY_HOME = Path(__file__).parent


def count_tokens(text: str) -> int:
    """Estimate token count. Uses tiktoken if available (accurate for the
    OpenAI-compatible providers this router talks to); otherwise falls back to
    the standard ~4-chars-per-token heuristic. Never raises."""
    if not text:
        return 0
    try:
        import tiktoken
        # cl100k_base is a reasonable cross-provider approximation; we only
        # need it good enough to drive the 80% rotation threshold, not billing.
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4 + 1

# Which key names feed each provider (resolved lazily via secrets_loader,
# which reads the gitignored vault — never slurps real secrets at boot).
PROVIDER_KEYS = {
    "xai":        ["XAI_API_KEY"],
    "groq":       ["GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3"],
    "gemini":     ["GEMINI_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    # Jun 2026 subscriptions
    "vertex_ai":  ["GOOGLE_CLOUD_API_KEY"],   # VERTEX_AI_PROJECT_ID loaded by CloudClient
    "emergent":   ["EMERGENT_API_KEY"],
    "copilot":    ["GITHUB_COPILOT_TOKEN"],
    # Wired but inactive until a key is added to the vault (secrets.env).
    "deepinfra":  ["DEEPINFRA_API_KEY_1", "DEEPINFRA_API_KEY_2"],
    "fireworks":  ["FIREWORKS_API_KEY_1", "FIREWORKS_API_KEY_2"],
    "lambda":     ["LAMBDA_API_KEY_1", "LAMBDA_API_KEY_2"],
    "runpod":     ["RUNPOD_API_KEY_1", "RUNPOD_API_KEY_2"],
}

# Default provider preference per task type.
# Providers listed left-to-right = most preferred first.
# Credit-burn priority layer (CreditBurnPolicy) may re-sort at runtime.
TASK_PROVIDER_ORDER = {
    "code":      ["copilot", "vertex_ai", "xai", "gemini", "groq"],
    "research":  ["vertex_ai", "gemini", "xai", "groq", "copilot"],
    "reasoning": ["vertex_ai", "xai", "gemini", "groq"],
    "general":   ["vertex_ai", "gemini", "groq", "xai"],
}

# Keyword patterns for lightweight task classification (no LLM call).
_TASK_PATTERNS = {
    "code": re.compile(
        r"\b(def |class |import |function|bug|error|exception|test|refactor|"
        r"debug|syntax|compile|lint|snippet|script|module|api endpoint|"
        r"write.*code|fix.*code|implement|algorithm)\b", re.IGNORECASE),
    "research": re.compile(
        r"\b(explain|summarize|summary|what is|what are|find|search|"
        r"history|overview|describe|tell me about|list|examples of)\b", re.IGNORECASE),
    "reasoning": re.compile(
        r"\b(analyze|compare|plan|design|should I|why|trade.?off|"
        r"pros and cons|recommend|evaluate|assess|strategy|decide)\b", re.IGNORECASE),
}


def classify_task(prompt: str) -> str:
    """Classify a prompt into a task type using keyword matching. Never raises."""
    if not prompt:
        return "general"
    for task, pattern in _TASK_PATTERNS.items():
        if pattern.search(prompt):
            return task
    return "general"


class CreditBurnPolicy:
    """Re-orders the provider list to burn expiring credits first,
    without degrading quality for the given task type."""

    # Which task types each provider is considered capable enough for
    # credit-burn prioritization (won't bump to top for tasks not in its set).
    _CAPABLE_FOR = {
        "vertex_ai": {"code", "research", "reasoning", "general"},
        "emergent":  {"research", "general"},
        "copilot":   {"code"},
    }

    def __init__(self, config: dict):
        self.credits = config.get("credits", {})

    def _days_until_expiry(self, provider: str) -> Optional[int]:
        cfg = self.credits.get(provider, {})
        expires_str = cfg.get("expires")
        if not expires_str:
            return None
        try:
            exp = date.fromisoformat(expires_str)
            return (exp - date.today()).days
        except ValueError:
            return None

    def _is_expiring_soon(self, provider: str, threshold_days: int = 90) -> bool:
        days = self._days_until_expiry(provider)
        return days is not None and days <= threshold_days

    def prioritize_expiring(self, order: List[str], task_type: str = "general") -> List[str]:
        """Return a re-sorted copy that puts expiring-credit providers first,
        but only when they're capable for the given task type."""
        expiring = [
            p for p in order
            if self._is_expiring_soon(p)
            and task_type in self._CAPABLE_FOR.get(p, set())
        ]
        rest = [p for p in order if p not in expiring]
        return expiring + rest


class UsageTracker:
    """Tracks token + request usage per provider; persists to disk."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or JACKY_HOME / "data" / "router_usage.json"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.usage = {}
        self.load()

    def load(self):
        """Load usage state from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                    self.usage = data.get("usage", {})
            except Exception as e:
                log.warning(f"Failed to load usage tracker: {e}")

    def save(self):
        """Persist usage state to disk."""
        try:
            with open(self.db_path, 'w') as f:
                json.dump({
                    "usage": self.usage,
                    "last_update": datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            log.warning(f"Failed to save usage tracker: {e}")

    def record(self, provider: str, tokens: int, success: bool = True):
        """Record a request + token usage for a provider."""
        if provider not in self.usage:
            self.usage[provider] = {
                "tokens_used": 0,
                "requests_made": 0,
                "last_reset": datetime.now().isoformat(),
            }
        self.usage[provider]["tokens_used"] += tokens if success else 0
        self.usage[provider]["requests_made"] += 1
        self.save()

    def usage_percent(self, provider: str, max_tokens_per_minute: int) -> float:
        """What percent of the minute limit has this provider used?"""
        if provider not in self.usage:
            return 0.0
        last_reset = datetime.fromisoformat(self.usage[provider]["last_reset"])
        if datetime.now() - last_reset > timedelta(minutes=1):
            self.usage[provider]["tokens_used"] = 0
            self.usage[provider]["requests_made"] = 0
            self.usage[provider]["last_reset"] = datetime.now().isoformat()
            self.save()
            return 0.0
        used = self.usage[provider]["tokens_used"]
        return (used / max_tokens_per_minute * 100) if max_tokens_per_minute > 0 else 0.0

    def get_stats(self, provider: str) -> dict:
        """Return current stats for a provider."""
        return self.usage.get(provider, {
            "tokens_used": 0,
            "requests_made": 0,
            "cost_usd": 0.0,
            "credits_consumed": 0,
            "last_reset": datetime.now().isoformat(),
        })

    def record_cost(self, provider: str, tokens: int, cost_per_token: float,
                    credits: int = 0):
        """Record estimated cost + credits consumed for a request."""
        if provider not in self.usage:
            self.usage[provider] = {
                "tokens_used": 0, "requests_made": 0,
                "cost_usd": 0.0, "credits_consumed": 0,
                "last_reset": datetime.now().isoformat(),
            }
        self.usage[provider].setdefault("cost_usd", 0.0)
        self.usage[provider].setdefault("credits_consumed", 0)
        self.usage[provider]["cost_usd"] += tokens * cost_per_token
        self.usage[provider]["credits_consumed"] += credits
        self.save()

    def credit_burn_rate(self, provider: str) -> dict:
        """Estimate daily burn rate and days remaining for a credited provider."""
        stats = self.usage.get(provider, {})
        first_seen_str = stats.get("first_seen")
        if not first_seen_str:
            return {"daily_tokens": 0, "days_remaining": None}
        try:
            first_seen = datetime.fromisoformat(first_seen_str)
            days_elapsed = max((datetime.now() - first_seen).days, 1)
            total_tokens = stats.get("tokens_used", 0)
            daily = total_tokens / days_elapsed
            return {"daily_tokens": round(daily), "days_elapsed": days_elapsed}
        except Exception:
            return {"daily_tokens": 0, "days_remaining": None}

    def monthly_summary(self, cost_per_token_cfg: dict = None) -> dict:
        """Return a summary of cost + usage per provider for the current month."""
        cpt = cost_per_token_cfg or {}
        summary = {}
        for provider, stats in self.usage.items():
            tokens = stats.get("tokens_used", 0)
            cost = stats.get("cost_usd", tokens * cpt.get(provider, 0.0))
            summary[provider] = {
                "tokens_used": tokens,
                "requests_made": stats.get("requests_made", 0),
                "estimated_cost_usd": round(cost, 6),
                "credits_consumed": stats.get("credits_consumed", 0),
            }
        return summary


class CloudRouter:
    """Try enabled cloud providers in config order; first success wins."""

    def __init__(self):
        self.config = self._load_config()
        self.order = self._provider_order()
        self.tracker = UsageTracker()
        self.credit_policy = CreditBurnPolicy(self.config)
        self.current_provider = self.order[0] if self.order else None

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

    def _should_rotate(self, provider: str) -> bool:
        """Check if provider is at/above 80% of its per-minute limit; if so, rotate."""
        limits = self.config.get("provider_limits", {}).get(provider, {})
        max_tokens = limits.get("max_tokens_per_minute", 60000)
        usage_pct = self.tracker.usage_percent(provider, max_tokens)
        should = usage_pct >= 80.0
        if should:
            log.info(f"Provider {provider} at {usage_pct:.1f}% limit; rotating")
        return should

    def _rotate_to_next(self) -> bool:
        """Rotate to the next available provider in the order."""
        current_idx = self.order.index(self.current_provider) if self.current_provider in self.order else 0
        for i in range(1, len(self.order)):
            next_idx = (current_idx + i) % len(self.order)
            next_provider = self.order[next_idx]
            keys = self._keys_for(next_provider)
            if keys:
                self.current_provider = next_provider
                log.info(f"Rotated to provider: {self.current_provider}")
                return True
        return False

    def available(self) -> List[dict]:
        """Which enabled providers actually have usable keys."""
        out = []
        for p in self.order:
            keys = self._keys_for(p)
            out.append({"provider": p, "has_keys": bool(keys), "key_count": len(keys)})
        return out

    def usage_report(self) -> dict:
        """Current usage + limits for all providers."""
        report = {"current_provider": self.current_provider, "providers": {}}
        for p in self.order:
            limits = self.config.get("provider_limits", {}).get(p, {})
            max_tokens = limits.get("max_tokens_per_minute", 60000)
            usage_pct = self.tracker.usage_percent(p, max_tokens)
            stats = self.tracker.get_stats(p)
            report["providers"][p] = {
                "usage_percent": f"{usage_pct:.1f}%",
                "tokens_used": stats.get("tokens_used", 0),
                "requests_made": stats.get("requests_made", 0),
                "max_tokens_per_minute": max_tokens,
            }
        return report

    def _task_ordered_providers(self, task_type: str) -> List[str]:
        """Return the provider list for this task type, filtered to enabled+keyed
        providers, then re-sorted for credit-burn priority."""
        # Start from TASK_PROVIDER_ORDER; fall back to config order.
        preferred = TASK_PROVIDER_ORDER.get(task_type, self.order)
        # Only keep providers that are enabled (in config order).
        enabled = set(self.order)
        ordered = [p for p in preferred if p in enabled]
        # Add any enabled providers not in the task-specific list (as fallbacks).
        for p in self.order:
            if p not in ordered:
                ordered.append(p)
        # Apply credit-burn priority: bump expiring-credit providers to the front.
        return self.credit_policy.prioritize_expiring(ordered, task_type)

    def ask(self, prompt: str, system: Optional[str] = None,
            max_tokens: int = 512, task_type: Optional[str] = None) -> dict:
        """Route prompt to best provider. task_type overrides auto-classification."""
        from cloud_client import CloudClient, CloudError  # local import; SSL via truststore

        if task_type is None:
            task_type = classify_task(prompt)

        order = self._task_ordered_providers(task_type)
        cost_per_token_cfg = self.config.get("cost_per_token", {})

        tried = []
        for provider in order:
            if self._should_rotate(provider):
                tried.append({"provider": provider, "skipped": "at limit"})
                continue

            keys = self._keys_for(provider)
            if not keys:
                tried.append({"provider": provider, "skipped": "no keys"})
                continue

            try:
                client = CloudClient(provider, keys)
                result = client.timed_generate(prompt, system=system, max_tokens=max_tokens)
                if result.get("status") == "ok":
                    tokens = count_tokens(prompt) + count_tokens(result.get("response", ""))
                    self.tracker.record(provider, tokens, success=True)
                    cost_per_tok = cost_per_token_cfg.get(provider, 0.0)
                    self.tracker.record_cost(provider, tokens, cost_per_tok)
                    self.current_provider = provider
                    result["tried"] = tried
                    result["task_type"] = task_type
                    result["routing_reason"] = (
                        f"task={task_type}; credit-priority={provider in [p for p in order[:2]]}"
                    )
                    return result
                tried.append({"provider": provider, "error": result.get("response")})
            except Exception as e:
                tried.append({"provider": provider, "error": str(e)})

        return {"status": "error", "engine": "cloud", "tried": tried,
                "task_type": task_type,
                "response": "All enabled cloud providers failed or have no keys."}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = CloudRouter()
    print("Enabled provider order:", r.order)
    print(f"Current provider: {r.current_provider}")
    print("\nAvailability:")
    for a in r.available():
        print(f"  {a['provider']}: keys={a['key_count']}")
    print("\nProvider Limits & Usage:")
    report = r.usage_report()
    for provider, stats in report["providers"].items():
        print(f"  {provider}: {stats['usage_percent']} used ({stats['tokens_used']} tokens)")
    print(f"\nCurrent: {report['current_provider']}")

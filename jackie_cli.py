#!/usr/bin/env python3
"""
jackie_cli.py — command-line interface for the Jackie AI router.

Usage:
  python jackie_cli.py status              # active provider + usage %
  python jackie_cli.py costs               # spend per provider, credit burn rate
  python jackie_cli.py ask "prompt"        # route query, show provider + reply
  python jackie_cli.py ask --task code "prompt"  # force task type
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

JACKY_HOME = Path(__file__).parent


def _load_config() -> dict:
    try:
        with open(JACKY_HOME / "config.json") as f:
            return json.load(f)
    except Exception:
        return {}


def cmd_status(args):
    from cloud_router import CloudRouter
    router = CloudRouter()
    report = router.usage_report()

    print(f"Active provider : {report['current_provider']}")
    print(f"Provider order  : {', '.join(router.order)}")
    print()
    print(f"{'Provider':<14} {'Usage %':<10} {'Tokens used':<14} {'Requests'}")
    print("-" * 52)
    for provider, stats in report["providers"].items():
        print(
            f"{provider:<14} {stats['usage_percent']:<10} "
            f"{stats['tokens_used']:<14} {stats['requests_made']}"
        )

    avail = router.available()
    keyed = [a["provider"] for a in avail if a["has_keys"]]
    missing = [a["provider"] for a in avail if not a["has_keys"]]
    print()
    print(f"Keyed providers : {', '.join(keyed) or 'none'}")
    if missing:
        print(f"No keys         : {', '.join(missing)}")


def cmd_costs(args):
    from cloud_router import UsageTracker
    config = _load_config()
    cost_cfg = config.get("cost_per_token", {})
    credits_cfg = config.get("credits", {})

    tracker = UsageTracker()
    summary = tracker.monthly_summary(cost_cfg)

    print(f"{'Provider':<14} {'Tokens':<12} {'Requests':<12} {'Cost (USD)':<14} {'Credits'}")
    print("-" * 62)
    for provider, s in summary.items():
        cost = f"${s['estimated_cost_usd']:.6f}"
        credits = s["credits_consumed"] or "-"
        print(f"{provider:<14} {s['tokens_used']:<12} {s['requests_made']:<12} {cost:<14} {credits}")

    print()
    for provider, cfg in credits_cfg.items():
        expires = cfg.get("expires")
        balance = cfg.get("balance_usd") or cfg.get("balance_credits")
        currency = cfg.get("currency", "USD")
        unit = "credits" if cfg.get("balance_credits") else currency
        burn = tracker.credit_burn_rate(provider)

        if expires:
            days_left = (date.fromisoformat(expires) - date.today()).days
            print(f"{provider}: {balance} {unit} | expires {expires} ({days_left}d)")
        else:
            reset = cfg.get("reset", "unknown")
            print(f"{provider}: {balance} {unit} | resets {reset}")

        if burn.get("daily_tokens"):
            print(f"  burn rate: {burn['daily_tokens']:,} tokens/day "
                  f"(over {burn.get('days_elapsed', '?')} days)")


def cmd_ask(args):
    from cloud_router import CloudRouter
    router = CloudRouter()

    prompt = args.prompt
    task_type = args.task or None

    print(f"Routing: {'auto-classify' if not task_type else f'forced task={task_type}'}")
    result = router.ask(prompt, task_type=task_type, max_tokens=args.max_tokens)

    print(f"Provider  : {result.get('provider', 'unknown')} ({result.get('model', '')})")
    print(f"Task type : {result.get('task_type', '?')}")
    print(f"Latency   : {result.get('latency_s', '?')}s")
    print(f"Routing   : {result.get('routing_reason', '')}")
    status = result.get("status")
    if status != "ok":
        tried = result.get("tried", [])
        if tried:
            print(f"Tried     : {tried}")
    print()
    print(result.get("response", "[no response]"))


def main():
    parser = argparse.ArgumentParser(
        prog="jackie",
        description="Jackie AI router CLI",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show active provider and usage stats")
    sub.add_parser("costs", help="Show cost and credit burn per provider")

    ask_p = sub.add_parser("ask", help="Route a prompt through the cloud router")
    ask_p.add_argument("prompt", help="The prompt to send")
    ask_p.add_argument("--task", choices=["code", "research", "reasoning", "general"],
                       help="Force a task type (skips auto-classify)")
    ask_p.add_argument("--max-tokens", type=int, default=512,
                       dest="max_tokens", help="Max tokens in response (default: 512)")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "costs":
        cmd_costs(args)
    elif args.command == "ask":
        cmd_ask(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

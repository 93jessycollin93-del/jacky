"""
squad_manager.py — Bot config loader and memory injection for Jacky's AI squads.

Loads bot definitions from bots/*.json, builds system prompts with personal
memory context, and provides squad routing helpers used by jacky_api.py.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("SquadManager")

JACKY_HOME = Path(__file__).parent
BOTS_DIR = JACKY_HOME / "bots"
MEMORY_DIR = Path(r"C:\Users\93jes\.claude\projects\C--Users-93jes\memory")
ARCHIVE_DIR = JACKY_HOME / "data"

# Which bots lead each squad (single primary responder)
SQUAD_LEADS = {
    "coding":    "lead",
    "security":  "monitor",
    "archivist": "collector",
}

# Squad membership order (lead first)
SQUAD_ROSTER = {
    "coding":    ["lead", "architect", "impl", "reviewer", "claude_jr"],
    "security":  ["monitor", "analyst"],
    "archivist": ["collector", "organizer", "retriever"],
}


class BotConfig:
    def __init__(self, data: dict):
        self.id                 = data["id"]
        self.name               = data["name"]
        self.squad              = data["squad"]
        self.role               = data.get("role", "specialist")
        self.primary_focus      = data.get("primary_focus", "")
        self.secondary_focus    = data.get("secondary_focus", "")
        self.system_prompt_prefix = data.get("system_prompt_prefix", "")
        self.model_preference   = data.get("model_preference", "auto")
        self.memory_enabled     = data.get("memory_enabled", True)
        self.memory_max_snippets = data.get("memory_max_snippets", 3)
        self.active             = data.get("active", True)
        self.color              = data.get("color", "#00d4ff")
        self.cloud_fallback     = data.get("cloud_fallback", False)
        self.claude_code_capable = data.get("claude_code_capable", False)

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "name":          self.name,
            "squad":         self.squad,
            "role":          self.role,
            "primary_focus": self.primary_focus,
            "model_preference": self.model_preference,
            "active":        self.active,
            "color":         self.color,
            "cloud_fallback": self.cloud_fallback,
            "claude_code_capable": self.claude_code_capable,
        }


class SquadManager:
    def __init__(self):
        self._bots: dict[str, BotConfig] = {}
        self._memory_cache: Optional[str] = None
        self.load_bots()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_bots(self):
        """Read all bots/*.json and register them."""
        if not BOTS_DIR.exists():
            log.warning(f"bots/ directory not found at {BOTS_DIR}")
            return
        loaded = 0
        for path in BOTS_DIR.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                bot = BotConfig(data)
                self._bots[bot.id] = bot
                loaded += 1
            except Exception as e:
                log.warning(f"Failed to load bot config {path.name}: {e}")
        log.info(f"SquadManager: loaded {loaded} bots from {BOTS_DIR}")

    def reload(self):
        """Hot-reload bot configs without restarting the server."""
        self._bots.clear()
        self.load_bots()

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_bot(self, bot_id: str) -> Optional[BotConfig]:
        return self._bots.get(bot_id)

    def get_squad(self, squad: str) -> list[BotConfig]:
        """Return ordered bot list for a squad (lead first)."""
        order = SQUAD_ROSTER.get(squad, [])
        bots = [self._bots[bid] for bid in order if bid in self._bots]
        if not bots:
            # Fallback: any active bot in this squad
            bots = [b for b in self._bots.values()
                    if b.squad == squad and b.active]
        return bots

    def get_lead(self, squad: str) -> Optional[BotConfig]:
        lead_id = SQUAD_LEADS.get(squad)
        return self._bots.get(lead_id) if lead_id else None

    def all_squads(self) -> dict:
        """Return squad metadata for /api/squads."""
        result = {}
        for squad, roster in SQUAD_ROSTER.items():
            bots_data = []
            for bid in roster:
                bot = self._bots.get(bid)
                if bot:
                    bots_data.append(bot.to_dict())
            result[squad] = {
                "lead": SQUAD_LEADS.get(squad),
                "bots": bots_data,
                "count": len(bots_data),
            }
        return result

    def all_bots(self) -> list[dict]:
        return [b.to_dict() for b in self._bots.values()]

    # ------------------------------------------------------------------
    # Memory injection
    # ------------------------------------------------------------------

    def _load_memory_index(self) -> str:
        """Read the MEMORY.md index (the 200-line pointer file)."""
        try:
            index_path = MEMORY_DIR / "MEMORY.md"
            if index_path.exists():
                return index_path.read_text(encoding="utf-8")
        except Exception as e:
            log.warning(f"Could not read MEMORY.md: {e}")
        return ""

    def _find_relevant_snippets(self, prompt: str, max_snippets: int) -> list[str]:
        """
        Find relevant context snippets using RAG (if available) or keyword search.
        RAG uses semantic similarity on the vector index for better relevance.
        Keyword search falls back if RAG unavailable.
        """
        # Try RAG first
        try:
            from rag_retriever import query_rag
            chunks = query_rag(prompt, top_k=max_snippets)
            if chunks:
                return [f"[{c['source_file']}] {c['text'][:300]}" for c in chunks]
        except Exception as e:
            log.debug(f"RAG retrieval failed: {e}; falling back to keyword search")

        # Fallback: keyword-based search (original implementation)
        if not MEMORY_DIR.exists():
            return []

        prompt_words = set(w.lower() for w in prompt.split() if len(w) > 3)
        scored: list[tuple[int, str]] = []

        for path in MEMORY_DIR.glob("*.md"):
            if path.name == "MEMORY.md":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                lines = text.splitlines()
                # Score = number of prompt words found in this file
                score = sum(1 for w in prompt_words if w in text.lower())
                if score > 0:
                    # Extract the body (skip frontmatter)
                    body_lines = []
                    in_front = False
                    for i, line in enumerate(lines):
                        if i == 0 and line.strip() == "---":
                            in_front = True
                            continue
                        if in_front and line.strip() == "---":
                            in_front = False
                            continue
                        if not in_front:
                            body_lines.append(line)
                    body = "\n".join(body_lines[:10]).strip()
                    if body:
                        scored.append((score, f"[{path.stem}] {body[:300]}"))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_snippets]]

    def build_system_prompt(self, bot: BotConfig, prompt: str) -> str:
        """
        Assemble the full system prompt for a bot:
          1. Bot's own personality prefix
          2. Memory context (if enabled and relevant snippets found)
        """
        parts = [bot.system_prompt_prefix]

        if bot.memory_enabled and prompt:
            snippets = self._find_relevant_snippets(prompt, bot.memory_max_snippets)
            if snippets:
                mem_block = "\n\n--- RELEVANT MEMORY CONTEXT ---\n"
                mem_block += "\n\n".join(snippets)
                mem_block += "\n--- END MEMORY CONTEXT ---"
                parts.append(mem_block)

        return "\n".join(parts)


# Module-level singleton — imported by jacky_api.py
squad_manager = SquadManager()

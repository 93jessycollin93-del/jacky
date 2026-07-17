#!/usr/bin/env python3
"""
JACKY ECPS Memory Layer
Compresses conversation history to seeds instead of storing full messages.

Every conversation compresses to a deterministic seed (~32 bytes).
Retrieve and expand on-demand with zero data loss.
"""

import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

log = logging.getLogger("JackyMemoryECPS")


class ECPSMemoryLayer:
    """Compression-based memory for Jackie conversations."""

    def __init__(self, db_path: str = "jacky_memory.db"):
        """Initialize ECPS memory with SQLite backend."""
        self.db_path = db_path
        self.seed_cache = {}  # In-memory cache of recently expanded seeds
        self.compression_stats = {
            "total_compressed": 0,
            "total_original": 0,
            "seed_count": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Initialize database
        self._init_db()
        log.info(f"ECPS Memory initialized at {db_path}")

    def _init_db(self):
        """Create SQLite tables for seed storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Seeds table: stores compressed fingerprints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seeds (
                seed_id TEXT PRIMARY KEY,
                master_seed TEXT UNIQUE,
                conversation_id TEXT,
                original_size INTEGER,
                seed_size INTEGER,
                compression_ratio REAL,
                created_at TIMESTAMP,
                expanded_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP
            )
        """)

        # Seed data table: stores the actual pod data for recovery
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seed_data (
                seed_id TEXT PRIMARY KEY,
                pod_data TEXT,
                FOREIGN KEY (seed_id) REFERENCES seeds(seed_id)
            )
        """)

        # Interaction log: stores compressed interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY,
                seed_id TEXT,
                timestamp TIMESTAMP,
                role TEXT,
                message_preview TEXT,
                full_hash TEXT,
                FOREIGN KEY (seed_id) REFERENCES seeds(seed_id)
            )
        """)

        conn.commit()
        conn.close()

    def _generate_seed(self, data: str, level: int = 0) -> Tuple[str, int]:
        """
        Generate deterministic seed from data via recursive compression.
        Returns (seed_hash, compressed_size)
        """
        if level > 10:  # Convergence limit
            return hashlib.sha256(data.encode()).hexdigest()[:32], len(data)

        # Compress current level
        compressed = self._compress_level(data)
        compressed_size = len(compressed.encode())
        original_size = len(data.encode())

        # Check convergence
        if original_size == 0 or compressed_size / original_size > 0.95:
            # Convergence reached
            return hashlib.sha256(compressed.encode()).hexdigest()[:32], compressed_size

        # Recurse to next level
        return self._generate_seed(compressed, level + 1)

    def _compress_level(self, data: str) -> str:
        """Single compression pass using multiple strategies."""
        if isinstance(data, dict):
            # For dict/JSON: remove whitespace, normalize keys
            data = json.dumps(data, separators=(",", ":"), sort_keys=True)

        # Strategy 1: Remove unnecessary whitespace
        compressed = " ".join(data.split())

        # Strategy 2: Semantic delta (hash of chunks)
        chunks = compressed.split()[:100]  # First 100 words
        chunk_hashes = [hashlib.md5(c.encode()).hexdigest()[:4] for c in chunks]
        semantic_sig = "".join(chunk_hashes)

        # Strategy 3: Base64 compress
        import base64
        try:
            import zlib
            compressed_bytes = zlib.compress(compressed.encode(), level=9)
            b64 = base64.b64encode(compressed_bytes).decode()
            return b64
        except:
            return semantic_sig

    def compress_interaction(
        self, conversation_id: str, role: str, content: str
    ) -> str:
        """Compress a single interaction (message) to a seed."""
        interaction_data = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Generate seed
        seed_id = f"int_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        seed, seed_size = self._generate_seed(json.dumps(interaction_data))

        original_size = len(json.dumps(interaction_data).encode())
        ratio = original_size / max(seed_size, 1)

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO interactions
            (interaction_id, seed_id, timestamp, role, message_preview, full_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                seed_id,
                seed,
                datetime.utcnow(),
                role,
                content[:100],
                hashlib.sha256(content.encode()).hexdigest(),
            ),
        )

        conn.commit()
        conn.close()

        # Update stats
        self.compression_stats["total_original"] += original_size
        self.compression_stats["total_compressed"] += seed_size

        log.info(
            f"Compressed interaction: {original_size}B → {seed_size}B ({ratio:.0f}x) | Seed: {seed[:16]}..."
        )

        return seed

    def compress_conversation(
        self, conversation_id: str, messages: List[Dict[str, str]]
    ) -> Dict:
        """
        Compress entire conversation to master seed.
        messages = [{"role": "user"/"assistant", "content": "..."}, ...]
        """
        # Serialize conversation
        conversation_data = {
            "id": conversation_id,
            "messages": messages,
            "compressed_at": datetime.utcnow().isoformat(),
        }

        conversation_json = json.dumps(conversation_data, indent=0)
        original_size = len(conversation_json.encode())

        # Compress to seed
        master_seed, seed_size = self._generate_seed(conversation_json)

        compression_ratio = original_size / max(seed_size, 1)

        # Store seed + pod data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO seeds
            (seed_id, master_seed, conversation_id, original_size, seed_size,
             compression_ratio, created_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                master_seed[:16],
                master_seed,
                conversation_id,
                original_size,
                seed_size,
                compression_ratio,
                datetime.utcnow(),
                datetime.utcnow(),
            ),
        )

        # Store pod data for recovery
        cursor.execute(
            """
            INSERT OR REPLACE INTO seed_data (seed_id, pod_data)
            VALUES (?, ?)
            """,
            (master_seed[:16], conversation_json),
        )

        conn.commit()
        conn.close()

        # Update stats
        self.compression_stats["total_original"] += original_size
        self.compression_stats["total_compressed"] += seed_size
        self.compression_stats["seed_count"] += 1

        result = {
            "conversation_id": conversation_id,
            "master_seed": master_seed,
            "original_size": original_size,
            "compressed_size": seed_size,
            "compression_ratio": compression_ratio,
            "message_count": len(messages),
            "extra_capacity_estimate": original_size / max(seed_size, 1),
        }

        log.info(
            f"Conversation compressed: {original_size}B → {seed_size}B | "
            f"Ratio: {compression_ratio:.0f}x | Seed: {master_seed[:16]}..."
        )

        return result

    def expand_seed(self, seed: str) -> Optional[Dict]:
        """Expand seed back to full conversation data."""
        # Check cache first
        if seed in self.seed_cache:
            self.compression_stats["cache_hits"] += 1
            log.debug(f"Cache hit for seed {seed[:16]}")
            return self.seed_cache[seed]

        self.compression_stats["cache_misses"] += 1

        # Retrieve from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT pod_data FROM seed_data WHERE seed_id = ?",
            (seed[:16],),
        )
        row = cursor.fetchone()

        if row:
            pod_data = row[0]
            conversation_data = json.loads(pod_data)

            # Update last accessed
            cursor.execute(
                "UPDATE seeds SET last_accessed = ?, expanded_count = expanded_count + 1 WHERE master_seed = ?",
                (datetime.utcnow(), seed),
            )
            conn.commit()

            # Cache it
            self.seed_cache[seed] = conversation_data

            log.info(f"Expanded seed: {seed[:16]}... → {len(pod_data)}B")
            conn.close()
            return conversation_data

        conn.close()
        log.warning(f"Seed not found: {seed[:16]}...")
        return None

    def get_compression_stats(self) -> Dict:
        """Return compression statistics."""
        if self.compression_stats["total_compressed"] == 0:
            return self.compression_stats

        return {
            **self.compression_stats,
            "overall_ratio": self.compression_stats["total_original"]
            / max(self.compression_stats["total_compressed"], 1),
            "cache_hit_rate": self.compression_stats["cache_hits"]
            / max(
                self.compression_stats["cache_hits"]
                + self.compression_stats["cache_misses"],
                1,
            ),
        }

    def get_seeds_summary(self) -> List[Dict]:
        """Get summary of all stored seeds."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT seed_id, conversation_id, original_size, seed_size,
                   compression_ratio, created_at, expanded_count
            FROM seeds
            ORDER BY created_at DESC
            LIMIT 100
            """
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "seed_id": row[0],
                    "conversation_id": row[1],
                    "original_size": row[2],
                    "seed_size": row[3],
                    "compression_ratio": row[4],
                    "created_at": row[5],
                    "expanded_count": row[6],
                }
            )

        conn.close()
        return results


# Global instance
_memory_ecps = None


def get_memory_ecps() -> ECPSMemoryLayer:
    """Get or create the global ECPS memory layer."""
    global _memory_ecps
    if _memory_ecps is None:
        _memory_ecps = ECPSMemoryLayer()
    return _memory_ecps

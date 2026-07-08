#!/usr/bin/env python3
"""
Jackie Pod Activity Logger
Records every pod compression event with timestamp, type, and results.
The log itself gets compressed with ECPS (recursive compression).
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class PodActivityLogger:
    """Log pod compression/expansion events with semantic color states."""

    # Color codes representing pod states (meaningful, not decorative)
    STATE_COLORS = {
        "created": "#4A90E2",      # Blue: pod created, neutral
        "compressing": "#F5A623",  # Orange: compression in progress
        "compressed": "#7ED321",   # Green: compression succeeded
        "expanding": "#BD10E0",    # Purple: expansion in progress
        "expanded": "#7ED321",     # Green: expansion succeeded
        "cached": "#50E3C2",       # Teal: served from cache
        "archived": "#417505",     # Dark green: moved to archive
        "error": "#D0021B",        # Red: error state
    }

    def __init__(self, db_path: str = "jacky_pod_activity.db"):
        """Initialize pod activity logger."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create SQLite tables for pod activity log."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pod_events (
                event_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                pod_id TEXT,
                pod_type TEXT,  -- "memory", "model", "cache", etc.
                event_type TEXT,  -- "compress", "expand", "cache_hit", etc.
                state TEXT,  -- "compressing", "compressed", "expanding", etc.
                color TEXT,  -- semantic color representing state
                original_size_bytes INTEGER,
                compressed_size_bytes INTEGER,
                compression_ratio REAL,
                duration_ms INTEGER,
                details TEXT  -- JSON with additional context
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pod_archive (
                archive_id TEXT PRIMARY KEY,
                created_at TIMESTAMP,
                event_count INTEGER,
                original_size_bytes INTEGER,
                archive_size_bytes INTEGER,
                compression_ratio REAL,
                archive_seed TEXT,  -- ECPS seed representing entire archive
                events_json TEXT  -- Serialized events (can be expanded from seed)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pod_events_timestamp
            ON pod_events(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pod_events_pod_id
            ON pod_events(pod_id)
        """)

        conn.commit()
        conn.close()

    def log_pod_event(
        self,
        pod_id: str,
        pod_type: str,
        event_type: str,
        state: str,
        original_size: int = 0,
        compressed_size: int = 0,
        duration_ms: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a pod event."""
        if state not in self.STATE_COLORS:
            state = "created"

        color = self.STATE_COLORS[state]
        compression_ratio = (
            original_size / compressed_size
            if compressed_size > 0 and original_size > 0
            else 0
        )

        event_id = f"{pod_id}_{event_type}_{int(datetime.utcnow().timestamp() * 1000)}"
        timestamp = datetime.utcnow()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO pod_events
            (event_id, timestamp, pod_id, pod_type, event_type, state, color,
             original_size_bytes, compressed_size_bytes, compression_ratio,
             duration_ms, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                timestamp,
                pod_id,
                pod_type,
                event_type,
                state,
                color,
                original_size,
                compressed_size,
                compression_ratio,
                duration_ms,
                json.dumps(details or {}),
            ),
        )

        conn.commit()
        conn.close()

        return event_id

    def get_pod_timeline(self, pod_id: str, limit: int = 50) -> List[Dict]:
        """Get activity timeline for a specific pod."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT event_id, timestamp, event_type, state, color,
                   original_size_bytes, compressed_size_bytes, compression_ratio,
                   duration_ms
            FROM pod_events
            WHERE pod_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (pod_id, limit),
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "event_id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "state": row[3],
                    "color": row[4],
                    "original_size": row[5],
                    "compressed_size": row[6],
                    "compression_ratio": row[7],
                    "duration_ms": row[8],
                }
            )

        conn.close()
        return results

    def get_all_events(self, limit: int = 100, offset: int = 0) -> Dict:
        """Get all pod events (paginated)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) FROM pod_events")
        total = cursor.fetchone()[0]

        # Fetch page
        cursor.execute(
            """
            SELECT event_id, timestamp, pod_id, pod_type, event_type, state, color,
                   original_size_bytes, compressed_size_bytes, compression_ratio,
                   duration_ms
            FROM pod_events
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

        events = []
        for row in cursor.fetchall():
            events.append(
                {
                    "event_id": row[0],
                    "timestamp": row[1],
                    "pod_id": row[2],
                    "pod_type": row[3],
                    "event_type": row[4],
                    "state": row[5],
                    "color": row[6],
                    "original_size": row[7],
                    "compressed_size": row[8],
                    "compression_ratio": row[9],
                    "duration_ms": row[10],
                }
            )

        conn.close()
        return {"total": total, "events": events, "limit": limit, "offset": offset}

    def get_pod_stats(self, pod_id: Optional[str] = None) -> Dict:
        """Get statistics for pod(s)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if pod_id:
            cursor.execute(
                """
                SELECT COUNT(*) as event_count,
                       SUM(original_size_bytes) as total_original,
                       SUM(compressed_size_bytes) as total_compressed,
                       AVG(duration_ms) as avg_duration,
                       MIN(duration_ms) as min_duration,
                       MAX(duration_ms) as max_duration
                FROM pod_events
                WHERE pod_id = ?
                """,
                (pod_id,),
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*) as event_count,
                       SUM(original_size_bytes) as total_original,
                       SUM(compressed_size_bytes) as total_compressed,
                       AVG(duration_ms) as avg_duration,
                       MIN(duration_ms) as min_duration,
                       MAX(duration_ms) as max_duration
                FROM pod_events
                """
            )

        row = cursor.fetchone()
        conn.close()

        return {
            "event_count": row[0] or 0,
            "total_original_bytes": row[1] or 0,
            "total_compressed_bytes": row[2] or 0,
            "avg_duration_ms": round(row[3] or 0, 1),
            "min_duration_ms": row[4] or 0,
            "max_duration_ms": row[5] or 0,
            "overall_ratio": (row[1] or 1) / max(row[2] or 1, 1),
        }

    def create_archive(self, archive_seed: str = None) -> str:
        """Archive all current events and compress the archive with ECPS."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all events
        cursor.execute(
            """
            SELECT event_id, timestamp, pod_id, pod_type, event_type, state,
                   original_size_bytes, compressed_size_bytes
            FROM pod_events
            ORDER BY timestamp
            """
        )

        events = []
        total_original = 0
        for row in cursor.fetchall():
            events.append(
                {
                    "event_id": row[0],
                    "timestamp": row[1],
                    "pod_id": row[2],
                    "pod_type": row[3],
                    "event_type": row[4],
                    "state": row[5],
                    "original_size": row[6],
                    "compressed_size": row[7],
                }
            )
            total_original += row[6]

        events_json = json.dumps(events)
        archive_size = len(events_json.encode())

        archive_id = f"archive_{int(datetime.utcnow().timestamp())}"

        cursor.execute(
            """
            INSERT INTO pod_archive
            (archive_id, created_at, event_count, original_size_bytes,
             archive_size_bytes, compression_ratio, archive_seed, events_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                archive_id,
                datetime.utcnow(),
                len(events),
                total_original,
                archive_size,
                total_original / max(archive_size, 1),
                archive_seed or "pending",
                events_json,
            ),
        )

        conn.commit()
        conn.close()

        return archive_id

    def get_archives(self, limit: int = 10) -> List[Dict]:
        """List all archives."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT archive_id, created_at, event_count, original_size_bytes,
                   archive_size_bytes, compression_ratio, archive_seed
            FROM pod_archive
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        archives = []
        for row in cursor.fetchall():
            archives.append(
                {
                    "archive_id": row[0],
                    "created_at": row[1],
                    "event_count": row[2],
                    "original_size": row[3],
                    "archive_size": row[4],
                    "compression_ratio": row[5],
                    "archive_seed": row[6],
                }
            )

        conn.close()
        return archives

    def get_archive_details(self, archive_id: str) -> Optional[Dict]:
        """Get full archive details with all events."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT archive_id, created_at, event_count, original_size_bytes,
                   archive_size_bytes, compression_ratio, events_json
            FROM pod_archive
            WHERE archive_id = ?
            """,
            (archive_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "archive_id": row[0],
            "created_at": row[1],
            "event_count": row[2],
            "original_size": row[3],
            "archive_size": row[4],
            "compression_ratio": row[5],
            "events": json.loads(row[6]),
        }


# ============================================================================
# DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    import tempfile
    import os

    # Use a temp file for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = temp_db.name
    temp_db.close()

    logger = PodActivityLogger(temp_path)

    # Simulate pod activity
    print("📝 Logging pod activity events...\n")

    logger.log_pod_event(
        pod_id="memory_conv_001",
        pod_type="memory",
        event_type="compress_conversation",
        state="compressed",
        original_size=1770,
        compressed_size=1280,
        duration_ms=12,
        details={"message_count": 8, "conversation_id": "nvidia-opt-2025"},
    )

    logger.log_pod_event(
        pod_id="memory_conv_001",
        pod_type="memory",
        event_type="cache_hit",
        state="cached",
        original_size=1280,
        compressed_size=32,
        duration_ms=2,
        details={"served_from": "L1_cache"},
    )

    logger.log_pod_event(
        pod_id="model_7b_int4",
        pod_type="model",
        event_type="compress_weights",
        state="compressed",
        original_size=14000000000,
        compressed_size=3500000000,
        duration_ms=2500,
        details={"quantization": "int4", "layers": 32},
    )

    # Get timeline for first pod
    print("📊 Pod Activity Timeline (memory_conv_001):")
    print("-" * 60)
    timeline = logger.get_pod_timeline("memory_conv_001")
    for event in timeline:
        state_color = event["color"]
        print(f"  [{event['state']:12}] {event['event_type']:20} | "
              f"{event['compression_ratio']:.1f}x | "
              f"{event['duration_ms']:4}ms | Color: {state_color}")

    # Get all events
    print("\n📈 All Pod Events:")
    print("-" * 60)
    all_events = logger.get_all_events(limit=5)
    for event in all_events["events"]:
        print(f"  {event['pod_id']:20} | {event['state']:12} | "
              f"{event['compression_ratio']:.1f}x | {event['event_type']}")

    # Get stats
    print("\n📊 Statistics:")
    print("-" * 60)
    stats = logger.get_pod_stats()
    print(f"  Total events: {stats['event_count']}")
    print(f"  Original bytes: {stats['total_original_bytes']:,}")
    print(f"  Compressed bytes: {stats['total_compressed_bytes']:,}")
    print(f"  Overall ratio: {stats['overall_ratio']:.1f}x")
    print(f"  Avg duration: {stats['avg_duration_ms']}ms")

    # Create archive
    print("\n📦 Creating archive...")
    print("-" * 60)
    archive_id = logger.create_archive()
    print(f"  Archive ID: {archive_id}")

    archives = logger.get_archives()
    for archive in archives:
        print(f"  • {archive['archive_id']}: {archive['event_count']} events, "
              f"{archive['compression_ratio']:.1f}x ratio")

    # Cleanup
    os.unlink(temp_path)

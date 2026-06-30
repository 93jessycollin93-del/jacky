#!/usr/bin/env python3
"""
Build Vector Index: Load embeddings.jsonl, create sqlite-vec index.
Output: jacky_knowledge.db (vector index + metadata).
"""
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("VectorIndexBuilder")

# Configuration
DATA_DIR = Path("E:/AI/Jacky/data")
EMBEDDINGS_FILE = DATA_DIR / "embeddings.jsonl"
INDEX_DB = DATA_DIR / "jacky_knowledge.db"
EMBEDDING_DIM = 384                           # all-minilm-l6-v2 output dimension

def load_embeddings(path: Path) -> List[Dict]:
    """Load embeddings from JSONL."""
    embeddings = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if line.strip():
                embeddings.append(json.loads(line))
                if (i + 1) % 1000 == 0:
                    log.info(f"Loaded {i + 1} embeddings...")
    log.info(f"Total loaded: {len(embeddings)} embeddings")
    return embeddings

def create_index_sqlite_vec(embeddings: List[Dict], db_path: Path):
    """Create sqlite-vec vector index."""
    try:
        import sqlite_vec
    except ImportError:
        log.error("sqlite-vec not installed. Run: pip install sqlite-vec")
        log.info("Fallback: using simple sqlite3 with BLOB storage (slower search)")
        create_index_simple_sqlite(embeddings, db_path)
        return

    log.info(f"Creating sqlite-vec index at {db_path}")
    db = sqlite_vec.connect(str(db_path))
    cursor = db.cursor()

    # Create vector table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            embedding FLOAT32_BLOB,
            text TEXT NOT NULL,
            text_preview TEXT,
            source_file TEXT,
            source_type TEXT,
            metadata TEXT
        )
    """)

    # Insert embeddings
    log.info("Inserting embeddings into index...")
    for i, record in enumerate(embeddings):
        cursor.execute("""
            INSERT INTO chunks (chunk_id, embedding, text, text_preview, source_file, source_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record["chunk_id"],
            bytes(record["embedding"]),
            record["text"],
            record["text_preview"],
            record["source_file"],
            record["source_type"],
            json.dumps(record.get("metadata", {}))
        ))
        if (i + 1) % 1000 == 0:
            log.info(f"Inserted {i + 1} embeddings...")

    db.commit()
    log.info(f"✅ Vector index created: {db_path}")
    log.info(f"   Total chunks: {len(embeddings)}")

def create_index_simple_sqlite(embeddings: List[Dict], db_path: Path):
    """Fallback: simple sqlite3 with BLOB storage (no vector ops, but searchable)."""
    log.info(f"Creating simple SQLite index at {db_path}")
    db = sqlite3.connect(str(db_path))
    cursor = db.cursor()

    # Create table (embeddings stored as JSON for simplicity)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            embedding TEXT,
            text TEXT NOT NULL,
            text_preview TEXT,
            source_file TEXT,
            source_type TEXT,
            metadata TEXT
        )
    """)

    # Create text search index (FTS)
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_id UNINDEXED,
            text,
            source_file UNINDEXED,
            content=chunks,
            content_rowid=chunk_id
        )
    """)

    log.info("Inserting embeddings into index...")
    for i, record in enumerate(embeddings):
        cursor.execute("""
            INSERT INTO chunks (chunk_id, embedding, text, text_preview, source_file, source_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record["chunk_id"],
            json.dumps(record["embedding"]),
            record["text"],
            record["text_preview"],
            record["source_file"],
            record["source_type"],
            json.dumps(record.get("metadata", {}))
        ))

        # Also index in FTS
        cursor.execute("""
            INSERT INTO chunks_fts (chunk_id, text, source_file)
            VALUES (?, ?, ?)
        """, (
            record["chunk_id"],
            record["text"],
            record["source_file"]
        ))

        if (i + 1) % 1000 == 0:
            log.info(f"Inserted {i + 1} embeddings...")

    db.commit()
    log.info(f"✅ Simple SQLite index created: {db_path}")
    log.info(f"   Total chunks: {len(embeddings)}")
    log.info(f"   Note: Text search only (FTS). Use rag_retriever.py with embedding model for semantic search.")

def main():
    """Orchestrate index building."""
    if not EMBEDDINGS_FILE.exists():
        log.error(f"Embeddings file not found: {EMBEDDINGS_FILE}")
        log.error("Run embedding_worker.py first to create embeddings.jsonl")
        return

    embeddings = load_embeddings(EMBEDDINGS_FILE)
    create_index_sqlite_vec(embeddings, INDEX_DB)

if __name__ == "__main__":
    main()

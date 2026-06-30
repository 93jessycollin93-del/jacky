#!/usr/bin/env python3
"""
Ingestion Pipeline: Load data files, chunk, deduplicate, write to raw_chunks.jsonl.
Supports JSON, CSV, Parquet, Markdown, plain text, code files.
"""
import os, json, hashlib, re
from pathlib import Path
from typing import List, Dict, Iterator
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("IngestionPipeline")

# Configuration
DATA_ROOT = Path("E:/AI/Jacky/data")          # Local project data
ARCHIVE_ROOT = Path("H:/AI_ARCHIVE")           # Ollama models, snapshots
HF_DATASETS_ROOT = Path("H:/datasets")         # Downloaded HF datasets
OUTPUT_FILE = DATA_ROOT / "raw_chunks.jsonl"
CHUNK_SIZE = 512                              # tokens per chunk
CHUNK_OVERLAP = 100                           # token overlap for context

@dataclass
class Chunk:
    """A single chunk from the ingestion pipeline."""
    chunk_id: str
    source_file: str
    source_type: str                          # json, csv, markdown, code, etc.
    text: str
    metadata: Dict

def token_estimate(text: str) -> int:
    """Rough token count: ~4 chars per token."""
    return len(text.split())

def deduplicate_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """Remove duplicate chunks by SHA256 of text."""
    seen = {}
    unique = []
    for chunk in chunks:
        h = hashlib.sha256(chunk.text.encode()).hexdigest()
        if h not in seen:
            seen[h] = True
            unique.append(chunk)
    log.info(f"Deduplication: {len(chunks)} → {len(unique)} chunks")
    return unique

class ChunkWriter:
    """Write chunks to JSONL incrementally."""
    def __init__(self, output_path: Path):
        self.path = output_path
        self.count = 0

    def write(self, chunks: List[Chunk]):
        """Append chunks to JSONL file."""
        with open(self.path, 'a', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(asdict(chunk)) + '\n')
                self.count += 1
        log.info(f"Wrote {len(chunks)} chunks (total: {self.count})")

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks by token count."""
    words = text.split()
    chunks_out = []
    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        if chunk:
            chunks_out.append(' '.join(chunk))
        i += chunk_size - overlap
    return chunks_out

# ─── Loaders for different file types ──────────────────────────────────

def load_json_file(path: Path) -> Iterator[Dict]:
    """Load JSON file; yield records if it's a list or streaming JSONL."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
            if text.strip().startswith('['):
                data = json.loads(text)
                if isinstance(data, list):
                    for item in data:
                        yield item if isinstance(item, dict) else {"content": str(item)}
            else:
                for line in text.splitlines():
                    if line.strip():
                        yield json.loads(line)
    except Exception as e:
        log.warning(f"Failed to load JSON from {path}: {e}")

def load_text_file(path: Path) -> str:
    """Load plain text, markdown, or code file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        log.warning(f"Failed to load text from {path}: {e}")
        return ""

def load_csv_file(path: Path, limit_rows: int = 1000) -> str:
    """Load CSV as delimited text (first N rows)."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(limit_rows + 1)]
            return '\n'.join(lines)
    except Exception as e:
        log.warning(f"Failed to load CSV from {path}: {e}")
        return ""

def load_parquet_file(path: Path) -> str:
    """Load Parquet file (requires pyarrow/pandas)."""
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        return df.to_string(max_rows=500)
    except ImportError:
        log.warning(f"pandas/pyarrow not installed; skipping {path}")
        return ""
    except Exception as e:
        log.warning(f"Failed to load Parquet from {path}: {e}")
        return ""

# ─── Ingestion for different sources ───────────────────────────────────

def ingest_file(path: Path, file_type: str = None) -> List[Chunk]:
    """Load a file, chunk it, return Chunk objects."""
    chunks_out = []
    if file_type is None:
        file_type = path.suffix.lower().lstrip('.')

    # Map file extension to loader
    if file_type in ('json', 'jsonl'):
        for record in load_json_file(path):
            text = json.dumps(record) if isinstance(record, dict) else str(record)
            for chunk_text in chunk_text(text):
                chunks_out.append(Chunk(
                    chunk_id=f"{path.stem}_{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
                    source_file=str(path.relative_to(Path.cwd())),
                    source_type='json',
                    text=chunk_text,
                    metadata={"file_type": file_type, "path": str(path)}
                ))
    elif file_type in ('csv',):
        text = load_csv_file(path)
        for chunk_text in chunk_text(text):
            chunks_out.append(Chunk(
                chunk_id=f"{path.stem}_{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
                source_file=str(path.relative_to(Path.cwd())),
                source_type='csv',
                text=chunk_text,
                metadata={"file_type": file_type, "path": str(path)}
            ))
    elif file_type in ('parquet',):
        text = load_parquet_file(path)
        if text:
            for chunk_text in chunk_text(text):
                chunks_out.append(Chunk(
                    chunk_id=f"{path.stem}_{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
                    source_file=str(path.relative_to(Path.cwd())),
                    source_type='parquet',
                    text=chunk_text,
                    metadata={"file_type": file_type, "path": str(path)}
                ))
    else:  # markdown, code, text
        text = load_text_file(path)
        if text:
            for chunk_text in chunk_text(text):
                chunks_out.append(Chunk(
                    chunk_id=f"{path.stem}_{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
                    source_file=str(path.relative_to(Path.cwd())),
                    source_type=file_type,
                    text=chunk_text,
                    metadata={"file_type": file_type, "path": str(path)}
                ))

    log.info(f"Ingested {path.name}: {len(chunks_out)} chunks")
    return chunks_out

def ingest_directory(root: Path, extensions: List[str] = None) -> List[Chunk]:
    """Recursively ingest all files in a directory."""
    if extensions is None:
        extensions = ['.json', '.jsonl', '.csv', '.parquet', '.md', '.txt', '.py', '.js']

    all_chunks = []
    for ext in extensions:
        for file_path in root.rglob(f'*{ext}'):
            if file_path.is_file() and file_path.stat().st_size < 100 * 1024 * 1024:  # Skip >100 MB
                chunks = ingest_file(file_path)
                all_chunks.extend(chunks)

    return all_chunks

# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    """Orchestrate full ingestion pipeline."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    writer = ChunkWriter(OUTPUT_FILE)

    sources = [
        (DATA_ROOT, ['*.json', '*.md', '*.txt']),
        (HF_DATASETS_ROOT, ['*.parquet', '*.jsonl']),
    ]

    for source_path, patterns in sources:
        if not source_path.exists():
            log.warning(f"Source path does not exist: {source_path}")
            continue

        log.info(f"Ingesting from {source_path}")
        chunks = ingest_directory(source_path)
        chunks = deduplicate_chunks(chunks)
        writer.write(chunks)

    log.info(f"✅ Ingestion complete. {writer.count} total chunks written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

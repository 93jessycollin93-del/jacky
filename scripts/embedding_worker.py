#!/usr/bin/env python3
"""
Batch embedding worker: read raw_chunks.jsonl, embed each chunk with sentence-transformers.
Output: embeddings.jsonl (chunk_id, embedding, text_preview).
"""
import json
import logging
from pathlib import Path
from typing import List, Dict
import hashlib

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("EmbeddingWorker")

# Configuration
DATA_DIR = Path("E:/AI/Jacky/data")
INPUT_FILE = DATA_DIR / "raw_chunks.jsonl"
OUTPUT_FILE = DATA_DIR / "embeddings.jsonl"
MODEL_NAME = "all-minilm-l6-v2"                # Fast + small (22 MB)
BATCH_SIZE = 512

def load_chunks(input_path: Path) -> List[Dict]:
    """Load chunks from JSONL file."""
    chunks = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    log.info(f"Loaded {len(chunks)} chunks from {input_path}")
    return chunks

def embed_chunks(chunks: List[Dict], model_name: str = MODEL_NAME, batch_size: int = BATCH_SIZE):
    """
    Embed chunks using sentence-transformers.
    Yields (chunk, embedding_vector) tuples.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        log.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        raise

    log.info(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    texts = [chunk['text'] for chunk in chunks]
    log.info(f"Embedding {len(texts)} chunks in batches of {batch_size}")

    # Batch encode for efficiency
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=False)

    for chunk, embedding in zip(chunks, embeddings):
        yield chunk, embedding.tolist()

def write_embeddings(chunks: List[Dict], model_name: str, output_path: Path):
    """Embed chunks and write to JSONL with embeddings."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk, embedding in embed_chunks(chunks, model_name=model_name):
            record = {
                "chunk_id": chunk["chunk_id"],
                "embedding": embedding,
                "text": chunk["text"],
                "text_preview": chunk["text"][:150],
                "source_file": chunk["source_file"],
                "source_type": chunk["source_type"],
                "metadata": chunk.get("metadata", {}),
            }
            f.write(json.dumps(record) + '\n')
            written += 1
            if written % 100 == 0:
                log.info(f"Embedded {written} chunks...")

    log.info(f"✅ Embedding complete. {written} chunks written to {output_path}")

def main():
    """Orchestrate embedding pipeline."""
    if not INPUT_FILE.exists():
        log.error(f"Input file not found: {INPUT_FILE}")
        log.error("Run ingestion_pipeline.py first to create raw_chunks.jsonl")
        return

    chunks = load_chunks(INPUT_FILE)
    write_embeddings(chunks, MODEL_NAME, OUTPUT_FILE)

if __name__ == "__main__":
    main()

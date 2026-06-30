#!/usr/bin/env python3
"""
RAG Retriever: Query the vector index, return top-k chunks for injection into prompts.
Used by squad_manager.py to replace keyword-based _find_relevant_snippets.
"""
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional

log = logging.getLogger("RAGRetriever")

class RAGRetriever:
    """Query semantic search over chunked knowledge base."""

    def __init__(self, db_path: Path = None, model_name: str = "all-minilm-l6-v2"):
        self.db_path = db_path or Path("E:/AI/Jacky/data/jacky_knowledge.db")
        self.model_name = model_name
        self.db = None
        self.embedding_model = None
        self._load()

    def _load(self):
        """Load database connection + embedding model."""
        if not self.db_path.exists():
            log.warning(f"Vector index not found at {self.db_path}")
            return False

        try:
            self.db = sqlite3.connect(str(self.db_path))
            log.info(f"Connected to vector index: {self.db_path}")
        except Exception as e:
            log.error(f"Failed to open database: {e}")
            return False

        try:
            from sentence_transformers import SentenceTransformer
            log.info(f"Loading embedding model: {self.model_name}")
            self.embedding_model = SentenceTransformer(self.model_name)
        except ImportError:
            log.error("sentence-transformers not installed; keyword search only")
            self.embedding_model = None

        return True

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x ** 2 for x in a))
        mag_b = math.sqrt(sum(x ** 2 for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _simple_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Fallback: keyword search using FTS if semantic model unavailable."""
        if not self.db:
            return []

        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT chunk_id, text, source_file, source_type, metadata
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                LIMIT ?
            """, (query.replace(" ", " AND "), top_k))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "chunk_id": row[0],
                    "text": row[1],
                    "source_file": row[2],
                    "source_type": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                    "score": 0.0,  # Placeholder; FTS doesn't return scores
                })
            return results
        except Exception as e:
            log.warning(f"Keyword search failed: {e}")
            return []

    def query(self, prompt: str, top_k: int = 5) -> List[Dict]:
        """
        Search for chunks most relevant to prompt.
        Returns list of dicts: {chunk_id, text, source_file, source_type, score}.
        """
        if not self.db:
            log.warning("Vector index not loaded; returning empty results")
            return []

        if not self.embedding_model:
            log.info("Using keyword search (embedding model not available)")
            return self._simple_search(prompt, top_k)

        try:
            # Embed the query
            query_embedding = self.embedding_model.encode(prompt, convert_to_numpy=False).tolist()

            # Fetch all chunks (sqlite-vec would do this efficiently; for simple sqlite we do linear scan)
            cursor = self.db.cursor()
            cursor.execute("SELECT chunk_id, text, embedding, source_file, source_type, metadata FROM chunks")
            rows = cursor.fetchall()

            # Compute similarities
            scored = []
            for row in rows:
                chunk_id, text, embedding_blob, source_file, source_type, metadata = row

                # Parse embedding (could be JSON string or binary blob)
                try:
                    embedding = json.loads(embedding_blob) if isinstance(embedding_blob, str) else embedding_blob
                except:
                    log.warning(f"Could not parse embedding for {chunk_id}; skipping")
                    continue

                similarity = self._cosine_similarity(query_embedding, embedding)
                scored.append({
                    "chunk_id": chunk_id,
                    "text": text,
                    "source_file": source_file,
                    "source_type": source_type,
                    "metadata": json.loads(metadata) if metadata else {},
                    "score": similarity,
                })

            # Sort by score, return top-k
            scored.sort(key=lambda x: x["score"], reverse=True)
            results = scored[:top_k]

            log.debug(f"Query '{prompt[:50]}...' returned {len(results)} results (scores: {[r['score'] for r in results]})")
            return results

        except Exception as e:
            log.error(f"Semantic search failed: {e}")
            return self._simple_search(prompt, top_k)

    def format_for_prompt(self, chunks: List[Dict], max_chars: int = 2000) -> str:
        """Format retrieved chunks for injection into system prompt."""
        if not chunks:
            return ""

        lines = ["--- RELEVANT KNOWLEDGE BASE ---"]
        total_chars = 0
        for chunk in chunks:
            source = chunk.get("source_file", "unknown")
            score = chunk.get("score", 0)
            text = chunk["text"][:300]
            line = f"[{source} ({score:.2f})] {text}"
            if total_chars + len(line) > max_chars:
                break
            lines.append(line)
            total_chars += len(line)

        lines.append("--- END KNOWLEDGE BASE ---")
        return "\n".join(lines)

# Module-level singleton (used by squad_manager.py)
_retriever: Optional[RAGRetriever] = None

def get_retriever() -> RAGRetriever:
    """Lazy-load RAG retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever

def query_rag(prompt: str, top_k: int = 5) -> List[Dict]:
    """Query RAG index for chunks relevant to prompt."""
    return get_retriever().query(prompt, top_k)

def format_rag_context(prompt: str, top_k: int = 5) -> str:
    """Query RAG + format for prompt injection."""
    chunks = query_rag(prompt, top_k)
    return get_retriever().format_for_prompt(chunks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    retriever = get_retriever()
    test_queries = [
        "How do rallies work in the MMO?",
        "What is the Jackie core architecture?",
        "Ethereum smart contracts",
    ]
    for q in test_queries:
        print(f"\n📝 Query: {q}")
        results = retriever.query(q, top_k=3)
        for r in results:
            print(f"  [{r['source_file']} ({r['score']:.2f})] {r['text'][:80]}")

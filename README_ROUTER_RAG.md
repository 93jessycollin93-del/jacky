# Jacky Multi-Provider Router + RAG Memory System

**Added 2026-06-30**: Proactive cloud provider rotation + semantic memory search.

## Quick Start

### 1. Wire Up Your Cloud API Keys

Add to `secrets/secrets.env` (gitignored):

```env
XAI_API_KEY=xai-...your-real-key...
GROQ_API_KEY_1=gsk-...your-groq-key...
GEMINI_API_KEY=...your-gemini-key...
OPENROUTER_API_KEY=...your-openrouter-key...
```

### 2. Verify Router Connectivity

```bash
python cloud_router.py
```

Output will show:
- Enabled provider order (Groq → Gemini → xAI)
- Which providers have keys loaded
- Current usage stats

### 3. Test a Cloud Request

```python
from cloud_router import CloudRouter

router = CloudRouter()
result = router.ask("Explain the MMO rally mechanic in one sentence.")
print(result["response"])
print(f"Provider used: {result['provider']}")
print(f"Usage report: {router.usage_report()}")
```

---

## How the Router Works

### Proactive Rotation (New)

**Old behavior:** Try provider, fail → try next provider (wasteful, slow).  
**New behavior:** Check usage before each request. If a provider is at 80% of its per-minute limit, rotate to the next one *before* hitting throttling.

### Provider Limits (Config-Driven)

Set in `config.json`:

```json
{
  "provider_limits": {
    "xai": { "max_tokens_per_minute": 60000 },
    "groq": { "max_tokens_per_minute": 6000 },
    "gemini": { "max_tokens_per_minute": 15000 }
  }
}
```

Limits reset every minute. Track usage in `data/router_usage.json`.

### Usage Tracking

Each call records:
- Provider name
- Tokens used (prompt + completion, rough estimate)
- Timestamp
- Whether it succeeded

Persisted to disk; survives server restarts.

---

## RAG (Retrieval-Augmented Generation) System

Turn your 2TB dataset into searchable knowledge for agents.

### Pipeline Overview

```
Raw Files (E/G/V/H drives)
    ↓
Ingestion (chunks + dedup)
    ↓
raw_chunks.jsonl (512-token chunks, 100-token overlap)
    ↓
Embedding (sentence-transformers)
    ↓
embeddings.jsonl (chunk + vector)
    ↓
Vector Index (sqlite-vec)
    ↓
jacky_knowledge.db
    ↓
RAG Queries (semantic search)
    ↓
Agent Context (top-5 chunks injected into system prompt)
```

### Building the Index (Local on GODZILLA PC)

Run these scripts on your machine with access to E, G, V, H drives:

```bash
# 1. Inventory large files on V:\
python scripts/find_large_files.py
# Output: V_large_files.json

# 2. Chunk + deduplicate files
python scripts/ingestion_pipeline.py
# Output: data/raw_chunks.jsonl (~10k-100k chunks, depending on source size)

# 3. Embed chunks (1-2 hours for 100k chunks on CPU)
python scripts/embedding_worker.py
# Output: data/embeddings.jsonl

# 4. Build vector index
python scripts/build_vector_index.py
# Output: data/jacky_knowledge.db (~500 MB for 100k chunks)
```

### Querying the Index

Automatically integrated into agent context. When an agent responds:

1. Prompt is embedded (same model as training)
2. Vector search finds top-5 most similar chunks
3. Chunks are injected into the agent's system prompt
4. Agent can now cite and reason over knowledge base

**Manual query:**

```python
from rag_retriever import get_retriever

retriever = get_retriever()

# Query and get results
results = retriever.query("How do rallies work in the MMO?", top_k=5)
for chunk in results:
    print(f"[{chunk['source_file']} ({chunk['score']:.2f})] {chunk['text'][:200]}")

# Format for prompt injection
context = retriever.format_for_prompt(results)
print(context)
```

### Performance Notes

- **Embedding speed**: ~100-200 chunks/sec on CPU (all-minilm model)
- **Query latency**: ~200-500 ms per query (embedding + search)
- **Index size**: ~5 bytes per token in original text (~500 MB for 100M tokens)
- **Recall quality**: Better than keyword search; can find semantically related content

### Embedding Model Choices

**all-minilm-l6-v2** (current, recommended for Jacky):
- Size: 22 MB
- Speed: Fast (200+ chunks/sec on CPU)
- Accuracy: Good for general code + knowledge
- No API cost

**all-mpnet-base-v2** (higher quality):
- Size: 109 MB
- Speed: Slower (50-100 chunks/sec on CPU)
- Accuracy: Better recall (more precise matches)
- Still free (local)

To switch: update `config.json: rag.model` and re-run embedding pipeline.

---

## Integration with Squad Manager

`squad_manager.py` now uses RAG as primary memory source:

```python
bot_config = squad_manager.get_bot("lead")
system_prompt = squad_manager.build_system_prompt(bot_config, user_prompt)
# The prompt now includes top-5 RAG chunks + any local memory snippets
```

Falls back to keyword search if RAG DB unavailable (e.g., first run).

---

## Architecture: Local-First, Cost-Efficient

- ✅ No embedding API costs (runs on your CPU)
- ✅ Single-file database (sqlite-vec)
- ✅ No external services (just Python + SQLite)
- ✅ Thermal-gated (heavy indexing won't max GPU; CPU-only)
- ✅ Knowledge persists across restarts
- ✅ Config-driven (no code changes to tune)

---

## Next Steps for the Team

1. **Run inventory** on E/G/V/H drives to identify best source data
2. **Start with 50 GB pilot** (easier to test and iterate)
3. **Measure**: Ingestion speed, embedding time, query latency, search quality
4. **Tune**: Adjust chunk size, model, limits based on your hardware + use case
5. **Scale**: Once pilot is working, ingest full 2TB

---

## Troubleshooting

**"Vector index not found"** → Run the ingestion pipeline steps above.

**"sentence-transformers not installed"** → `pip install sentence-transformers`

**"sqlite-vec not installed"** → `pip install sqlite-vec` (or falls back to simple SQLite FTS)

**Query latency is slow** → Try `all-minilm-l6-v2` (faster) instead of mpnet. Or batch your queries.

**Index is huge** → Reduce chunk size (e.g., 256 tokens instead of 512) or fewer chunks retained.

---

## Files Added / Modified

**New:**
- `cloud_router.py`: Enhanced with `UsageTracker`, `_should_rotate()`, `_rotate_to_next()`
- `rag_retriever.py`: Semantic search + query layer
- `scripts/find_large_files.py`: Inventory script
- `scripts/ingestion_pipeline.py`: Chunking + dedup
- `scripts/embedding_worker.py`: Batch embedding
- `scripts/build_vector_index.py`: Index builder
- `README_ROUTER_RAG.md`: This file

**Modified:**
- `cloud_client.py`: Updated Grok model (grok-beta → grok-4)
- `config.json`: Added provider limits + RAG config
- `squad_manager.py`: Now uses RAG + fallback to keywords

---

## Questions?

See the plan at `.claude/plans/got-the-vision-clear-wondrous-moon.md` for full architecture + design decisions.

# Jacky Data Collector & Refiner Setup Guide

**Status:** Production-Ready  
**Version:** 1.0  
**Date:** 2026-06-29

---

## Overview

The Jacky Data Collector is a **background asset refinement system** that autonomously:

1. **FETCHES** data from multiple sources (memory archive, system state, project files)
2. **FILTERS** for novelty and durability
3. **COMPRESSES** to atomic knowledge units
4. **INTERNALIZES** into a persistent knowledge graph
5. **ACTS** by making knowledge available to other systems

The system runs **independently** in the background while the UI remains responsive.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA COLLECTOR SERVICE                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐   ┌─────────┐   ┌───────────┐               │
│  │  FETCH   │──▶│ FILTER  │──▶│ COMPRESS  │               │
│  │ Sources  │   │ Novelty │   │ Insights  │               │
│  └──────────┘   └─────────┘   └───────────┘               │
│       ▲                            │                        │
│       │                            ▼                        │
│       │        ┌──────────────────────────────┐             │
│       │        │   INTERNALIZE (Knowledge DB)  │             │
│       │        │   - Store nodes               │             │
│       │        │   - Build graph edges         │             │
│       │        │   - Persist to disk           │             │
│       │        └──────────────────────────────┘             │
│       │                    │                                │
│       │                    ▼                                │
│       │        ┌──────────────────────────────┐             │
│       └────────│    ACT (Knowledge Available)  │             │
│                │    - API endpoints            │             │
│                │    - Context injection        │             │
│                │    - Analysis triggers        │             │
│                └──────────────────────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Files

### Core Components

| File | Purpose |
|------|---------|
| `data_collector.py` | Collector service, pipeline, storage |
| `jacky_unified_enhanced.jsx` | Enhanced UI with collector controls |
| `COLLECTOR_SETUP.md` | This guide |

### Integration

Add to `jacky_api.py` (see section below).

---

## Installation & Setup

### Step 1: Add to Flask App

In your `jacky_api.py`, add the collector route registration:

```python
from data_collector import register_collector_routes

# In your Flask app setup:
register_collector_routes(app)
```

### Step 2: Ensure Dependencies

```bash
pip install Flask Flask-CORS psutil  # psutil for system metrics
```

### Step 3: Create Data Directories

```bash
mkdir -p E:\AI\Jacky\data
mkdir -p H:\AI_ARCHIVE
```

### Step 4: Update UI Import

Replace `chat.html` iframe route with the enhanced component:

```jsx
// In hub.html or wherever you load chat
import JackyUnifiedEnhanced from './jacky_unified_enhanced.jsx';

export default function Hub() {
  return <JackyUnifiedEnhanced />;
}
```

---

## API Reference

### Start Collection

```http
POST /api/collector/start
Content-Type: application/json

{
  "interval": 60  // seconds between collection cycles
}
```

**Response:**
```json
{
  "status": "started",
  "interval": 60
}
```

### Stop Collection

```http
POST /api/collector/stop
```

**Response:**
```json
{
  "status": "stopped"
}
```

### Collect Once

```http
POST /api/collector/collect
Content-Type: application/json

{
  "sources": ["memory_archive", "system_state", "project_files"]
}
```

**Response:**
```json
{
  "pipeline_result": {
    "learned": 12,
    "graph_size": 345,
    "timestamp": "2026-06-29T10:23:45.123456"
  },
  "stats": {
    "fetched": 25,
    "filtered": 12,
    "compressed": 12,
    "internalized": 12,
    "acted": 12
  },
  "assets_processed": 25,
  "timestamp": "2026-06-29T10:23:45.123456"
}
```

### Get Status

```http
GET /api/collector/status
```

**Response:**
```json
{
  "running": true,
  "graph_size": 345,
  "pipeline_stats": {
    "fetched": 120,
    "filtered": 85,
    "compressed": 85,
    "internalized": 85,
    "acted": 85
  },
  "last_run": {
    "memory_archive": 1719728400.123,
    "system_state": 1719728405.456
  },
  "recent_logs": [
    "[2026-06-29 10:23:45.123456] Processed 25 assets → 12 learned",
    "[2026-06-29 10:23:15.789012] Processed 18 assets → 8 learned"
  ],
  "timestamp": "2026-06-29T10:23:45.123456"
}
```

### Load Knowledge Graph

```http
GET /api/collector/graph
```

**Response:**
```json
{
  "count": 345,
  "nodes": [
    {
      "id": "a1b2c3d4e5f6g7h8",
      "source": "memory:feedback-testing.md",
      "domain": "PERSONAL",
      "novelty_score": 0.75,
      "durability_score": 0.85,
      "core_insight": "Integration tests must hit real database not mocks",
      "tags": ["testing", "integration", "database", "mocks"],
      "created_at": "2026-06-29T10:00:00.000000",
      "refined_at": "2026-06-29T10:01:23.456789",
      "status": "acted"
    },
    ...
  ]
}
```

---

## Data Sources

### 1. Memory Archive

**Location:** `C:\Users\93jes\.claude\projects\C--Users-93jes\memory\`

**Collects:**
- Personal memory files (*.md)
- User context and feedback
- Decision records and preferences

**Interval:** 300 seconds (5 min)

### 2. System State

**Metrics:**
- CPU usage %
- Memory usage %
- Disk usage %

**Interval:** 60 seconds (1 min)

### 3. Project Files

**Collects:**
- Bot configuration files (`bots/*.json`)
- Project metadata
- System configuration

**Interval:** 600 seconds (10 min)

### 4. API Feeds (Optional)

**Disabled by default.** To enable:

```python
COLLECTION_CONFIG["sources"]["api_feeds"]["enabled"] = True
```

Add a new source class in `data_collector.py`:

```python
class APIFeedSource(DataSource):
    def collect(self) -> list:
        assets = []
        # Fetch from RSS, GitHub API, etc.
        return assets
```

---

## Storage & Persistence

### Knowledge Graph

**Location:** `E:\AI\Jacky\data\knowledge_graph.json`

**Format:**
```json
{
  "nodes": {
    "node_id_1": { node object },
    "node_id_2": { node object }
  },
  "edges": {
    "node_id_1": ["node_id_2", "node_id_3"]
  },
  "timestamp": "2026-06-29T10:23:45.123456"
}
```

**Size Limits:**
- Max nodes: 10,000
- Max file size: 500 MB
- Auto-archived when limits reached

### Archives

**Location:** `H:\AI_ARCHIVE\`

Old knowledge nodes are archived to preserve history while keeping active graph lean.

---

## Configuration

Edit `data_collector.py` section `COLLECTION_CONFIG`:

```python
COLLECTION_CONFIG = {
    "sources": {
        "memory_archive": {"enabled": True, "interval": 300, "priority": 1},
        "system_state": {"enabled": True, "interval": 60, "priority": 2},
        "project_files": {"enabled": True, "interval": 600, "priority": 3},
        "api_feeds": {"enabled": False, "interval": 300, "priority": 4},
    },
    "filters": {
        "novelty_threshold": 0.6,      # 0-1, higher = stricter
        "durability_threshold": 0.5,   # 0-1, higher = stricter
        "max_age_days": 90,            # Remove nodes older than this
    },
    "storage": {
        "max_nodes": 10000,
        "max_size_mb": 500,
        "archive_path": "H:/AI_ARCHIVE",
        "data_path": "E:/AI/Jacky/data",
    }
}
```

---

## Usage Guide

### Quick Start

1. **Open Hub:** `http://localhost:5000/hub`
2. **Login:** Any token (for testing)
3. **Go to Collector Tab**
4. **Select Sources:** Check the boxes for data you want to collect
5. **Start Collector:** Click "START" → background collection begins
6. **Monitor:** Watch the pipeline stats and logs in real-time
7. **View Knowledge:** Click "LOAD GRAPH" → browse accumulated nodes

### Common Workflows

#### Collect Once Manually

```javascript
fetch('http://localhost:5000/api/collector/collect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    sources: ['memory_archive', 'system_state']
  })
})
.then(r => r.json())
.then(data => console.log(`Learned ${data.pipeline_result.learned} nodes`))
```

#### Monitor Collection Status

```javascript
setInterval(async () => {
  const res = await fetch('http://localhost:5000/api/collector/status');
  const status = await res.json();
  console.log(`Graph: ${status.graph_size} nodes | Running: ${status.running}`);
}, 5000);
```

#### Export Knowledge Graph

```bash
# Via API
curl http://localhost:5000/api/collector/graph > knowledge.json

# Direct file access
cat E:\AI\Jacky\data\knowledge_graph.json
```

---

## Performance Tuning

### If Collection is Slow

1. **Reduce frequency:**
   ```python
   "memory_archive": {"enabled": True, "interval": 600}  # 10 min instead of 5
   ```

2. **Disable expensive sources:**
   ```python
   "project_files": {"enabled": False}  # Skip project scanning
   ```

3. **Increase filter thresholds:**
   ```python
   "novelty_threshold": 0.8  # Be more selective
   ```

### If Graph is Too Large

1. **Reduce max nodes:**
   ```python
   "max_nodes": 5000
   ```

2. **Archive old nodes** (automatic at limit)

3. **Run cleanup** (manual):
   ```python
   collector.graph.cleanup(older_than_days=30)
   ```

---

## Troubleshooting

### Collector Won't Start

**Check:**
```bash
# Is Flask running?
curl http://localhost:5000/api/status

# Are routes registered?
curl http://localhost:5000/api/collector/status
# Should return 200 with status JSON
```

**Fix:**
- Restart Flask app
- Verify `register_collector_routes(app)` is called in `jacky_api.py`

### No Data Being Collected

**Check:**
```bash
# Are sources enabled?
curl http://localhost:5000/api/collector/status
# Look at "last_run" timestamps

# Do source directories exist?
ls C:\Users\93jes\.claude\projects\C--Users-93jes\memory\
ls E:\AI\Jacky\data
```

**Fix:**
- Create missing directories
- Check source configuration
- Run `collect_once()` manually to see error output

### Knowledge Graph Not Growing

**Check:**
- Run `curl http://localhost:5000/api/collector/graph`
- Look at `pipeline_stats` in status
- Check if nodes are being filtered out (high thresholds?)

**Fix:**
- Lower novelty/durability thresholds
- Add more data sources
- Check recent logs for errors

---

## Advanced: Custom Data Source

Create a new source class in `data_collector.py`:

```python
class CustomSource(DataSource):
    """Your custom data source"""
    def collect(self) -> list:
        assets = []
        # Your collection logic here
        my_data = fetch_from_somewhere()
        
        for item in my_data:
            asset = DataAsset(
                source="custom:my_source",
                raw_content=str(item),
                domain="CUSTOM"
            )
            assets.append(asset)
        
        return assets

# Register it
collector.sources["custom"] = CustomSource()

# Enable in config
COLLECTION_CONFIG["sources"]["custom"] = {
    "enabled": True,
    "interval": 300,
    "priority": 5
}
```

---

## Metrics & Monitoring

### Key Metrics

| Metric | Meaning |
|--------|---------|
| `fetched` | Raw data items collected |
| `filtered` | Items passing novelty/durability checks |
| `compressed` | Insights extracted |
| `internalized` | Nodes stored in knowledge graph |
| `acted` | Knowledge made available |
| `graph_size` | Current node count |

### Example: Daily Summary

```python
import requests

status = requests.get("http://localhost:5000/api/collector/status").json()
print(f"""
=== Daily Collector Summary ===
Nodes collected: {status['pipeline_stats']['fetched']}
Nodes learned: {status['pipeline_stats']['internalized']}
Knowledge graph size: {status['graph_size']}
Status: {'RUNNING' if status['running'] else 'IDLE'}
""")
```

---

## Integration with Squads

The knowledge graph can be injected into squad prompts automatically:

```python
# In squad_manager.py
from data_collector import get_collector

def build_system_prompt(self, bot, prompt):
    # Get collector graph
    collector = get_collector()
    relevant_nodes = collector.graph.search(prompt, top_k=3)
    
    # Inject into system prompt
    context = "\n".join([n.core_insight for n in relevant_nodes])
    
    return f"""
{bot.system_prompt_prefix}

## Recent Knowledge Context
{context}
"""
```

---

## Next Steps

1. ✅ Integrate Flask routes
2. ✅ Deploy enhanced UI
3. ⬜ Start background collection
4. ⬜ Monitor knowledge graph growth
5. ⬜ Inject graph into squad prompts
6. ⬜ Add custom data sources as needed

---

## Support

**Issues?** Check:
- `E:\AI\Jacky\data\` for graph files
- Flask console output for errors
- `/api/collector/status` for detailed diagnostics

**Questions?** See:
- `data_collector.py` for implementation details
- `jacky_unified_enhanced.jsx` for UI examples
- API Reference section above

---

**Status:** Ready for production use  
**Last Updated:** 2026-06-29

#!/usr/bin/env python3
"""
Jacky Data Collector & Refiner
==============================
Background service that:
1. Collects data from multiple sources (files, APIs, system state)
2. Processes through FETCH → FILTER → COMPRESS → INTERNALIZE → ACT pipeline
3. Stores refined knowledge assets to disk
4. Maintains a persistent knowledge graph

Runs independently of the UI. UI can query status and trigger collection.
"""

import os
import json
import time
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ====== CONFIGURATION ======
ARCHIVE_PATH = Path("H:/AI_ARCHIVE")
DATA_PATH = Path("E:/AI/Jacky/data")
MEMORY_PATH = Path("C:/Users/93jes/.claude/projects/C--Users-93jes/memory")

COLLECTION_CONFIG = {
    "sources": {
        "memory_archive": {"enabled": True, "interval": 300, "priority": 1},
        "system_state": {"enabled": True, "interval": 60, "priority": 2},
        "project_files": {"enabled": True, "interval": 600, "priority": 3},
        "api_feeds": {"enabled": False, "interval": 300, "priority": 4},
    },
    "filters": {
        "novelty_threshold": 0.6,
        "durability_threshold": 0.5,
        "max_age_days": 90,
    },
    "storage": {
        "max_nodes": 10000,
        "max_size_mb": 500,
        "archive_path": str(ARCHIVE_PATH),
        "data_path": str(DATA_PATH),
    }
}

# ====== DATA MODELS ======
class DataAsset:
    """A collected, filtered, and refined data unit"""
    def __init__(self, source, raw_content, domain="GENERAL"):
        self.id = hashlib.md5(f"{source}{raw_content}{time.time()}".encode()).hexdigest()[:16]
        self.source = source
        self.raw_content = raw_content
        self.domain = domain
        self.novelty_score = 0.0
        self.durability_score = 0.0
        self.core_insight = ""
        self.tags = []
        self.created_at = datetime.now().isoformat()
        self.refined_at = None
        self.status = "raw"  # raw, filtered, compressed, internalized, acted

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "domain": self.domain,
            "novelty_score": self.novelty_score,
            "durability_score": self.durability_score,
            "core_insight": self.core_insight,
            "tags": self.tags,
            "created_at": self.created_at,
            "refined_at": self.refined_at,
            "status": self.status,
        }

class KnowledgeGraph:
    """Persistent storage of refined knowledge"""
    def __init__(self, path=None):
        self.path = path or DATA_PATH / "knowledge_graph.json"
        self.nodes = {}
        self.edges = {}
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    self.nodes = {k: DataAsset.__dict__.update(v) for k, v in data.get("nodes", {}).items()}
            except Exception as e:
                print(f"[GRAPH] Load error: {e}")

    def save(self):
        os.makedirs(self.path.parent, exist_ok=True)
        try:
            with open(self.path, 'w') as f:
                json.dump({
                    "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
                    "edges": self.edges,
                    "timestamp": datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            print(f"[GRAPH] Save error: {e}")

    def add_node(self, asset):
        self.nodes[asset.id] = asset
        self.save()

    def count(self):
        return len(self.nodes)

# ====== COLLECTION SOURCES ======
class DataSource:
    def collect(self) -> list:
        """Return list of DataAsset objects"""
        raise NotImplementedError

class MemoryArchiveSource(DataSource):
    """Collect from personal memory archive"""
    def collect(self) -> list:
        assets = []
        if not MEMORY_PATH.exists():
            return assets

        try:
            for md_file in MEMORY_PATH.glob("*.md"):
                if md_file.name == "MEMORY.md":
                    continue
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        asset = DataAsset(
                            source=f"memory:{md_file.name}",
                            raw_content=content[:500],
                            domain="PERSONAL"
                        )
                        assets.append(asset)
                except Exception as e:
                    print(f"[COLLECT] Memory file error: {e}")
        except Exception as e:
            print(f"[COLLECT] Memory archive error: {e}")

        return assets

class SystemStateSource(DataSource):
    """Collect system metrics and state"""
    def collect(self) -> list:
        assets = []
        try:
            import psutil
            # CPU, memory, disk state
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent

            asset = DataAsset(
                source="system:metrics",
                raw_content=f"CPU:{cpu}% MEM:{memory}% DISK:{disk}%",
                domain="SYSTEMS"
            )
            assets.append(asset)
        except Exception as e:
            print(f"[COLLECT] System state error: {e}")

        return assets

class ProjectFilesSource(DataSource):
    """Collect from project directories"""
    def collect(self) -> list:
        assets = []
        project_paths = [
            Path("E:/AI/Jacky"),
            Path("E:/AI"),
        ]

        for proj_path in project_paths:
            if not proj_path.exists():
                continue
            try:
                for config_file in proj_path.glob("**/*.json"):
                    if config_file.stat().st_size < 10000:  # Only small configs
                        try:
                            with open(config_file, 'r') as f:
                                content = f.read()[:300]
                                asset = DataAsset(
                                    source=f"project:{config_file.name}",
                                    raw_content=content,
                                    domain="CODE"
                                )
                                assets.append(asset)
                        except Exception as e:
                            pass
            except Exception as e:
                print(f"[COLLECT] Project files error: {e}")

        return assets

# ====== PIPELINE STAGES ======
class Pipeline:
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.stats = {
            "fetched": 0,
            "filtered": 0,
            "compressed": 0,
            "internalized": 0,
            "acted": 0,
        }

    def fetch(self, sources: list) -> list:
        """STAGE 1: Collect raw data"""
        assets = []
        for source in sources:
            try:
                assets.extend(source.collect())
            except Exception as e:
                print(f"[FETCH] Source error: {e}")

        self.stats["fetched"] += len(assets)
        return assets

    def filter(self, assets: list) -> list:
        """STAGE 2: Score novelty & durability"""
        filtered = []
        for asset in assets:
            # Simple novelty: length > 10
            asset.novelty_score = min(1.0, len(asset.raw_content) / 100)
            # Durability: if not too recent, it's durable
            asset.durability_score = 0.7 if asset.source.startswith("memory") else 0.5

            threshold = COLLECTION_CONFIG["filters"]["novelty_threshold"]
            if asset.novelty_score > threshold or asset.durability_score > 0.6:
                filtered.append(asset)
                asset.status = "filtered"

        self.stats["filtered"] += len(filtered)
        return filtered

    def compress(self, assets: list) -> list:
        """STAGE 3: Extract core insight"""
        compressed = []
        for asset in assets:
            # Extract first sentence or key words
            words = asset.raw_content.split()[:10]
            asset.core_insight = " ".join(words) if words else "No insight"
            asset.tags = [t for t in asset.raw_content.split() if len(t) > 4][:5]
            asset.status = "compressed"
            compressed.append(asset)

        self.stats["compressed"] += len(compressed)
        return compressed

    def internalize(self, assets: list) -> list:
        """STAGE 4: Store to knowledge graph"""
        internalized = []
        for asset in assets:
            self.graph.add_node(asset)
            asset.status = "internalized"
            asset.refined_at = datetime.now().isoformat()
            internalized.append(asset)

        self.stats["internalized"] += len(internalized)
        return internalized

    def act(self, assets: list) -> dict:
        """STAGE 5: Apply knowledge (trigger actions)"""
        actions = {
            "learned": len(assets),
            "graph_size": self.graph.count(),
            "timestamp": datetime.now().isoformat(),
        }

        for asset in assets:
            asset.status = "acted"

        self.stats["acted"] += len(assets)
        return actions

    def run_full_pipeline(self, sources: list) -> dict:
        """Execute complete FETCH → FILTER → COMPRESS → INTERNALIZE → ACT"""
        raw_assets = self.fetch(sources)
        filtered = self.filter(raw_assets)
        compressed = self.compress(filtered)
        internalized = self.internalize(compressed)
        actions = self.act(internalized)

        return {
            "pipeline_result": actions,
            "stats": self.stats,
            "assets_processed": len(raw_assets),
        }

# ====== BACKGROUND COLLECTOR ======
class BackgroundCollector:
    def __init__(self):
        self.graph = KnowledgeGraph()
        self.pipeline = Pipeline(self.graph)
        self.sources = {
            "memory_archive": MemoryArchiveSource(),
            "system_state": SystemStateSource(),
            "project_files": ProjectFilesSource(),
        }
        self.running = False
        self.thread = None
        self.last_run = {}
        self.collection_log = []

    def should_collect(self, source_name: str) -> bool:
        """Check if enough time has passed since last collection"""
        config = COLLECTION_CONFIG["sources"].get(source_name, {})
        if not config.get("enabled"):
            return False

        interval = config.get("interval", 300)
        last = self.last_run.get(source_name, 0)
        return (time.time() - last) > interval

    def collect_once(self, source_names=None):
        """Run one collection cycle"""
        if source_names is None:
            source_names = list(self.sources.keys())

        active_sources = [
            self.sources[name] for name in source_names
            if name in self.sources and self.should_collect(name)
        ]

        if not active_sources:
            return {"status": "no_sources_ready", "log": self.collection_log[-10:]}

        result = self.pipeline.run_full_pipeline(active_sources)
        result["timestamp"] = datetime.now().isoformat()

        # Log
        log_entry = f"[{result['timestamp']}] Processed {result['assets_processed']} assets → {result['pipeline_result']['learned']} learned"
        self.collection_log.append(log_entry)
        if len(self.collection_log) > 100:
            self.collection_log = self.collection_log[-100:]

        # Update last run
        for name in source_names:
            self.last_run[name] = time.time()

        return result

    def start_background(self, interval=60):
        """Start background collection thread"""
        if self.running:
            return {"status": "already_running"}

        self.running = True
        def background_loop():
            while self.running:
                try:
                    self.collect_once()
                    time.sleep(interval)
                except Exception as e:
                    print(f"[BACKGROUND] Error: {e}")
                    time.sleep(5)

        self.thread = threading.Thread(target=background_loop, daemon=True)
        self.thread.start()
        return {"status": "started", "interval": interval}

    def stop_background(self):
        """Stop background collection thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        return {"status": "stopped"}

    def status(self):
        """Get collector status"""
        return {
            "running": self.running,
            "graph_size": self.graph.count(),
            "pipeline_stats": self.pipeline.stats,
            "last_run": self.last_run,
            "recent_logs": self.collection_log[-20:],
            "timestamp": datetime.now().isoformat(),
        }

# ====== SINGLETON INSTANCE ======
_collector = None

def get_collector():
    global _collector
    if _collector is None:
        _collector = BackgroundCollector()
    return _collector

# ====== FLASK INTEGRATION ======
def register_collector_routes(app):
    """Register Flask routes for collection management"""
    from flask import jsonify, request

    @app.route("/api/collector/status")
    def collector_status():
        return jsonify(get_collector().status())

    @app.route("/api/collector/start", methods=["POST"])
    def collector_start():
        interval = request.json.get("interval", 60)
        return jsonify(get_collector().start_background(interval))

    @app.route("/api/collector/stop", methods=["POST"])
    def collector_stop():
        return jsonify(get_collector().stop_background())

    @app.route("/api/collector/collect", methods=["POST"])
    def collector_collect_once():
        sources = request.json.get("sources")
        return jsonify(get_collector().collect_once(sources))

    @app.route("/api/collector/graph")
    def collector_graph():
        collector = get_collector()
        return jsonify({
            "count": collector.graph.count(),
            "nodes": [v.to_dict() for v in list(collector.graph.nodes.values())[-100:]],
        })

if __name__ == "__main__":
    # Demo: run standalone
    collector = BackgroundCollector()
    print("Starting collector...")
    collector.start_background(interval=30)

    for i in range(5):
        time.sleep(35)
        status = collector.status()
        print(f"\n=== Status {i+1} ===")
        print(f"Graph size: {status['graph_size']}")
        print(f"Pipeline: {status['pipeline_stats']}")
        print(f"Recent: {status['recent_logs'][-1] if status['recent_logs'] else 'None'}")

    collector.stop_background()
    print("\nCollector stopped.")

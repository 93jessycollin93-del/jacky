#!/usr/bin/env python3
"""
JACKY - AI Operations Manager
Core orchestrator service

Manages bots, analyzes tasks, routes work, tracks metrics.
Frame: "It's Jacky's PC. You learn from Jacky."
"""

import json
import os
import sys
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import sqlite3

# ============================================================================
# SETUP
# ============================================================================

JACKY_HOME = Path(__file__).parent
DATA_DIR = JACKY_HOME / "data"
BOTS_DIR = JACKY_HOME / "bots"
LOGS_DIR = DATA_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
BOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f"jacky_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("JACKY")

# ============================================================================
# DATA MODELS
# ============================================================================

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class BotStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class Task:
    """A unit of work for Jacky to distribute."""
    id: str
    name: str
    priority: TaskPriority
    target_bots: List[str]  # which bots can handle this
    payload: Dict[str, Any]
    created_at: float = None
    deadline: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

@dataclass
class BotInfo:
    """Metadata about a bot."""
    name: str
    status: BotStatus = BotStatus.OFFLINE
    busy_since: Optional[float] = None
    last_task: Optional[str] = None
    errors: int = 0
    completed_tasks: int = 0

# ============================================================================
# JACKY CORE
# ============================================================================

class JackyCore:
    """The orchestrator. It's Jacky's PC."""

    def __init__(self):
        self.bots: Dict[str, 'BotInfo'] = {}
        self.task_queue: List[Task] = []
        self.task_history: List[Task] = []
        self.lock = threading.Lock()
        self.running = False
        self.db_path = DATA_DIR / "jacky.db"

        log.info("=== JACKY CORE INITIALIZING ===")
        self._init_database()
        self._load_config()
        self._discover_bots()

    def _init_database(self):
        """SQLite for state persistence."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                priority TEXT,
                status TEXT,
                created_at REAL,
                completed_at REAL,
                result TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS bot_metrics (
                bot_name TEXT,
                timestamp REAL,
                status TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                tasks_completed INT,
                errors INT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                severity TEXT,
                message TEXT,
                education TEXT
            )
        """)
        conn.commit()
        conn.close()
        log.info("Database initialized")

    def _load_config(self):
        """Load Jacky configuration."""
        config_path = JACKY_HOME / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                self.config = json.load(f)
        else:
            self.config = {
                "max_concurrent_bots": 4,
                "resource_limits": {
                    "cpu_percent": 80,
                    "memory_percent": 75,
                    "disk_io_percent": 70
                },
                "time_cost_preference": "balanced",  # "speed", "cost", "balanced"
                "enabled_bots": ["monitor_bot", "github_bot", "security_bot"]
            }
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        log.info(f"Config loaded: {self.config}")

    def _discover_bots(self):
        """Auto-discover available bots."""
        for bot_file in BOTS_DIR.glob("*_bot.py"):
            bot_name = bot_file.stem
            if bot_name in self.config.get("enabled_bots", []):
                self.bots[bot_name] = BotInfo(name=bot_name)
                log.info(f"Bot discovered: {bot_name}")

    def submit_task(self, task: Task) -> str:
        """User or internal system submits a task."""
        with self.lock:
            self.task_queue.append(task)
        log.info(f"Task submitted: {task.name} (priority: {task.priority.name})")
        return task.id

    def analyze_and_route(self):
        """Analyze incoming tasks, decide bot allocation, route work."""
        while self.running:
            with self.lock:
                if not self.task_queue:
                    time.sleep(1)
                    continue

                # Sort by priority
                self.task_queue.sort(key=lambda t: t.priority.value)
                task = self.task_queue.pop(0)

            log.info(f"Routing task: {task.name}")

            # Decision: how many bots needed?
            bot_count = self._decide_bot_allocation(task)
            selected_bots = self._select_bots(task.target_bots, bot_count)

            if not selected_bots:
                log.warning(f"No available bots for task {task.name}")
                self._alert("NO_BOTS_AVAILABLE",
                    f"Task '{task.name}' has no available bots.",
                    education="Each bot has a specific job. If all are busy, tasks wait.")
                with self.lock:
                    self.task_queue.insert(0, task)  # re-queue
                time.sleep(2)
                continue

            # Dispatch to selected bots (parallel if multiple)
            self._dispatch(task, selected_bots)
            self.task_history.append(task)

            time.sleep(0.5)

    def _decide_bot_allocation(self, task: Task) -> int:
        """How many bots needed for this task?"""
        # Simple heuristic for now; ML can improve this later
        if task.priority == TaskPriority.CRITICAL:
            return min(self.config["max_concurrent_bots"], 3)
        elif task.priority == TaskPriority.HIGH:
            return 2
        else:
            return 1

    def _select_bots(self, target_bots: List[str], count: int) -> List[str]:
        """Select idle bots from target list."""
        idle_bots = [name for name, info in self.bots.items()
                     if info.status == BotStatus.IDLE and name in target_bots]
        return idle_bots[:count]

    def _dispatch(self, task: Task, bots: List[str]):
        """Send task to selected bots (would actually invoke bot.handle_task)."""
        log.info(f"Dispatching {task.name} to bots: {bots}")
        for bot_name in bots:
            self.bots[bot_name].status = BotStatus.BUSY
            self.bots[bot_name].busy_since = time.time()
            # In real implementation, would call bot.handle_task(task)

    def _alert(self, alert_type: str, message: str, education: str = ""):
        """Raise an alert with explanation."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("INSERT INTO alerts (timestamp, severity, message, education) VALUES (?, ?, ?, ?)",
                  (time.time(), alert_type, message, education))
        conn.commit()
        conn.close()
        log.warning(f"ALERT: {message}\nEDUCATION: {education}")

    def get_status(self) -> Dict[str, Any]:
        """Current system status (for SAS dashboard)."""
        with self.lock:
            return {
                "timestamp": time.time(),
                "jacky_running": self.running,
                "bots": {name: asdict(info) for name, info in self.bots.items()},
                "queued_tasks": len(self.task_queue),
                "total_completed": len(self.task_history),
                "config": self.config
            }

    def start(self):
        """Start Jacky's main loop."""
        self.running = True
        log.info("JACKY STARTING")
        log.info(f"Bots available: {list(self.bots.keys())}")

        # Start analyzer thread
        analyzer_thread = threading.Thread(target=self.analyze_and_route, daemon=True)
        analyzer_thread.start()

        # Start REST API (would be separate in production)
        # For now, just keep core running
        try:
            while self.running:
                time.sleep(10)
                log.debug(f"Status: {len(self.task_queue)} queued, {len(self.task_history)} completed")
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Shut down Jacky gracefully."""
        self.running = False
        log.info("JACKY SHUTTING DOWN")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    jacky = JackyCore()
    jacky.start()

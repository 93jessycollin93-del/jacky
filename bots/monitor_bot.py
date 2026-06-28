#!/usr/bin/env python3
"""
Monitor Bot - System health & alerts
Watches GPU, RAM, CPU, disk, processes.
Reports back to Jacky.
"""

import psutil
import os
import logging
from dataclasses import dataclass
from typing import Dict, Any

log = logging.getLogger("MonitorBot")

@dataclass
class SystemMetrics:
    """Current system state."""
    cpu_percent: float
    memory_percent: float
    gpu_memory_used: float  # MB
    gpu_memory_total: float  # MB
    disk_free_gb: Dict[str, float]  # per drive
    processes_running: int
    timestamp: float

class MonitorBot:
    """Jacky's system health monitor."""

    def __init__(self):
        self.name = "monitor_bot"
        self.alerts_sent = 0
        log.info("Monitor Bot ready")

    def get_system_metrics(self) -> SystemMetrics:
        """Sample current system state."""
        import time
        metrics = SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=psutil.virtual_memory().percent,
            gpu_memory_used=0,  # would query nvidia-smi
            gpu_memory_total=24576,  # RTX 3090 = 24GB
            disk_free_gb={
                'C': psutil.disk_usage('C:/').free / (1024**3),
                'E': psutil.disk_usage('E:/').free / (1024**3),
            },
            processes_running=len(psutil.pids()),
            timestamp=time.time()
        )
        return metrics

    def handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a monitoring task."""
        task_type = task.get("type", "full_check")

        if task_type == "full_check":
            metrics = self.get_system_metrics()
            result = {
                "status": "ok",
                "metrics": metrics.__dict__,
                "alerts": self._check_thresholds(metrics)
            }
        elif task_type == "gpu_check":
            result = {"gpu_memory_mb": 0}  # would get actual GPU status
        elif task_type == "disk_check":
            result = {"disk_free_gb": self.get_system_metrics().disk_free_gb}
        else:
            result = {"error": f"Unknown task type: {task_type}"}

        log.info(f"Monitoring task {task_type} complete")
        return result

    def _check_thresholds(self, metrics: SystemMetrics) -> list:
        """Check for problems."""
        alerts = []

        if metrics.cpu_percent > 80:
            alerts.append({
                "type": "HIGH_CPU",
                "value": metrics.cpu_percent,
                "message": f"CPU at {metrics.cpu_percent}%",
                "education": "High CPU means something is computing hard. If sustained, consider reducing load."
            })

        if metrics.memory_percent > 85:
            alerts.append({
                "type": "HIGH_MEMORY",
                "value": metrics.memory_percent,
                "message": f"Memory at {metrics.memory_percent}%",
                "education": "Running out of RAM. Jacky might pause some tasks to free space."
            })

        # Check disk space on E:
        if metrics.disk_free_gb['E'] < 100:
            alerts.append({
                "type": "DISK_SPACE_LOW",
                "drive": "E",
                "free_gb": metrics.disk_free_gb['E'],
                "message": f"E: drive low ({metrics.disk_free_gb['E']:.1f} GB free)",
                "education": "Your AI models and data live here. Jacky will alert you sooner if this gets worse."
            })

        return alerts

# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = MonitorBot()
    metrics = bot.get_system_metrics()
    print(f"CPU: {metrics.cpu_percent}%")
    print(f"RAM: {metrics.memory_percent}%")
    print(f"E: drive: {metrics.disk_free_gb.get('E', 'N/A'):.1f} GB free")

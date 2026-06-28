#!/usr/bin/env python3
"""
JACKY REST API & SAS Dashboard Server
Serves the web UI and API endpoints for Jacky Core.
"""

import json
import os
import sys
import logging
import psutil
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime

log = logging.getLogger("JackyAPI")

JACKY_HOME = Path(__file__).parent
SAS_UI_PATH = JACKY_HOME / "sas_ui"
TOOLS_DIR = r"E:\AI\ai-agents\tools"

# Make Jacky's client + the shared tools (ensemble, router) importable.
for p in (str(JACKY_HOME), TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

app = Flask(__name__)
CORS(app)

# ----------------------------------------------------------------------------
# LIVE AI ENGINE — local-first. Built once at import; cloud stays OFF.
# ----------------------------------------------------------------------------
ollama_client = None
ensemble = None
bot_router = None
assessor = None
resource_policy = None
CLOUD_ENABLED = False  # overridden from config.json below

def _load_cloud_flag() -> bool:
    try:
        with open(JACKY_HOME / "config.json") as f:
            cfg = json.load(f)
        return bool(cfg.get("integrations", {}).get("cloud_bots", {}).get("enabled", False))
    except Exception:
        return False

def init_engine():
    """Instantiate the real local AI engine (Ollama client, ensemble, router)."""
    global ollama_client, ensemble, bot_router, assessor, resource_policy, CLOUD_ENABLED
    try:
        from ollama_client import OllamaClient
        ollama_client = OllamaClient()
    except Exception as e:
        log.warning(f"OllamaClient unavailable: {e}")
    try:
        from ollama_ensemble import OllamaEnsemble
        ensemble = OllamaEnsemble(client=ollama_client)
    except Exception as e:
        log.warning(f"OllamaEnsemble unavailable: {e}")
    try:
        from bot_router import BotRouter
        bot_router = BotRouter()
    except Exception as e:
        log.warning(f"BotRouter unavailable: {e}")
    try:
        from resource_policy import ResourcePolicy
        resource_policy = ResourcePolicy()
    except Exception as e:
        log.warning(f"ResourcePolicy unavailable: {e}")
    try:
        from situation_assessor import SituationAssessor
        assessor = SituationAssessor(resource_policy)
    except Exception as e:
        log.warning(f"SituationAssessor unavailable: {e}")
    CLOUD_ENABLED = _load_cloud_flag()
    log.info(f"Engine ready. cloud_enabled={CLOUD_ENABLED}")

init_engine()

# Expected models from the download queue (for online/downloading display).
EXPECTED_MODELS = [
    "qwen2.5-coder:14b", "whiterabbitneo", "gpt-oss:20b",
    "nomic-embed-text", "deepseek-r1:14b", "dolphin-llama3:8b", "qwen3.5:4b",
]

# Back-compat alias; some routes/tests reference jacky_core.
jacky_core = None  # core orchestrator stays separate; API serves the engine

# Free-first multi-provider cloud router (Groq -> Gemini -> OpenRouter -> local).
cloud_router = None
try:
    from cloud_router import CloudRouter
    cloud_router = CloudRouter()
    log.info(f"CloudRouter ready. Enabled providers: {cloud_router.order}")
except Exception as e:
    log.warning(f"CloudRouter init failed: {e}")

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Redirect to dashboard."""
    return f"""
    <html>
    <head>
        <title>JACKY - AI Operations Manager</title>
        <meta http-equiv="refresh" content="0; url=/dashboard" />
    </head>
    <body>
        <p><a href="/dashboard">Redirecting to SAS Dashboard...</a></p>
    </body>
    </html>
    """

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Serve the SAS Dashboard HTML."""
    dashboard_file = SAS_UI_PATH / "dashboard.html"
    if dashboard_file.exists():
        return send_file(str(dashboard_file))
    else:
        return {"error": "Dashboard not found"}, 404

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({
        "status": "healthy",
        "service": "Jacky API",
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get current Jacky status with real system metrics."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk_e = psutil.disk_usage('E:\\')
        disk_c = psutil.disk_usage('C:\\')

        # Get temps if available (psutil rarely exposes GPU temp on Windows).
        temps = {}
        try:
            temps = psutil.sensors_temperatures()
        except Exception:
            temps = {}

        # Real GPU thermal/load from nvidia-smi via the resource policy.
        gpu = {}
        if resource_policy:
            try:
                snap = resource_policy.gpu_snapshot()
                if snap:
                    gpu = {
                        "available": True,
                        "temp_c": snap["temp_c"],
                        "load_percent": snap["util_percent"],
                        "mem_used_mb": snap["mem_used_mb"],
                        "mem_total_mb": snap["mem_total_mb"],
                        "max_temp_c": resource_policy.gpu_max_temp,
                        "thermal_margin": resource_policy.thermal_margin,
                        "headroom_c": resource_policy.thermal_headroom_c(snap),
                        "safe_to_use": resource_policy.gpu_safe_to_use(snap),
                    }
                else:
                    gpu = {"available": False}
            except Exception as e:
                log.warning(f"gpu snapshot failed: {e}")
                gpu = {"available": False}

        return jsonify({
            "status": "healthy",
            "cpu": round(cpu, 1),
            "memory": round(mem.percent, 1),
            "disk_free": f"{round(disk_e.free / (1024**3), 1)} GB",
            "disk_used_percent": round((disk_e.used / disk_e.total) * 100, 1),
            "temps": temps,
            "gpu": gpu,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e), "timestamp": datetime.now().isoformat()}), 500

@app.route('/api/bots', methods=['GET'])
def api_bots():
    """List the active named cloud backup bots (jacky, claude_jr) + their info.

    These are the only two named bots in the simplified architecture; local
    Ollama is the primary engine (see /api/models) and isn't listed here.
    """
    bots = []
    if bot_router:
        try:
            status = bot_router.get_status().get("bots", {})
            for key, info in status.items():
                bots.append({
                    "name": info.get("name", key),
                    "key": key,
                    "model": info.get("model"),
                    "provider": info.get("provider"),
                    "cost": info.get("cost"),
                    "status": "idle",  # named bots are on-demand backups
                })
        except Exception as e:
            log.warning(f"bot_router status failed: {e}")
    if not bots:
        bots = [{"name": "Jacky", "key": "jacky", "status": "idle"},
                {"name": "Claude Jr", "key": "claude_jr", "status": "idle"}]
    return jsonify({"bots": bots})


@app.route('/api/assessment', methods=['GET'])
def api_assessment():
    """Live situation assessment for the dashboard (temp/load/verdict)."""
    if not assessor:
        return jsonify({"error": "assessor unavailable",
                        "level": "unknown", "badge": "Unknown"}), 503
    try:
        report = assessor.assess()
        report["badge"] = assessor.short_status()
        report["timestamp"] = datetime.now().isoformat()
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/models', methods=['GET'])
def api_models():
    """Live local-model roster: which are online vs still expected/downloading."""
    online = []
    if ollama_client:
        try:
            online = ollama_client.list_models()
        except Exception as e:
            log.warning(f"list_models failed: {e}")
    online_names = {m["name"] for m in online}
    downloading = [name for name in EXPECTED_MODELS
                   if name not in online_names
                   and not any(o.startswith(name.split(':')[0]) for o in online_names)]
    specialties = {}
    if ensemble:
        try:
            specialties = {mid: m["specialty"]
                           for mid, m in ensemble.get_ensemble_status()["models"].items()}
        except Exception:
            specialties = {}
    for m in online:
        m["specialty"] = specialties.get(m["name"], "")
        m["state"] = "online"
    return jsonify({
        "online": online,
        "downloading": downloading,
        "count_online": len(online),
        "timestamp": datetime.now().isoformat(),
    })


def _try_cloud(prompt, chain):
    """Run the free cloud escalation tier (Groq -> Gemini -> OpenRouter).

    Returns a JSON-able dict on success, or None to keep walking the chain.
    Appends a step to `chain` describing what happened.
    """
    if not CLOUD_ENABLED:
        chain.append({"step": "cloud_free", "status": "disabled",
                      "detail": "integrations.cloud_bots.enabled is false"})
        return None
    if not cloud_router:
        chain.append({"step": "cloud_free", "status": "unavailable",
                      "detail": "cloud_router not initialized"})
        return None
    try:
        result = cloud_router.ask(prompt)
        if result.get("status") == "ok":
            chain.append({"step": "cloud_free", "status": "ok",
                          "provider": result.get("provider")})
            return {
                "engine": "cloud",
                "provider": result.get("provider"),
                "model": result.get("model"),
                "status": "ok",
                "latency_s": result.get("latency_s"),
                "response": result.get("response"),
            }
        chain.append({"step": "cloud_free", "status": "exhausted",
                      "detail": result.get("tried")})
    except Exception as e:
        chain.append({"step": "cloud_free", "status": "error", "detail": str(e)})
    return None


@app.route('/api/ask', methods=['POST'])
def api_ask():
    """Ask the AI with situation-aware routing and an explicit fallback chain.

    Body: {"prompt": "...", "task_type": "general"|"code"|"security"|...}

    Fallback chain: local -> cloud (free tier) -> forced local -> error.
    A live situation assessment gates whether local runs at all: if the GPU is
    too hot/loaded, we skip straight to the free cloud tier instead of cooking
    the card. The response reports the assessment, the chosen model, *why*, and
    every step the request walked through.
    """
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    task_type = (data.get("task_type") or "general").strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    chain = []

    # Live situation assessment (thermal/load/VRAM verdict).
    assessment = {}
    if assessor:
        try:
            assessment = assessor.assess()
        except Exception as e:
            log.warning(f"assessment error: {e}")

    # Task-complexity routing (economy brain): local vs a named cloud bot.
    target = "ollama_local"
    if bot_router:
        try:
            target = bot_router.route(task_type, priority="normal")
        except Exception as e:
            log.warning(f"router error: {e}")

    safe_local = assessment.get("safe_to_run_local", True)
    complexity_escalates = target != "ollama_local"

    # ---- Step 1: local (only if thermally safe AND task doesn't demand cloud) ----
    if ensemble and safe_local and not complexity_escalates:
        result = ensemble.query_best(prompt, task_type, respect_thermal=True)
        if result.get("status") == "ok":
            chain.append({"step": "local", "status": "ok", "model": result.get("model")})
            return jsonify({
                "route": "ollama_local",
                "engine": "local",
                "model": result.get("model"),
                "specialty": result.get("specialty"),
                "status": "ok",
                "latency_s": result.get("latency_s"),
                "response": result.get("response"),
                "why": result.get("assessment", {}).get("reason", "GPU healthy — ran local."),
                "assessment": assessment,
                "fallback_chain": chain,
            })
        if result.get("status") == "escalate":
            chain.append({"step": "local", "status": "escalate",
                          "detail": result.get("reason")})
        else:
            chain.append({"step": "local", "status": "error",
                          "detail": result.get("response") or result.get("error")})
    else:
        why = ("task complexity escalates to a cloud bot"
               if complexity_escalates else
               assessment.get("reason", "local unsafe"))
        chain.append({"step": "local", "status": "skipped", "detail": why})

    # ---- Step 2: free cloud escalation tier ----
    cloud_result = _try_cloud(prompt, chain)
    if cloud_result:
        cloud_result.update({
            "route": target if complexity_escalates else "escalated",
            "why": assessment.get("reason") if not complexity_escalates
                   else f"task '{task_type}' routed to {target}",
            "assessment": assessment,
            "fallback_chain": chain,
        })
        return jsonify(cloud_result)

    # ---- Step 3: forced local (last resort — better a warm GPU than nothing) ----
    if ensemble:
        result = ensemble.query_best(prompt, task_type, respect_thermal=False)
        if result.get("status") == "ok":
            chain.append({"step": "forced_local", "status": "ok",
                          "model": result.get("model")})
            return jsonify({
                "route": "ollama_local (forced fallback)",
                "engine": "local",
                "model": result.get("model"),
                "specialty": result.get("specialty"),
                "status": "ok",
                "latency_s": result.get("latency_s"),
                "response": result.get("response"),
                "why": "Cloud unavailable; ran local as last resort despite thermal state.",
                "assessment": assessment,
                "fallback_chain": chain,
            })
        chain.append({"step": "forced_local", "status": "error",
                      "detail": result.get("response") or result.get("error")})

    # ---- Step 4: error with explanation ----
    return jsonify({
        "status": "error",
        "engine": "none",
        "response": "All routes failed: local was unsafe/unavailable and the free "
                    "cloud tier could not answer. See fallback_chain for details.",
        "assessment": assessment,
        "fallback_chain": chain,
    }), 503

@app.route('/api/task', methods=['POST'])
def api_submit_task():
    """Submit a new task to Jacky."""
    if not jacky_core:
        return {"error": "Jacky Core not ready"}, 503

    data = request.get_json()
    if not data:
        return {"error": "No JSON data provided"}, 400

    # Simple validation
    name = data.get("name")
    if not name:
        return {"error": "Task must have a 'name'"}, 400

    # Would create a proper Task object here
    task_id = f"task_{datetime.now().timestamp()}"
    log.info(f"Task submitted via API: {name}")

    return jsonify({
        "task_id": task_id,
        "name": name,
        "status": "queued",
        "timestamp": datetime.now().isoformat()
    }), 201

@app.route('/api/config', methods=['GET'])
def api_config():
    """Get current configuration."""
    config_path = JACKY_HOME / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return jsonify(config)
    else:
        return {"error": "Config not found"}, 404

@app.route('/api/config', methods=['POST'])
def api_config_update():
    """Update configuration (admin only)."""
    data = request.get_json()
    if not data:
        return {"error": "No JSON data provided"}, 400

    config_path = JACKY_HOME / "config.json"
    try:
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        log.info("Config updated via API")
        return jsonify({"status": "updated", "timestamp": datetime.now().isoformat()}), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    """Get recent alerts."""
    # Would query database
    return jsonify({
        "alerts": [
            {
                "type": "GPU_CHECK_FAILED",
                "severity": "warning",
                "message": "RTX 3090 not responding to nvidia-smi",
                "timestamp": datetime.now().isoformat(),
                "education": "GPU drivers might need updating."
            },
            {
                "type": "DOWNLOAD_SLOW",
                "severity": "info",
                "message": "Model download at 889 KB/s (ETA ~2h37m)",
                "timestamp": datetime.now().isoformat(),
                "education": "Your VPN/security software may be slowing downloads."
            }
        ]
    })

@app.route('/api/metrics', methods=['GET'])
def api_metrics():
    """Get system metrics."""
    # Would call monitor_bot
    return jsonify({
        "cpu_percent": 45,
        "memory_percent": 62,
        "gpu_memory_used_mb": 3700,
        "gpu_memory_total_mb": 24576,
        "disk_free_gb": {
            "C": 1212,
            "E": 1810
        },
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# MAIN
# ============================================================================

def init_jacky_api(core_instance=None):
    """Initialize API with Jacky Core instance."""
    global jacky_core
    jacky_core = core_instance
    log.info("Jacky API initialized")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("Starting Jacky API server...")
    log.info("SAS Dashboard: http://localhost:5000/dashboard")
    log.info("REST API: http://localhost:5000/api/...")
    app.run(host='127.0.0.1', port=5000, debug=True)

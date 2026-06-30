#!/usr/bin/env python3
"""
JACKY REST API & SAS Dashboard Server
Serves the web UI and API endpoints for Jacky Core.
"""

import json
import os
import sys
import hmac
import secrets as _secrets
import logging
import psutil
from pathlib import Path
from functools import wraps
from flask import (Flask, jsonify, request, send_file, session,
                   redirect, Response, render_template_string)
from flask_cors import CORS
from datetime import datetime, timedelta

log = logging.getLogger("JackyAPI")

# Squad manager — loads bots/*.json at import time
try:
    from squad_manager import squad_manager
    log.info("SquadManager loaded.")
except Exception as _e:
    squad_manager = None
    log.warning(f"SquadManager unavailable: {_e}")

# Knowledge Condenser suite — wrapped, never modified. Each import is isolated
# so a failure in one condenser module can't take down the API or the others.
try:
    from bots.condenser_bot import compress as condenser_compress, CondenserBot, SPECIALIZATIONS as CONDENSER_SPECIALIZATIONS
    _condenser_bot = CondenserBot()
    log.info("CondenserBot loaded.")
except Exception as _e:
    condenser_compress = None
    CONDENSER_SPECIALIZATIONS = {}
    _condenser_bot = None
    log.warning(f"CondenserBot unavailable: {_e}")

try:
    from condenser_benchmark import run_benchmark, FrequencyCondenser
    log.info("condenser_benchmark loaded.")
except Exception as _e:
    run_benchmark = None
    FrequencyCondenser = None
    log.warning(f"condenser_benchmark unavailable: {_e}")

try:
    from condenser_adversary import single_action_impacts, greedy_attack, attack_to_probs, failure_of, ACTIONS, N_ACTIONS
    log.info("condenser_adversary loaded.")
except Exception as _e:
    single_action_impacts = None
    greedy_attack = None
    attack_to_probs = None
    failure_of = None
    ACTIONS = []
    N_ACTIONS = 0
    log.warning(f"condenser_adversary unavailable: {_e}")

JACKY_HOME = Path(__file__).parent
SAS_UI_PATH = JACKY_HOME / "sas_ui"
TOOLS_DIR = r"E:\AI\ai-agents\tools"

# Make Jacky's client + the shared tools (ensemble, router) importable.
for p in (str(JACKY_HOME), TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

app = Flask(__name__)
# Restrict CORS to trusted origins only
TRUSTED_ORIGINS = os.getenv("SAS_TRUSTED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000").split(",")
CORS(app, supports_credentials=True, origins=TRUSTED_ORIGINS)

# ----------------------------------------------------------------------------
# AUTH — protects SAS when it's exposed to the internet (Cloudflare Tunnel).
# A login token gates the dashboard + API. Auth turns ON automatically the
# moment SAS_ACCESS_TOKEN is set (in the vault or env); without it, SAS runs
# open for LAN-only use and logs a loud warning.
# ----------------------------------------------------------------------------
try:
    from secrets_loader import get_secret
except Exception:
    def get_secret(name, default=None):
        return os.getenv(name, default)

SAS_ACCESS_TOKEN = get_secret("SAS_ACCESS_TOKEN") or ""
REQUIRE_AUTH = bool(SAS_ACCESS_TOKEN.strip())

# Fail fast if exposed to internet without auth
SAS_HOST = os.getenv("SAS_HOST", "127.0.0.1")
if not REQUIRE_AUTH and SAS_HOST not in ("127.0.0.1", "localhost", "::1"):
    log.critical("FATAL: SAS_ACCESS_TOKEN is missing, but app is bound to a public interface "
                 f"({SAS_HOST}). Refusing to start in open mode on public network. "
                 "Set SAS_ACCESS_TOKEN in secrets/secrets.env or bind to 127.0.0.1.")
    sys.exit(1)

# Stable secret key so sessions survive restarts; falls back to random.
app.secret_key = (get_secret("SAS_SECRET_KEY")
                  or os.getenv("SAS_SECRET_KEY")
                  or _secrets.token_hex(32))

# Secure session cookies
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24) # Reduced from 30 days
)
app.permanent_session_lifetime = timedelta(hours=24)

# Paths reachable WITHOUT a session (login flow, health, PWA shell assets).
_OPEN_PATHS = {
    "/health", "/login", "/logout",
    "/manifest.webmanifest", "/sw.js",
    "/icon.svg", "/icon-maskable.svg", "/favicon.ico",
}

if REQUIRE_AUTH:
    log.info("AUTH ENABLED — SAS_ACCESS_TOKEN is set; login required.")
else:
    log.warning("AUTH DISABLED — no SAS_ACCESS_TOKEN set. SAS is OPEN. "
                "Set SAS_ACCESS_TOKEN in the vault before exposing to the internet.")


@app.before_request
def _gate():
    """Block unauthenticated access when auth is enabled."""
    if not REQUIRE_AUTH:
        return None
    path = request.path.rstrip("/") or "/"
    if path in _OPEN_PATHS:
        return None
    if session.get("authed"):
        return None
    # API callers get a clean 401; browsers get the login page.
    if path.startswith("/api"):
        return jsonify({"error": "unauthorized", "login": "/login"}), 401
    return redirect("/login")


# ----------------------------------------------------------------------------
# RATE LIMITER — lightweight, dependency-free, in-process sliding window.
# Used to gate compute-heavy / arbitrary-input endpoints (e.g. condenser
# compression, benchmark, adversary simulation) against abuse/DoS, since
# this app is internet-exposed via the Cloudflare Tunnel.
# ----------------------------------------------------------------------------
import threading as _threading
from collections import deque as _deque

_rate_lock = _threading.Lock()
_rate_buckets = {}

def rate_limit(max_calls=20, window_seconds=60):
    """Decorator: caps calls per (client identity, endpoint) within a sliding window."""
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            ident = request.remote_addr or "anon"
            key = (ident, fn.__name__)
            now = datetime.utcnow().timestamp()
            with _rate_lock:
                bucket = _rate_buckets.setdefault(key, _deque())
                while bucket and now - bucket[0] > window_seconds:
                    bucket.popleft()
                if len(bucket) >= max_calls:
                    retry_after = max(1, int(window_seconds - (now - bucket[0])))
                    return jsonify({"error": "rate_limited",
                                    "message": f"Too many requests. Retry in {retry_after}s.",
                                    "retry_after": retry_after}), 429
                bucket.append(now)
            return fn(*args, **kwargs)
        return wrapped
    return decorator

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

# ----------------------------------------------------------------------------
# RUNTIME CONTROLS — the master switches the SAS dashboard drives.
#   active        : master on/off for the whole AI team. When False, /api/ask
#                   refuses to run anything (the team is "stood down").
#   thinking_mode : default depth for requests that don't specify one —
#                   "fast" | "balanced" | "deep".
# Persisted to config.json so the choice survives restarts.
# ----------------------------------------------------------------------------
VALID_MODES = ("fast", "balanced", "deep")
RUNTIME = {"active": True, "thinking_mode": "balanced"}

def _load_runtime():
    try:
        with open(JACKY_HOME / "config.json") as f:
            cfg = json.load(f)
        rc = cfg.get("runtime_controls", {})
        if isinstance(rc.get("active"), bool):
            RUNTIME["active"] = rc["active"]
        if rc.get("thinking_mode") in VALID_MODES:
            RUNTIME["thinking_mode"] = rc["thinking_mode"]
    except Exception:
        pass

def _save_runtime():
    try:
        path = JACKY_HOME / "config.json"
        cfg = {}
        if path.exists():
            with open(path) as f:
                cfg = json.load(f)
        cfg["runtime_controls"] = dict(RUNTIME)
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log.warning(f"could not persist runtime controls: {e}")

_load_runtime()

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


@app.route('/chat', methods=['GET'])
def chat_page():
    """Cursor-style multi-agent chat UI."""
    chat_file = SAS_UI_PATH / "chat.html"
    if chat_file.exists():
        return send_file(str(chat_file))
    return jsonify({"error": "Chat UI not found"}), 404


@app.route('/health', methods=['GET'])
def health():
    """Health check (always open — used by the tunnel + uptime checks)."""
    return jsonify({
        "status": "healthy",
        "service": "Jacky API",
        "auth": "enabled" if REQUIRE_AUTH else "disabled",
        "timestamp": datetime.now().isoformat()
    })

# ----------------------------------------------------------------------------
# AUTH ROUTES
# ----------------------------------------------------------------------------
_LOGIN_HTML = """<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>SAS — Sign in</title>
<link rel=manifest href=/manifest.webmanifest>
<meta name=theme-color content=#0a0e27>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:linear-gradient(135deg,#0a0e27,#1a2744);
color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:rgba(0,50,100,.25);border:1px solid rgba(0,212,255,.25);border-radius:16px;
padding:36px 28px;width:100%;max-width:360px;backdrop-filter:blur(10px)}
h1{font-size:22px;margin-bottom:6px;display:flex;align-items:center;gap:10px}
.sub{font-size:13px;color:#8aa;margin-bottom:24px}
label{font-size:12px;color:#9bd;display:block;margin-bottom:6px}
input{width:100%;background:rgba(0,0,0,.3);border:1px solid rgba(0,212,255,.3);color:#e0e0e0;
padding:12px;border-radius:8px;font-size:16px;margin-bottom:16px}
input:focus{outline:none;border-color:#00d4ff}
button{width:100%;background:linear-gradient(90deg,#00d4ff,#0099ff);border:none;color:#06223a;
padding:13px;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer}
button:active{transform:scale(.98)}
.err{color:#ff8a8a;font-size:13px;margin-bottom:14px;{{ 'display:block' if error else 'display:none' }}}
.logo{width:34px;height:34px;vertical-align:middle}
</style></head><body>
<form class=card method=POST action=/login>
<h1><img class=logo src=/icon.svg alt="">SAS</h1>
<div class=sub>Situational Awareness · Jacky's PC</div>
<div class=err>Wrong access token. Try again.</div>
<label for=token>Access token</label>
<input id=token name=token type=password autocomplete=current-password autofocus
placeholder="paste your token" inputmode=text>
<button type=submit>Sign in</button>
</form></body></html>"""


import time as _time

# Basic rate limiting for login
_login_attempts = {}

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Token login. GET shows the form; POST validates and starts a session."""
    if not REQUIRE_AUTH:
        return redirect("/dashboard")
        
    client_ip = request.remote_addr
    now = _time.time()
    
    # Clean up old attempts
    for ip in list(_login_attempts.keys()):
        if now - _login_attempts[ip]['time'] > 300: # 5 min
            del _login_attempts[ip]
            
    if client_ip in _login_attempts and _login_attempts[client_ip]['count'] >= 5:
        if now - _login_attempts[client_ip]['time'] < 60: # 1 min lockout
            return "Too many attempts, try again later.", 429
            
    error = False
    if request.method == 'POST':
        supplied = (request.form.get("token") or "").strip()
        if hmac.compare_digest(supplied, SAS_ACCESS_TOKEN):
            session.permanent = True
            session["authed"] = True
            if client_ip in _login_attempts:
                del _login_attempts[client_ip]
            return redirect("/dashboard")
        
        # Track failed attempt
        if client_ip not in _login_attempts:
            _login_attempts[client_ip] = {'count': 0, 'time': now}
        _login_attempts[client_ip]['count'] += 1
        _login_attempts[client_ip]['time'] = now
        
        error = True
    return render_template_string(_LOGIN_HTML, error=error), (401 if error else 200)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect("/login")

# ----------------------------------------------------------------------------
# PWA ROUTES — make SAS installable as a phone/desktop app
# ----------------------------------------------------------------------------
@app.route('/manifest.webmanifest', methods=['GET'])
def manifest():
    data = {
        "name": "SAS — Jacky Situational Awareness",
        "short_name": "SAS",
        "description": "Live GPU/AI situational awareness for Jacky's PC.",
        "start_url": "/dashboard",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#0a0e27",
        "theme_color": "#0a0e27",
        "icons": [
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
            {"src": "/icon-maskable.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
        ],
    }
    return Response(json.dumps(data), mimetype="application/manifest+json")


@app.route('/sw.js', methods=['GET'])
def service_worker():
    f = SAS_UI_PATH / "sw.js"
    if f.exists():
        resp = send_file(str(f), mimetype="application/javascript")
        resp.headers["Service-Worker-Allowed"] = "/"
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    return Response("// sw missing", mimetype="application/javascript")


@app.route('/icon.svg', methods=['GET'])
def icon_svg():
    f = SAS_UI_PATH / "icon.svg"
    return send_file(str(f), mimetype="image/svg+xml") if f.exists() else ("", 404)


@app.route('/icon-maskable.svg', methods=['GET'])
def icon_maskable():
    f = SAS_UI_PATH / "icon-maskable.svg"
    return send_file(str(f), mimetype="image/svg+xml") if f.exists() else ("", 404)


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    f = SAS_UI_PATH / "icon.svg"
    return send_file(str(f), mimetype="image/svg+xml") if f.exists() else ("", 404)

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


def _build_agent_roster() -> list:
    """Unified list of selectable AIs for the chat UI."""
    agents = [{
        "id": "auto",
        "name": "Auto (Jacky Router)",
        "type": "router",
        "cost": "free",
        "available": True,
        "description": "Local-first routing with thermal safety",
    }]
    specialties = {}
    if ensemble:
        try:
            specialties = {mid: m.get("specialty", "")
                           for mid, m in ensemble.get_ensemble_status()["models"].items()}
        except Exception:
            pass
    if ollama_client:
        try:
            for m in ollama_client.list_models():
                name = m["name"]
                agents.append({
                    "id": f"local:{name}",
                    "name": name,
                    "type": "local",
                    "cost": "free",
                    "available": True,
                    "specialty": specialties.get(name, ""),
                    "size_gb": m.get("size_gb"),
                })
        except Exception as e:
            log.warning(f"agent roster local models failed: {e}")
    if cloud_router:
        for info in cloud_router.available():
            provider = info["provider"]
            agents.append({
                "id": f"cloud:{provider}",
                "name": provider.title(),
                "type": "cloud",
                "cost": "free",
                "available": bool(info.get("has_keys")),
                "description": f"Free cloud tier ({provider})",
            })
    if bot_router:
        try:
            for key, info in bot_router.get_status().get("bots", {}).items():
                agents.append({
                    "id": f"bot:{key}",
                    "name": info.get("name", key),
                    "type": "bot",
                    "cost": info.get("cost", "unknown"),
                    "available": True,
                    "model": info.get("model"),
                    "provider": info.get("provider"),
                })
        except Exception as e:
            log.warning(f"agent roster bots failed: {e}")
    return agents


def _chat_messages_for_api(messages: list) -> list:
    """Normalize chat history to role/content pairs Ollama accepts."""
    out = []
    for m in messages or []:
        role = (m.get("role") or "user").lower()
        if role not in ("user", "assistant", "system"):
            continue
        content = (m.get("content") or "").strip()
        if content:
            out.append({"role": role, "content": content})
    return out


def _last_user_text(messages: list) -> str:
    for m in reversed(messages or []):
        if (m.get("role") or "").lower() == "user":
            return (m.get("content") or "").strip()
    return ""


def _cloud_chat(provider: str, messages: list) -> dict:
    """Run a cloud provider with full message history."""
    import time
    from cloud_client import CloudClient, CloudError
    from secrets_loader import get_keys
    from cloud_router import PROVIDER_KEYS

    keys = get_keys(PROVIDER_KEYS.get(provider, []))
    if not keys:
        return {"agent_id": f"cloud:{provider}", "status": "error",
                "response": f"No API keys for {provider}"}
    client = CloudClient(provider, keys)
    start = time.time()
    try:
        # Build multi-turn prompt for providers that only get a single user turn.
        lines = []
        for m in _chat_messages_for_api(messages):
            prefix = m["role"].capitalize()
            lines.append(f"{prefix}: {m['content']}")
        prompt = "\n\n".join(lines) if lines else ""
        if not prompt:
            return {"agent_id": f"cloud:{provider}", "status": "error",
                    "response": "No messages to send"}
        text = client.generate(prompt)
        return {
            "agent_id": f"cloud:{provider}",
            "agent_name": provider.title(),
            "engine": "cloud",
            "provider": provider,
            "model": client.model,
            "status": "ok",
            "response": text,
            "latency_s": round(time.time() - start, 2),
        }
    except CloudError as e:
        return {
            "agent_id": f"cloud:{provider}",
            "status": "error",
            "response": str(e),
            "latency_s": round(time.time() - start, 2),
        }


def _chat_with_agent(agent_id: str, messages: list, mode: str) -> dict:
    """Send conversation history to one specific agent."""
    import time
    agent_id = (agent_id or "auto").strip()
    msgs = _chat_messages_for_api(messages)
    if not msgs:
        return {"agent_id": agent_id, "status": "error", "response": "No messages"}

    if agent_id == "auto":
        prompt = _last_user_text(msgs)
        data, _code = _run_ask(prompt, "general", mode)
        return {
            "agent_id": "auto",
            "agent_name": "Auto (Jacky Router)",
            "engine": data.get("engine", "unknown"),
            "model": data.get("model"),
            "provider": data.get("provider"),
            "status": data.get("status", "error"),
            "response": data.get("response", ""),
            "why": data.get("why"),
            "latency_s": data.get("latency_s"),
            "fallback_chain": data.get("fallback_chain"),
        }

    if agent_id.startswith("local:"):
        model = agent_id[6:]
        if not ollama_client:
            return {"agent_id": agent_id, "status": "error", "response": "Ollama unavailable"}
        start = time.time()
        try:
            text = ollama_client.chat(model, msgs)
            return {
                "agent_id": agent_id,
                "agent_name": model,
                "engine": "local",
                "model": model,
                "status": "ok",
                "response": text,
                "latency_s": round(time.time() - start, 2),
            }
        except Exception as e:
            return {
                "agent_id": agent_id,
                "status": "error",
                "response": str(e),
                "latency_s": round(time.time() - start, 2),
            }

    if agent_id.startswith("cloud:"):
        provider = agent_id[6:]
        return _cloud_chat(provider, msgs)

    if agent_id.startswith("bot:"):
        key = agent_id[4:]
        prompt = _last_user_text(msgs)
        if bot_router:
            try:
                target = bot_router.route(key, priority="normal")
            except Exception:
                target = key
        else:
            target = key
        if target == "ollama_local" and ensemble:
            result = ensemble.query_best(prompt, "general", respect_thermal=True, mode=mode)
            return {
                "agent_id": agent_id,
                "agent_name": key,
                "engine": "local",
                "model": result.get("model"),
                "status": result.get("status", "error"),
                "response": result.get("response", ""),
                "latency_s": result.get("latency_s"),
            }
        cloud = _try_cloud(prompt, [])
        if cloud:
            cloud["agent_id"] = agent_id
            cloud["agent_name"] = key
            return cloud
        return {"agent_id": agent_id, "status": "error", "response": "Bot route failed"}

    return {"agent_id": agent_id, "status": "error", "response": f"Unknown agent: {agent_id}"}


@app.route('/api/agents', methods=['GET'])
def api_agents():
    """All AIs the chat UI can pick or add to a conversation."""
    return jsonify({
        "agents": _build_agent_roster(),
        "timestamp": datetime.now().isoformat(),
    })


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Multi-turn chat with explicit agent selection or multi-agent replies.

    Body:
      messages: [{role, content}, ...]
      agent_id: "auto" | "local:model" | "cloud:groq" | "bot:jacky"  (active agent)
      agents:   optional list — when len>1, every agent replies to the last turn
      mode:     fast | balanced | deep
    """
    if not RUNTIME["active"]:
        return jsonify({
            "status": "paused",
            "response": "AI team is PAUSED. Resume from the dashboard or chat header.",
        }), 200

    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    mode = (data.get("mode") or RUNTIME["thinking_mode"]).lower()
    if mode not in VALID_MODES:
        mode = RUNTIME["thinking_mode"]

    multi = data.get("agents") or []
    if len(multi) > 1:
        results = [_chat_with_agent(aid, messages, mode) for aid in multi]
        ok = any(r.get("status") == "ok" for r in results)
        return jsonify({
            "status": "ok" if ok else "error",
            "multi": True,
            "responses": results,
            "timestamp": datetime.now().isoformat(),
        })

    agent_id = data.get("agent_id") or (multi[0] if multi else "auto")
    result = _chat_with_agent(agent_id, messages, mode)
    result["timestamp"] = datetime.now().isoformat()
    status_code = 200 if result.get("status") in ("ok", "paused") else 503
    return jsonify(result), status_code


@app.route('/api/control', methods=['GET', 'POST'])
def api_control():
    """Read or set the master runtime controls (active switch + thinking mode).

    GET  -> {"active": bool, "thinking_mode": "fast|balanced|deep"}
    POST -> body may include {"active": bool} and/or {"thinking_mode": "..."}.
            Returns the updated state. Persists to config.json.
    """
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if isinstance(data.get("active"), bool):
            RUNTIME["active"] = data["active"]
        mode = (data.get("thinking_mode") or "").lower()
        if mode in VALID_MODES:
            RUNTIME["thinking_mode"] = mode
        _save_runtime()
        log.info(f"Runtime controls updated: {RUNTIME}")
    return jsonify({**RUNTIME, "valid_modes": list(VALID_MODES),
                    "timestamp": datetime.now().isoformat()})


@app.route('/api/ask', methods=['POST'])
def api_ask():
    """Ask the AI with situation-aware routing and an explicit fallback chain."""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    task_type = (data.get("task_type") or "general").strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    if not RUNTIME["active"]:
        return jsonify({
            "status": "paused",
            "engine": "none",
            "response": "🛑 AI team is PAUSED. Flip the Active switch in the SAS "
                        "Power Panel to resume.",
            "active": False,
            "fallback_chain": [{"step": "master_switch", "status": "paused"}],
        }), 200

    mode = (data.get("mode") or data.get("thinking_mode") or "").lower()
    if mode not in VALID_MODES:
        mode = RUNTIME["thinking_mode"]

    result, code = _run_ask(prompt, task_type, mode)
    return jsonify(result), code


def _run_ask(prompt: str, task_type: str, mode: str):
    """Core ask logic — returns (response_dict, http_status)."""
    chain = []

    assessment = {}
    if assessor:
        try:
            assessment = assessor.assess()
        except Exception as e:
            log.warning(f"assessment error: {e}")

    target = "ollama_local"
    if bot_router:
        try:
            target = bot_router.route(task_type, priority="normal")
        except Exception as e:
            log.warning(f"router error: {e}")

    safe_local = assessment.get("safe_to_run_local", True)
    complexity_escalates = target != "ollama_local"

    if ensemble and safe_local and not complexity_escalates:
        result = ensemble.query_best(prompt, task_type, respect_thermal=True, mode=mode)
        if result.get("status") == "ok":
            chain.append({"step": "local", "status": "ok", "model": result.get("model")})
            return ({
                "route": "ollama_local",
                "engine": "local",
                "model": result.get("model"),
                "specialty": result.get("specialty"),
                "status": "ok",
                "thinking_mode": mode,
                "latency_s": result.get("latency_s"),
                "response": result.get("response"),
                "why": result.get("assessment", {}).get("reason", "GPU healthy — ran local."),
                "assessment": assessment,
                "fallback_chain": chain,
            }, 200)
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

    cloud_result = _try_cloud(prompt, chain)
    if cloud_result:
        cloud_result.update({
            "route": target if complexity_escalates else "escalated",
            "why": assessment.get("reason") if not complexity_escalates
                   else f"task '{task_type}' routed to {target}",
            "assessment": assessment,
            "fallback_chain": chain,
        })
        return (cloud_result, 200)

    if ensemble:
        result = ensemble.query_best(prompt, task_type, respect_thermal=False, mode=mode)
        if result.get("status") == "ok":
            chain.append({"step": "forced_local", "status": "ok",
                          "model": result.get("model")})
            return ({
                "route": "ollama_local (forced fallback)",
                "engine": "local",
                "model": result.get("model"),
                "specialty": result.get("specialty"),
                "thinking_mode": mode,
                "status": "ok",
                "latency_s": result.get("latency_s"),
                "response": result.get("response"),
                "why": "Cloud unavailable; ran local as last resort despite thermal state.",
                "assessment": assessment,
                "fallback_chain": chain,
            }, 200)
        chain.append({"step": "forced_local", "status": "error",
                      "detail": result.get("response") or result.get("error")})

    return ({
        "status": "error",
        "engine": "none",
        "response": "All routes failed: local was unsafe/unavailable and the free "
                    "cloud tier could not answer. See fallback_chain for details.",
        "assessment": assessment,
        "fallback_chain": chain,
    }, 503)

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
# HUB PAGE
# ============================================================================

@app.route('/hub', methods=['GET'])
def hub():
    """Three-panel command center: squad roster | chat | SAS stats."""
    hub_file = SAS_UI_PATH / "hub.html"
    if hub_file.exists():
        return send_file(str(hub_file))
    return jsonify({"error": "Hub UI not found — build hub.html first"}), 404

# ============================================================================
# CONDENSER SUITE
# Wraps bots/condenser_bot.py, condenser_benchmark.py and condenser_adversary.py
# as pages + JSON APIs, without changing a single line of their logic. Every
# route here is already covered by the global auth gate (_gate, above) since
# none of these paths appear in _OPEN_PATHS. Compute-heavy / arbitrary-input
# endpoints are additionally rate-limited and size-capped against abuse.
# ============================================================================

CONDENSER_MAX_INPUT_CHARS = 20000  # hard cap on text submitted for compression


@app.route('/condenser', methods=['GET'])
def condenser_page():
    """Condenser Bot console — live compression of knowledge signals."""
    f = SAS_UI_PATH / "condenser.html"
    if f.exists():
        return send_file(str(f))
    return jsonify({"error": "Condenser UI not found"}), 404


@app.route('/condenser/benchmark', methods=['GET'])
def condenser_benchmark_page():
    """Condenser Benchmark scorecard (graph reconstruction, invariants, etc.)."""
    f = SAS_UI_PATH / "condenser_benchmark.html"
    if f.exists():
        return send_file(str(f))
    return jsonify({"error": "Condenser benchmark UI not found"}), 404


@app.route('/condenser/adversary', methods=['GET'])
def condenser_adversary_page():
    """Adversarial co-evolution — brittleness map + learned-attack results."""
    f = SAS_UI_PATH / "condenser_adversary.html"
    if f.exists():
        return send_file(str(f))
    return jsonify({"error": "Condenser adversary UI not found"}), 404


@app.route('/api/condenser/specializations', methods=['GET'])
def api_condenser_specializations():
    """Available condenser specializations (density + symbolic tag)."""
    if not condenser_compress:
        return jsonify({"error": "condenser bot unavailable"}), 503
    return jsonify({"specializations": CONDENSER_SPECIALIZATIONS})


@app.route('/api/condenser/compress', methods=['POST'])
@rate_limit(max_calls=20, window_seconds=60)
def api_condenser_compress():
    """Run the live knowledge condenser on submitted text (bots/condenser_bot.py)."""
    if not condenser_compress or not _condenser_bot:
        return jsonify({"error": "condenser bot unavailable"}), 503
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "text is required"}), 400
    if len(text) > CONDENSER_MAX_INPUT_CHARS:
        return jsonify({"error": f"text exceeds {CONDENSER_MAX_INPUT_CHARS} character limit"}), 413
    specialization = data.get("specialization", "baseline")
    if specialization not in CONDENSER_SPECIALIZATIONS:
        specialization = "baseline"
    try:
        density = int(data.get("density", 0))
    except (TypeError, ValueError):
        density = 0
    density = max(0, min(100, density))
    save = bool(data.get("save", True))
    try:
        result = condenser_compress(text, density, specialization)
        if save:
            result["star_id"] = _condenser_bot.save_star(result, text)
        return jsonify(result)
    except Exception as e:
        log.exception("condenser compress failed")
        return jsonify({"error": "compression failed"}), 500


@app.route('/api/condenser/stars', methods=['GET'])
@rate_limit(max_calls=60, window_seconds=60)
def api_condenser_stars():
    """List previously saved condenser 'stars' from data/condensers.db."""
    if not _condenser_bot:
        return jsonify({"error": "condenser bot unavailable"}), 503
    specialization = request.args.get("specialization") or None
    if specialization and specialization not in CONDENSER_SPECIALIZATIONS:
        return jsonify({"error": "unknown specialization"}), 400
    try:
        limit = max(1, min(100, int(request.args.get("limit", 20))))
    except ValueError:
        limit = 20
    try:
        return jsonify({"stars": _condenser_bot.list_stars(specialization, limit)})
    except Exception:
        log.exception("condenser list_stars failed")
        return jsonify({"error": "could not list stars"}), 500


@app.route('/api/condenser/benchmark', methods=['GET'])
@rate_limit(max_calls=10, window_seconds=60)
def api_condenser_benchmark():
    """Run condenser_benchmark.run_benchmark() with bounded, safe parameters."""
    if not run_benchmark:
        return jsonify({"error": "condenser benchmark unavailable"}), 503
    try:
        samples = max(20, min(300, int(request.args.get("samples", 200))))
    except ValueError:
        samples = 200
    try:
        seed = int(request.args.get("seed", 0)) & 0xFFFFFFFF
    except ValueError:
        seed = 0
    try:
        results = run_benchmark(FrequencyCondenser, n_samples=samples, seed=seed)
        # JSON object keys must be strings; per_noise is keyed by float noise levels.
        results["per_noise"] = {str(k): v for k, v in results["per_noise"].items()}
        return jsonify(results)
    except Exception:
        log.exception("condenser benchmark failed")
        return jsonify({"error": "benchmark run failed"}), 500


@app.route('/api/condenser/adversary', methods=['GET'])
@rate_limit(max_calls=5, window_seconds=60)
def api_condenser_adversary():
    """Run the adversarial co-evolution layer with bounded, safe parameters."""
    if not single_action_impacts:
        return jsonify({"error": "condenser adversary unavailable"}), 503
    import random as _random
    try:
        budget = max(1, min(5, int(request.args.get("budget", 3))))
    except ValueError:
        budget = 3
    try:
        keep = max(0.05, min(0.9, float(request.args.get("keep", 0.30))))
    except ValueError:
        keep = 0.30
    kw = dict(keep=keep)
    try:
        base, rows = single_action_impacts(**kw)
        chosen, learned_fail, gains = greedy_attack(budget=budget, **kw)
        _, learned_ef, learned_iv = failure_of(chosen, **kw)
        attack_names = [f"{ACTIONS[i][0]} {ACTIONS[i][1][0]}->{ACTIONS[i][1][1]}" for i in chosen]
        rand_fs = []
        rng = _random.Random(7)
        for _ in range(10):
            rc = rng.sample(range(N_ACTIONS), len(chosen)) if chosen else []
            rand_fs.append(failure_of(rc, **kw)[0])
        rand_fail = (sum(rand_fs) / len(rand_fs)) if rand_fs else 0.0
        return jsonify({
            "no_attack_failure": round(base, 3),
            "brittleness_map": [
                {"kind": r["kind"], "edge": f"{r['edge'][0]}->{r['edge'][1]}",
                 "impact": round(r["impact"], 3)} for r in rows
            ],
            "greedy_attack": attack_names,
            "marginal_gains": [round(g, 3) for g in gains],
            "learned_failure": round(learned_fail, 3),
            "random_failure": round(rand_fail, 3),
            "learning_advantage": round(learned_fail - rand_fail, 3),
        })
    except Exception:
        log.exception("condenser adversary failed")
        return jsonify({"error": "adversary run failed"}), 500

# ============================================================================
# SQUAD API
# ============================================================================

@app.route('/api/squads', methods=['GET'])
def api_squads():
    """Return all squads and their bot rosters."""
    if not squad_manager:
        return jsonify({"error": "SquadManager unavailable"}), 503
    return jsonify({
        "squads": squad_manager.all_squads(),
        "timestamp": datetime.now().isoformat(),
    })


@app.route('/api/squads/bots', methods=['GET'])
def api_squads_bots():
    """Flat list of all bots across all squads."""
    if not squad_manager:
        return jsonify({"error": "SquadManager unavailable"}), 503
    return jsonify({
        "bots": squad_manager.all_bots(),
        "timestamp": datetime.now().isoformat(),
    })


@app.route('/api/squads/<squad>/ask', methods=['POST'])
def api_squad_ask(squad: str):
    """Route to the squad's lead bot only (single response with memory)."""
    if not RUNTIME["active"]:
        return jsonify({"status": "paused",
                        "response": "AI team is PAUSED."}), 200
    if not squad_manager:
        return jsonify({"error": "SquadManager unavailable"}), 503

    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    mode = (data.get("mode") or RUNTIME["thinking_mode"]).lower()
    if mode not in VALID_MODES:
        mode = RUNTIME["thinking_mode"]

    lead = squad_manager.get_lead(squad)
    if not lead:
        return jsonify({"error": f"Unknown squad: {squad}"}), 404

    # Build the user prompt for memory retrieval
    user_prompt = ""
    for m in reversed(messages):
        if (m.get("role") or "").lower() == "user":
            user_prompt = (m.get("content") or "").strip()
            break

    # Inject memory + personality into messages as system prefix
    system_text = squad_manager.build_system_prompt(lead, user_prompt)
    augmented = [{"role": "system", "content": system_text}] + list(messages)

    result = _chat_with_agent(lead.model_preference or "auto", augmented, mode)
    result.update({
        "bot_id":   lead.id,
        "bot_name": lead.name,
        "squad":    squad,
        "memory_injected": lead.memory_enabled,
        "timestamp": datetime.now().isoformat(),
    })
    status_code = 200 if result.get("status") in ("ok", "paused") else 503
    return jsonify(result), status_code


@app.route('/api/squads/<squad>/discuss', methods=['POST'])
def api_squad_discuss(squad: str):
    """All squad members reply to the last user message (multi-agent mode)."""
    if not RUNTIME["active"]:
        return jsonify({"status": "paused",
                        "response": "AI team is PAUSED."}), 200
    if not squad_manager:
        return jsonify({"error": "SquadManager unavailable"}), 503

    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    mode = (data.get("mode") or RUNTIME["thinking_mode"]).lower()
    if mode not in VALID_MODES:
        mode = RUNTIME["thinking_mode"]

    bots = squad_manager.get_squad(squad)
    if not bots:
        return jsonify({"error": f"Unknown or empty squad: {squad}"}), 404

    user_prompt = ""
    for m in reversed(messages):
        if (m.get("role") or "").lower() == "user":
            user_prompt = (m.get("content") or "").strip()
            break

    responses = []
    for bot in bots:
        if not bot.active:
            continue
        system_text = squad_manager.build_system_prompt(bot, user_prompt)
        augmented = [{"role": "system", "content": system_text}] + list(messages)
        result = _chat_with_agent(bot.model_preference or "auto", augmented, mode)
        result.update({
            "bot_id":   bot.id,
            "bot_name": bot.name,
            "color":    bot.color,
        })
        responses.append(result)

    ok = any(r.get("status") == "ok" for r in responses)
    return jsonify({
        "status":    "ok" if ok else "error",
        "multi":     True,
        "squad":     squad,
        "responses": responses,
        "timestamp": datetime.now().isoformat(),
    })


@app.route('/api/squads/reload', methods=['POST'])
def api_squads_reload():
    """Hot-reload bot configs from bots/*.json without restarting."""
    if not squad_manager:
        return jsonify({"error": "SquadManager unavailable"}), 503
    squad_manager.reload()
    return jsonify({"status": "reloaded",
                    "bots": len(squad_manager.all_bots()),
                    "timestamp": datetime.now().isoformat()})

# ============================================================================
# SHELL API — whitelisted PowerShell execution
# ============================================================================

import subprocess, re as _re, shlex as _shlex

_SHELL_WHITELIST = [
    r"^Get-",
    r"^ls\b", r"^dir\b", r"^cat\b",
    r"^ollama\b",
    r"^git (status|log|diff|branch|show)\b",
    r"^nvidia-smi\b",
    r"^netstat\b", r"^ipconfig\b",
    r"^tasklist\b", r"^Get-Process\b",
    r"^echo\b", r"^Write-Host\b",
    r"^Select-Object\b", r"^Where-Object\b", r"^Sort-Object\b",
    r"^Get-Content\b", r"^Test-Path\b", r"^Resolve-Path\b",
]

_SHELL_BLOCK = [
    r"Remove-Item", r"rm\b", r"del\b", r"rd\b",
    r"format\b", r"reg\s+add", r"reg\s+delete",
    r"netsh\s+(add|delete|set)",
    r"Set-ExecutionPolicy",
    r"Invoke-Expression", r"iex\b",
    r"DownloadFile", r"WebClient",
    r"Start-Process.*-Verb\s*RunAs",
    r"shutdown", r"restart-computer",
]

def _shell_allowed(command: str) -> tuple[bool, str]:
    cmd = command.strip()
    for pattern in _SHELL_BLOCK:
        if _re.search(pattern, cmd, _re.IGNORECASE):
            return False, f"Blocked: matches deny-list pattern '{pattern}'"
    for pattern in _SHELL_WHITELIST:
        if _re.search(pattern, cmd, _re.IGNORECASE):
            return True, "ok"
    return False, "Not in allow-list. Add it to _SHELL_WHITELIST in jacky_api.py."


@app.route('/api/shell', methods=['POST'])
def api_shell():
    """Execute a whitelisted PowerShell command and return output."""
    if not REQUIRE_AUTH and not session.get("authed"):
        pass  # Open SAS — allow
    elif REQUIRE_AUTH and not session.get("authed"):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    command = (data.get("command") or "").strip()
    if not command:
        return jsonify({"error": "command is required"}), 400

    allowed, reason = _shell_allowed(command)
    if not allowed:
        return jsonify({
            "status": "blocked",
            "command": command,
            "reason": reason,
        }), 403

    try:
        result = subprocess.run(
            ["powershell", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=30
        )
        return jsonify({
            "status":    "ok",
            "command":   command,
            "stdout":    result.stdout[:8000],
            "stderr":    result.stderr[:2000],
            "exit_code": result.returncode,
            "timestamp": datetime.now().isoformat(),
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "command": command,
                        "error": "Command timed out (30s limit)"}), 408
    except Exception as e:
        return jsonify({"status": "error", "command": command,
                        "error": str(e)}), 500

# ============================================================================
# SAS COMMS — Claude Code personality gating
# ============================================================================

@app.route('/api/sas-comms/activate', methods=['POST'])
def sas_comms_activate():
    """Activate SAS communications intelligence mode (enables Claude Code)."""
    session["sas_comms"] = True
    log.info("SAS comms mode activated for this session.")
    return jsonify({"status": "active", "claude_code_enabled": True,
                    "timestamp": datetime.now().isoformat()})


@app.route('/api/sas-comms/status', methods=['GET'])
def sas_comms_status():
    return jsonify({
        "active": bool(session.get("sas_comms")),
        "timestamp": datetime.now().isoformat(),
    })

# ============================================================================
# DATA COLLECTOR — background asset collection & refinement endpoints.
# Wired in with a guard so a collector import error can't take down the API.
# All /api/collector/* routes are protected by the global auth gate above.
# ============================================================================
try:
    from data_collector import register_collector_routes
    register_collector_routes(app)
    log.info("Data collector routes registered (/api/collector/*).")
except Exception as e:
    log.warning(f"Data collector routes unavailable: {e}")

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
    # Bind to all interfaces by default so the Cloudflare Tunnel (and LAN) can
    # reach it. Debug is OFF for safety. For a hardened production run use
    # serve.py (waitress). Override with SAS_HOST / SAS_PORT.
    host = os.getenv("SAS_HOST", "0.0.0.0")
    port = int(os.getenv("SAS_PORT", "5000"))
    log.info("Starting Jacky API server (dev/Flask)...")
    log.info(f"SAS Dashboard: http://localhost:{port}/dashboard")
    log.info(f"Auth: {'ENABLED' if REQUIRE_AUTH else 'DISABLED (LAN only!)'}")
    app.run(host=host, port=port, debug=False)

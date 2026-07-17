"""
condenser_bot.py - Knowledge Condenser Bot for Jacky
Plugs into bots/ directory. Auto-discovered by jacky_core.py.
Pure offline compression of knowledge signals into structured stars.
"""
import re, json, sqlite3, asyncio
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "condensers.db"

SPECIALIZATIONS = {
    "baseline":     {"density": 50, "symbol": "sun"},
    "coding":       {"density": 85, "symbol": "mars"},
    "security":     {"density": 90, "symbol": "vulcan"},
    "emotion":      {"density": 40, "symbol": "venus"},
    "semantic":     {"density": 75, "symbol": "neptune"},
    "dialog":       {"density": 50, "symbol": "mercury"},
    "memory":       {"density": 60, "symbol": "saturn"},
    "analysis":     {"density": 80, "symbol": "chiron"},
    "language":     {"density": 65, "symbol": "mercury2"},
    "tracking":     {"density": 55, "symbol": "mars2"},
    "relationship": {"density": 45, "symbol": "pluto"},
    "orchestration":{"density": 70, "symbol": "uranus"},
}

SECURITY_KW = ["security","threat","vulnerability","protect","hack","encrypt","auth","firewall","attack"]
CODE_KW     = ["function","class","module","api","code","algorithm","debug","deploy","error","import"]
EMOTION_KW  = ["feel","emotion","love","pain","joy","anger","sad","happy","peace","calm","fear","hope"]
CONTRAST_KW = ["but","however","yet","although","despite","whereas","though","still"]


def detect_domain(text):
    lower = text.lower()
    scores = {
        "security": sum(1 for k in SECURITY_KW if k in lower),
        "coding":   sum(1 for k in CODE_KW if k in lower),
        "emotion":  sum(1 for k in EMOTION_KW if k in lower),
        "conflict": sum(1 for k in CONTRAST_KW if k in lower),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def compress(text, density=75, specialization="baseline"):
    spec = SPECIALIZATIONS.get(specialization, SPECIALIZATIONS["baseline"])
    eff_density = spec["density"] if density == 0 else density
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    words = text.split()
    ratio = max(0.1, 1 - eff_density / 130)
    keep  = max(1, round(len(sentences) * ratio))

    scored = []
    for i, s in enumerate(sentences):
        score = len(s.split())
        score += sum(2 for k in CONTRAST_KW if k in s.lower())
        score -= i * 0.05
        scored.append((score, i, s))
    scored.sort(reverse=True)
    selected = sorted(scored[:keep], key=lambda x: x[1])
    core     = " ".join(s for _, _, s in selected)
    structure = [s for _, _, s in scored[:5]]

    depth = (f"Specialization: {specialization}. Density: {eff_density}%. "
             f"{len(words)} words -> {len(core.split())} tokens. "
             f"Domain: {detect_domain(text)}.")

    lower = text.lower()
    if specialization == "security" or any(k in lower for k in SECURITY_KW):
        resonance = "Security is not a feature. It is the foundation."
    elif specialization == "coding" or any(k in lower for k in CODE_KW):
        resonance = "Clean code is compressed thought made executable."
    elif specialization == "emotion" or any(k in lower for k in EMOTION_KW):
        resonance = "The human cost is real. Acknowledge it before optimizing."
    elif any(k in lower for k in CONTRAST_KW):
        resonance = "The tension is the signal. Both sides hold information."
    else:
        resonance = "Signal compressed. Meaning preserved. Noise removed."

    return {
        "core_signal":    core,
        "structure":      structure,
        "depth":          depth,
        "resonance":      resonance,
        "specialization": specialization,
        "symbol":         spec["symbol"],
        "density":        eff_density,
        "word_count":     len(words),
        "timestamp":      datetime.utcnow().isoformat(),
    }


class CondenserBot:
    name        = "condenser_bot"
    description = "Compresses knowledge signals into structured stars. Offline. Jacky-native."

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS stars (
                id TEXT PRIMARY KEY, core_signal TEXT, structure TEXT,
                depth TEXT, resonance TEXT, specialization TEXT,
                symbol TEXT, density INTEGER, word_count INTEGER,
                raw_input TEXT, timestamp TEXT)""")

    def save_star(self, result, raw_input):
        star_id = datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(abs(hash(raw_input)))[:6]
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO stars VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                star_id, result["core_signal"], json.dumps(result["structure"]),
                result["depth"], result["resonance"], result["specialization"],
                result["symbol"], result["density"], result["word_count"],
                raw_input[:2000], result["timestamp"]))
        return star_id

    def list_stars(self, specialization=None, limit=20):
        with sqlite3.connect(DB_PATH) as conn:
            if specialization:
                rows = conn.execute(
                    "SELECT id,core_signal,specialization,symbol,timestamp FROM stars WHERE specialization=? ORDER BY timestamp DESC LIMIT ?",
                    (specialization, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id,core_signal,specialization,symbol,timestamp FROM stars ORDER BY timestamp DESC LIMIT ?",
                    (limit,)).fetchall()
        return [{"id":r[0],"core_signal":r[1],"specialization":r[2],"symbol":r[3],"timestamp":r[4]} for r in rows]

    async def run(self, payload):
        text           = payload.get("text", "")
        density        = payload.get("density", 0)
        specialization = payload.get("specialization", "baseline")
        save           = payload.get("save", True)
        if not text:
            return {"error": "No text provided"}
        result  = compress(text, density, specialization)
        if save:
            result["star_id"] = self.save_star(result, text)
        return result


if __name__ == "__main__":
    bot  = CondenserBot()
    test = "Security is the foundation of all reliable systems. The attack surface must be minimized at every layer. Code without security review is technical debt by default."
    res  = asyncio.run(bot.run({"text": test, "specialization": "security", "density": 85}))
    print(json.dumps(res, indent=2))

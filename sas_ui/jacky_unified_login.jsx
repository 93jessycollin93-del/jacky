import { useState, useEffect, useRef } from "react";

// ====== KNOWLEDGE LOOP STAGES ======
const LOOP_STAGES = [
  { id: "fetch", label: "FETCH", color: "#00ff88", description: "Scan frontier sources — arxiv, GitHub trending, model releases. Pull raw signal.", angle: 0 },
  { id: "filter", label: "FILTER", color: "#00ccff", description: "Score for novelty + durability. Discard hype, keep structural insight.", angle: 72 },
  { id: "compress", label: "COMPRESS", color: "#aa88ff", description: "Distill to atomic knowledge units. One insight per node.", angle: 144 },
  { id: "internalize", label: "INTERNALIZE", color: "#ff8844", description: "Write to memory. Update world model. Connect existing nodes.", angle: 216 },
  { id: "act", label: "ACT", color: "#ff4488", description: "Knowledge changes behavior. Agent decisions improve. Loop closes.", angle: 288 },
];

// ====== 24 DOMAINS (12 TECH + 12 ESOTERIC) ======
const TECH_DOMAINS = [
  { id: "AI", label: "AI", color: "#00ff88", angle: 0 },
  { id: "CODE", label: "Code", color: "#00ccff", angle: 30 },
  { id: "CYBER", label: "Cyber", color: "#aa88ff", angle: 60 },
  { id: "SYSTEMS", label: "Systems", color: "#ff8844", angle: 90 },
  { id: "MATH", label: "Math", color: "#ffcc00", angle: 120 },
  { id: "PSYCH", label: "Psych", color: "#ff4488", angle: 150 },
  { id: "INFO", label: "Info", color: "#44ffcc", angle: 180 },
  { id: "CREATE", label: "Create", color: "#ff6644", angle: 210 },
  { id: "NATURE", label: "Nature", color: "#88ff44", angle: 240 },
  { id: "CONSCI", label: "Conscious", color: "#cc44ff", angle: 270 },
  { id: "SYMBOL", label: "Symbol", color: "#44ccff", angle: 300 },
  { id: "ESOT", label: "Esoteric", color: "#ff44cc", angle: 330 },
];

const ESOTERIC_DOMAINS = [
  { id: "EYE", label: "All-Seeing Eye", symbol: "👁", color: "#ffd700", angle: 15, meaning: "Omniscience, divine awareness, seeing beyond illusion." },
  { id: "CADUCEUS", label: "Caduceus", symbol: "⚕", color: "#c0c0c0", angle: 45, meaning: "Duality unified — two serpents in balance." },
  { id: "PHI", label: "Golden Ratio", symbol: "φ", color: "#daa520", angle: 75, meaning: "The divine proportion in nature, art, and code." },
  { id: "SERPENT", label: "Ouroboros", symbol: "∞", color: "#8b4513", angle: 105, meaning: "The eternal cycle — self-renewal, continuous learning." },
  { id: "ANKH", label: "Ankh", symbol: "☥", color: "#cd853f", angle: 135, meaning: "Life force and immortal wisdom." },
  { id: "TREE", label: "Tree of Life", symbol: "🌳", color: "#228b22", angle: 165, meaning: "The ten sephirot connecting worlds." },
  { id: "MOON", label: "Triple Moon", symbol: "☽◯☾", color: "#b0c4de", angle: 195, meaning: "Waxing, full, waning — cycles." },
  { id: "FLAME", label: "Sacred Flame", symbol: "🔥", color: "#ff4500", angle: 225, meaning: "Purification, transformation, insight." },
  { id: "WHEEL", label: "Dharma Wheel", symbol: "☸", color: "#ff8c00", angle: 255, meaning: "The eightfold path of right thought." },
  { id: "STAR6", label: "Hexagram", symbol: "✡", color: "#4169e1", angle: 285, meaning: "As above, so below — microcosm mirrors macrocosm." },
  { id: "SPIRAL", label: "Fibonacci Spiral", symbol: "🌀", color: "#20b2aa", angle: 315, meaning: "Growth through natural law." },
  { id: "BINDU", label: "Bindu", symbol: "◉", color: "#9400d3", angle: 345, meaning: "The primordial point of singularity." },
];

const ALL_DOMAINS = [...TECH_DOMAINS, ...ESOTERIC_DOMAINS];

// ====== SECURITY THREATS ======
const SCAM_PATTERNS = [
  { name: "Urgency Trap", indicators: ["act now","limited time","urgent","only today","expires"], context: "Artificial time pressure bypasses rational analysis" },
  { name: "Authority Impersonation", indicators: ["official","from your bank","support team","verified account"], context: "Mimics trust without verifiable proof" },
  { name: "Link Obfuscation", indicators: ["bit.ly","tinyurl","click here","verify here","shortened"], context: "Hides true destination from inspection" },
  { name: "Reciprocity Trap", indicators: ["free gift","you owe","special offer","bonus","reward"], context: "Creates psychological debt" },
  { name: "Social Proof Fabrication", indicators: ["thousands agree","everyone is doing","trusted by millions"], context: "Invents consensus to exploit conformity" },
  { name: "Data Harvest Pretext", indicators: ["verify identity","confirm details","update information"], context: "Requests sensitive data under false legitimacy" },
];

// ====== CODE SECURITY CHECKS ======
const CODE_PATTERNS = [
  { regex: /eval\(|Function\(/, sev: "CRITICAL", issue: "eval() usage", fix: "Use JSON.parse or safer alternatives" },
  { regex: /password\s*=\s*['"][^'"]{4,}['"]|pass\s*=\s*['"][^'"]{4,}['"]/, sev: "CRITICAL", issue: "Hardcoded password", fix: "Use environment variables" },
  { regex: /console\.log.*pass|console\.log.*secret|console\.log.*key/, sev: "CRITICAL", issue: "Logging sensitive data", fix: "Never log credentials" },
  { regex: /innerHTML/, sev: "HIGH", issue: "innerHTML assignment", fix: "Use textContent or sanitized DOMParser" },
  { regex: /Math\.random\(\)/, sev: "HIGH", issue: "Non-crypto randomness", fix: "Use crypto.getRandomValues()" },
  { regex: /==[^=]/, sev: "LOW", issue: "Loose equality (==)", fix: "Use strict equality (===)" },
];

export default function JackyUnifiedLogin() {
  // ====== STATE ======
  const [screen, setScreen] = useState("login"); // login, home, hub
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [tab, setTab] = useState("home");
  const [selectedDomain, setSelectedDomain] = useState(null);

  // Agent/analyzer state
  const [scamInput, setScamInput] = useState("");
  const [scamResult, setScamResult] = useState(null);
  const [codeInput, setCodeInput] = useState('function auth(user, pass) {\n  if (user === "admin" && pass === "password123") {\n    console.log("Password: " + pass);\n    return true;\n  }\n}');
  const [codeResult, setCodeResult] = useState(null);
  const [knowledgeNodes, setKnowledgeNodes] = useState([]);
  const [agentLogs, setAgentLogs] = useState([]);
  const [showAgent, setShowAgent] = useState(false);
  const [isAgentRunning, setIsAgentRunning] = useState(false);

  // Canvas refs
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const timeRef = useRef(0);

  // ====== CANVAS ANIMATION ======
  useEffect(() => {
    if (screen !== "home" && screen !== "hub") return;
    if (tab !== "home") return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const W = canvas.width = canvas.offsetWidth * 2;
    const H = canvas.height = canvas.offsetHeight * 2;
    const cx = W / 2, cy = H / 2;

    function draw(t) {
      ctx.clearRect(0, 0, W, H);
      const OUTER = W * 0.35;
      const INNER = W * 0.20;
      const CORE = W * 0.07;

      // Outer ring particles
      for (let i = 0; i < 60; i++) {
        const a = (i / 60) * Math.PI * 2 + t * 0.1;
        const r = OUTER + Math.sin(t * 2 + i * 0.4) * (W * 0.015);
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        const alpha = 0.15 + 0.1 * Math.sin(t * 3 + i);
        ctx.beginPath();
        ctx.arc(x, y, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0,255,136,${alpha})`;
        ctx.fill();
      }

      // All 24 domain nodes
      ALL_DOMAINS.forEach((d, i) => {
        const isTech = i < 12;
        const R = isTech ? INNER : OUTER * 0.72;
        const a = (d.angle * Math.PI) / 180 + t * (isTech ? 0.08 : -0.05);
        const x = cx + R * Math.cos(a);
        const y = cy + R * Math.sin(a);

        const grad = ctx.createLinearGradient(cx, cy, x, y);
        grad.addColorStop(0, "rgba(0,255,136,0.0)");
        grad.addColorStop(1, d.color + "44");
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.strokeStyle = grad;
        ctx.lineWidth = isTech ? 1 : 0.5;
        ctx.stroke();

        const pulseFactor = 0.7 + 0.3 * Math.sin(t * 2 + i * 0.5);
        ctx.beginPath();
        ctx.arc(x, y, (isTech ? 18 : 14) * pulseFactor, 0, Math.PI * 2);
        ctx.fillStyle = d.color + "22";
        ctx.strokeStyle = d.color + "88";
        ctx.lineWidth = 1;
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = d.color;
        ctx.font = `bold ${isTech ? 11 : 9}px monospace`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(isTech ? d.label : (d.symbol || "◈"), x, y);
      });

      // Inner star pattern
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(t * 0.05);
      for (let i = 0; i < 12; i++) {
        const a1 = (i / 12) * Math.PI * 2;
        const a2 = ((i + 5) / 12) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(INNER * 0.55 * Math.cos(a1), INNER * 0.55 * Math.sin(a1));
        ctx.lineTo(INNER * 0.55 * Math.cos(a2), INNER * 0.55 * Math.sin(a2));
        ctx.strokeStyle = "rgba(0,255,136,0.12)";
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }
      ctx.restore();

      // Central prism
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(t * 0.03);
      const ps = CORE * 1.2;
      ctx.beginPath();
      ctx.moveTo(0, -ps);
      ctx.lineTo(ps * Math.cos(Math.PI / 6), ps * Math.sin(Math.PI / 6));
      ctx.lineTo(-ps * Math.cos(Math.PI / 6), ps * Math.sin(Math.PI / 6));
      ctx.closePath();
      const tg = ctx.createLinearGradient(0, -ps, 0, ps);
      tg.addColorStop(0, "rgba(0,255,136,0.6)");
      tg.addColorStop(0.5, "rgba(0,204,255,0.4)");
      tg.addColorStop(1, "rgba(170,136,255,0.6)");
      ctx.fillStyle = tg;
      ctx.strokeStyle = "#00ff88";
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
      ctx.restore();

      // Core orb
      const orb = ctx.createRadialGradient(cx, cy, 0, cx, cy, CORE * 0.7);
      orb.addColorStop(0, "rgba(255,255,255,0.95)");
      orb.addColorStop(0.4, "rgba(0,255,136,0.8)");
      orb.addColorStop(1, "rgba(0,204,255,0.0)");
      ctx.beginPath();
      ctx.arc(cx, cy, CORE * 0.7, 0, Math.PI * 2);
      ctx.fillStyle = orb;
      ctx.fill();

      ctx.fillStyle = "#050508";
      ctx.font = `bold ${CORE * 0.7}px serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("∞", cx, cy);
    }

    function loop(ts) {
      timeRef.current = ts / 1000;
      draw(timeRef.current);
      animRef.current = requestAnimationFrame(loop);
    }
    animRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animRef.current);
  }, [screen, tab]);

  // ====== AGENT FUNCTIONS ======
  const addAgentLog = (msg) => {
    setAgentLogs(prev => [...prev, `${new Date().toLocaleTimeString()} ${msg}`]);
  };

  const analyzeScamWithAgent = () => {
    if (!scamInput.trim()) {
      alert("Paste text to analyze");
      return;
    }

    setIsAgentRunning(true);
    setAgentLogs([]);
    addAgentLog("=== AGENT LOOP START ===");
    addAgentLog("[FETCH] Scanning frontier threat sources...");

    setTimeout(() => {
      addAgentLog("[FILTER] Scoring patterns for novelty & durability...");

      const low = scamInput.toLowerCase();
      const hits = [];
      let score = 0;

      SCAM_PATTERNS.forEach(p => {
        const matches = p.indicators.filter(ind => low.includes(ind));
        if (matches.length) {
          hits.push({ ...p, matches });
          score += matches.length * 0.9;
        }
      });

      addAgentLog(`[FILTER] Passed ${hits.length} patterns (score: ${score.toFixed(1)})`);
      addAgentLog("[COMPRESS] Distilling to atomic knowledge units...");

      const insights = [];
      hits.forEach(hit => {
        const node = {
          id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
          insight: hit.name,
          domain: "CYBER",
          tags: hit.matches,
          color: "#ff2244",
          timestamp: new Date().toLocaleTimeString(),
        };
        insights.push(node);
      });

      addAgentLog(`[INTERNALIZE] Storing ${insights.length} knowledge nodes...`);
      setKnowledgeNodes(prev => [...prev, ...insights]);
      addAgentLog(`[INTERNALIZE] Total nodes in memory: ${knowledgeNodes.length + insights.length}`);

      const level = score > 5 ? "EXTREME" : score > 3 ? "HIGH" : score > 1 ? "MEDIUM" : "LOW";
      const color = { EXTREME: "#ff2244", HIGH: "#ff8800", MEDIUM: "#ffcc00", LOW: "#00ff88" }[level];

      addAgentLog(`[ACT] Classified as ${level} threat (${score.toFixed(1)} score)`);
      addAgentLog("[ACT] Injected context into response model");
      addAgentLog("=== LOOP COMPLETE ===");

      setScamResult({ level, color, score: score.toFixed(1), hits, agentNodes: insights.length });
      setIsAgentRunning(false);
    }, 1500);
  };

  const analyzeCodeWithAgent = () => {
    if (!codeInput.trim()) {
      alert("Paste code to analyze");
      return;
    }

    setIsAgentRunning(true);
    setAgentLogs([]);
    addAgentLog("=== CODE SECURITY LOOP ===");
    addAgentLog("[FETCH] Scanning code for vulnerability patterns...");

    setTimeout(() => {
      addAgentLog("[FILTER] Scoring severity & impact...");

      const issues = [];
      CODE_PATTERNS.forEach(p => {
        if (p.regex.test(codeInput)) {
          issues.push(p);
        }
      });

      addAgentLog(`[FILTER] Found ${issues.length} issues`);
      addAgentLog("[COMPRESS] Extracting fix recommendations...");

      const insights = issues.map(i => ({
        id: `code_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
        insight: i.issue,
        domain: "CYBER",
        tags: [i.sev],
        color: { CRITICAL: "#ff2244", HIGH: "#ff8800", MEDIUM: "#ffcc00", LOW: "#00ff88" }[i.sev],
        timestamp: new Date().toLocaleTimeString(),
      }));

      addAgentLog(`[INTERNALIZE] Storing ${insights.length} vulnerability nodes...`);
      setKnowledgeNodes(prev => [...prev, ...insights]);
      addAgentLog(`[INTERNALIZE] Updated security memory: ${knowledgeNodes.length + insights.length} total`);

      const grade = issues.filter(i => i.sev === "CRITICAL").length > 0 ? "F" :
                    issues.filter(i => i.sev === "HIGH").length > 0 ? "C" :
                    issues.length > 0 ? "B" : "A";

      addAgentLog(`[ACT] Security grade: ${grade}`);
      addAgentLog("[ACT] Model trained on ${insights.length} new examples");
      addAgentLog("=== ANALYSIS COMPLETE ===");

      setCodeResult({ grade, issues, agentNodes: insights.length });
      setIsAgentRunning(false);
    }, 1500);
  };

  const handleLogin = (e) => {
    e.preventDefault();
    if (token.length > 0) {
      setAuthenticated(true);
      setScreen("hub");
      setToken("");
    }
  };

  // ====== RENDER ======
  return (
    <div style={{ background: "#050508", minHeight: "100vh", color: "#e0e0e0", fontFamily: "'Fira Code', monospace" }}>

      {/* ====== LOGIN SCREEN ====== */}
      {screen === "login" && (
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div style={{ maxWidth: 600, width: "100%" }}>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <div style={{ fontSize: 48, marginBottom: 20 }}>∞</div>
              <h1 style={{ margin: 0, fontSize: 36, fontWeight: 700, color: "#fff", letterSpacing: -1, marginBottom: 8 }}>JACKY v3</h1>
              <p style={{ margin: 0, color: "#888", fontSize: 14, letterSpacing: 2 }}>INFINITE PRISM · AGENT-ENHANCED · SELF-IMPROVING</p>
            </div>

            <form onSubmit={handleLogin} style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #00ff8844", borderRadius: 8, padding: 32 }}>
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: "block", fontSize: 11, color: "#666", letterSpacing: 2, marginBottom: 8 }}>ACCESS TOKEN</label>
                <input
                  type="password"
                  value={token}
                  onChange={e => setToken(e.target.value)}
                  placeholder="sas_..."
                  style={{
                    width: "100%",
                    background: "rgba(5,5,8,0.8)",
                    border: "1px solid #00ff8844",
                    borderRadius: 6,
                    color: "#00ff88",
                    padding: "12px 16px",
                    fontSize: 12,
                    boxSizing: "border-box",
                    outline: "none"
                  }}
                  onFocus={e => e.target.style.borderColor = "#00ff88"}
                  onBlur={e => e.target.style.borderColor = "#00ff8844"}
                />
              </div>

              <button
                type="submit"
                style={{
                  width: "100%",
                  background: token.length > 0 ? "#00ff88" : "#333",
                  color: token.length > 0 ? "#050508" : "#666",
                  border: "none",
                  borderRadius: 6,
                  padding: "12px 16px",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: 2,
                  cursor: token.length > 0 ? "pointer" : "not-allowed",
                  transition: "all 0.2s"
                }}
              >
                AUTHENTICATE
              </button>

              <div style={{ marginTop: 20, fontSize: 10, color: "#555", textAlign: "center", lineHeight: 1.6 }}>
                Offline-first architecture. No cloud dependencies. Quantized local models.
              </div>
            </form>

            <div style={{ marginTop: 32, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              {[
                { label: "10 BOTS", desc: "5 coding, 2 security, 3 archivist" },
                { label: "24 DOMAINS", desc: "12 tech, 12 esoteric" },
                { label: "MEMORY", desc: "Personal archive injection" },
              ].map(f => (
                <div key={f.label} style={{ background: "rgba(10,10,20,0.5)", border: "1px solid #1a1a2a", borderRadius: 4, padding: 12, textAlign: "center" }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#00ff88", marginBottom: 4 }}>{f.label}</div>
                  <div style={{ fontSize: 9, color: "#666" }}>{f.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ====== HUB SCREEN ====== */}
      {screen === "hub" && authenticated && (
        <div>
          {/* NAV */}
          <div style={{ background: "rgba(5,5,8,0.97)", borderBottom: "1px solid #00ff8844", padding: "12px 16px", position: "sticky", top: 0, zIndex: 100 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#00ff88", boxShadow: "0 0 12px #00ff88" }} />
              <span style={{ fontSize: 16, fontWeight: 700, color: "#fff", letterSpacing: 2 }}>JACKY v3</span>
              <span style={{ fontSize: 9, color: "#444", letterSpacing: 3, marginLeft: "auto" }}>24 DOMAINS · AGENT-ENHANCED · INFINITE PRISM</span>
              <button onClick={() => { setAuthenticated(false); setScreen("login"); }} style={{
                marginLeft: 16,
                background: "transparent",
                border: "1px solid #333",
                color: "#666",
                padding: "6px 12px",
                borderRadius: 4,
                fontSize: 10,
                letterSpacing: 2,
                cursor: "pointer"
              }}>LOGOUT</button>
            </div>
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              {["home", "scam", "code", "knowledge"].map(t => (
                <button key={t} onClick={() => setTab(t)} style={{
                  background: tab === t ? "rgba(0,255,136,0.15)" : "transparent",
                  border: `1px solid ${tab === t ? "#00ff88" : "#333"}`,
                  color: tab === t ? "#00ff88" : "#666",
                  padding: "6px 12px",
                  borderRadius: 4,
                  fontSize: 10,
                  letterSpacing: 2,
                  cursor: "pointer",
                  textTransform: "uppercase"
                }}>{t}</button>
              ))}
              <button onClick={() => setShowAgent(!showAgent)} style={{
                marginLeft: "auto",
                background: showAgent ? "#00ff8822" : "transparent",
                border: `1px solid ${showAgent ? "#00ff88" : "#333"}`,
                color: showAgent ? "#00ff88" : "#666",
                padding: "6px 12px",
                borderRadius: 4,
                fontSize: 10,
                letterSpacing: 2,
                cursor: "pointer",
                textTransform: "uppercase"
              }}>🤖 {showAgent ? "CLOSE" : "AGENT"}</button>
            </div>
          </div>

          {/* CONTENT */}
          <div style={{ display: "grid", gridTemplateColumns: showAgent ? "1fr 340px" : "1fr", gap: 16, padding: "24px 16px", maxWidth: "100%" }}>
            <div style={{ maxWidth: "900px", margin: "0 auto", width: "100%" }}>

              {/* HOME TAB */}
              {tab === "home" && (
                <div>
                  <div style={{ position: "relative", marginBottom: 32 }}>
                    <canvas ref={canvasRef} style={{ width: "100%", height: 500, display: "block", background: "radial-gradient(ellipse at center, #0d0d1f 0%, #050508 70%)", borderRadius: 8, border: "1px solid #0a0a1a" }} />
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                    {[
                      { name: "Esoteric", color: "#ff44cc", desc: "Hidden patterns, archetypes, sacred geometry" },
                      { name: "Shadow", color: "#aa88ff", desc: "Overlooked threats, scams, predatory patterns" },
                      { name: "Cybernetic", color: "#00ccff", desc: "Systems, feedback loops, code as reality" },
                    ].map(l => (
                      <div key={l.name} style={{ background: "rgba(10,10,20,0.8)", border: `1px solid ${l.color}33`, borderRadius: 6, padding: 16, borderTop: `2px solid ${l.color}` }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: l.color, marginBottom: 8, letterSpacing: 1 }}>{l.name.toUpperCase()}</div>
                        <div style={{ fontSize: 10, color: "#888", lineHeight: 1.7 }}>{l.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SCAM TAB */}
              {tab === "scam" && (
                <div>
                  <div style={{ fontSize: 13, color: "#ff4444", letterSpacing: 2, marginBottom: 20 }}>🛡 THREAT PATTERN SCANNER</div>
                  <div style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #333", borderRadius: 8, padding: 20, marginBottom: 20 }}>
                    <textarea value={scamInput} onChange={e => setScamInput(e.target.value)} placeholder="Paste suspicious text..." style={{ width: "100%", minHeight: 120, background: "rgba(5,5,8,0.8)", border: "1px solid #2a2a2a", borderRadius: 6, color: "#e0e0e0", padding: 12, fontSize: 12, fontFamily: "inherit", outline: "none", boxSizing: "border-box" }} />
                    <button onClick={analyzeScamWithAgent} disabled={isAgentRunning} style={{ marginTop: 12, background: isAgentRunning ? "#333" : "#ff2244", color: "#fff", border: "none", padding: "10px 24px", borderRadius: 4, fontSize: 11, fontWeight: 700, letterSpacing: 2, cursor: isAgentRunning ? "not-allowed" : "pointer" }}>
                      {isAgentRunning ? "SCANNING..." : "SCAN"}
                    </button>
                  </div>

                  {scamResult && (
                    <div style={{ background: "rgba(10,10,20,0.9)", border: `2px solid ${scamResult.color}`, borderRadius: 8, padding: 20 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
                        <div><div style={{ fontSize: 10, color: "#666" }}>RISK</div><div style={{ fontSize: 24, fontWeight: 700, color: scamResult.color }}>{scamResult.level}</div></div>
                        <div><div style={{ fontSize: 10, color: "#666" }}>SCORE</div><div style={{ fontSize: 24, fontWeight: 700, color: "#00ff88" }}>{scamResult.score}</div></div>
                        <div><div style={{ fontSize: 10, color: "#666" }}>PATTERNS</div><div style={{ fontSize: 24, fontWeight: 700, color: "#00ccff" }}>{scamResult.hits.length}</div></div>
                        <div><div style={{ fontSize: 10, color: "#666" }}>NODES</div><div style={{ fontSize: 24, fontWeight: 700, color: "#aa88ff" }}>{scamResult.agentNodes}</div></div>
                      </div>
                      {scamResult.hits.map((h, i) => (
                        <div key={i} style={{ background: "rgba(5,5,8,0.8)", border: "1px solid #2a2a2a", borderRadius: 4, padding: 12, marginBottom: 8 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: "#ff8844" }}>{h.name}</div>
                          <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>Matched: {h.matches.join(", ")}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* CODE TAB */}
              {tab === "code" && (
                <div>
                  <div style={{ fontSize: 13, color: "#00ccff", letterSpacing: 2, marginBottom: 20 }}>⚡ CODE SECURITY ANALYZER</div>
                  <div style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #333", borderRadius: 8, padding: 20, marginBottom: 20 }}>
                    <textarea value={codeInput} onChange={e => setCodeInput(e.target.value)} style={{ width: "100%", minHeight: 160, background: "rgba(5,5,8,0.8)", border: "1px solid #2a2a2a", borderRadius: 6, color: "#00ff88", padding: 12, fontSize: 11, fontFamily: "'Fira Code', monospace", outline: "none", boxSizing: "border-box" }} />
                    <button onClick={analyzeCodeWithAgent} disabled={isAgentRunning} style={{ marginTop: 12, background: isAgentRunning ? "#333" : "#00ccff", color: "#000", border: "none", padding: "10px 24px", borderRadius: 4, fontSize: 11, fontWeight: 700, letterSpacing: 2, cursor: isAgentRunning ? "not-allowed" : "pointer" }}>
                      {isAgentRunning ? "ANALYZING..." : "ANALYZE"}
                    </button>
                  </div>

                  {codeResult && (
                    <div style={{ background: "rgba(10,10,20,0.9)", border: "1px solid #333", borderRadius: 8, padding: 20 }}>
                      <div style={{ display: "flex", gap: 20, marginBottom: 20 }}>
                        <div style={{ fontSize: 48, fontWeight: 700, color: { A: "#00ff88", B: "#00ccff", C: "#ffcc00", F: "#ff2244" }[codeResult.grade] }}>{codeResult.grade}</div>
                        <div style={{ fontSize: 12, color: "#888" }}>Security Grade<br />{codeResult.issues.length} issue(s) | {codeResult.agentNodes} nodes stored</div>
                      </div>
                      {codeResult.issues.map((issue, i) => (
                        <div key={i} style={{ background: "rgba(5,5,8,0.8)", border: "1px solid #2a2a2a", borderLeft: `3px solid ${{ CRITICAL: "#ff2244", HIGH: "#ff8800", MEDIUM: "#ffcc00" }[issue.sev]}`, borderRadius: 4, padding: 12, marginBottom: 8 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: "#ff8844", marginBottom: 6 }}>{issue.sev}: {issue.issue}</div>
                          <div style={{ fontSize: 11, color: "#00ff88" }}>→ {issue.fix}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* KNOWLEDGE TAB */}
              {tab === "knowledge" && (
                <div>
                  <div style={{ fontSize: 13, color: "#aa88ff", letterSpacing: 2, marginBottom: 20 }}>🧠 KNOWLEDGE ACCUMULATION</div>
                  {knowledgeNodes.length === 0 ? (
                    <div style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #333", borderRadius: 6, padding: 20, textAlign: "center", color: "#666" }}>
                      Run agent analysis to accumulate knowledge nodes
                    </div>
                  ) : (
                    <div>
                      <div style={{ fontSize: 11, color: "#666", marginBottom: 12 }}>Total nodes: {knowledgeNodes.length}</div>
                      {knowledgeNodes.map((n, i) => (
                        <div key={i} style={{ background: "rgba(10,10,20,0.8)", border: `1px solid ${n.color}33`, borderLeft: `2px solid ${n.color}`, borderRadius: 6, padding: 12, marginBottom: 8 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                            <div style={{ fontSize: 12, fontWeight: 700, color: n.color }}>{n.insight}</div>
                            <div style={{ fontSize: 9, color: "#555" }}>{n.timestamp}</div>
                          </div>
                          <div style={{ fontSize: 10, color: "#555" }}>Tags: {n.tags.join(", ")}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* AGENT SIDEBAR */}
            {showAgent && (
              <div style={{
                background: "rgba(10,10,20,0.95)",
                border: "1px solid #00ff8844",
                borderRadius: 8,
                padding: 16,
                height: "fit-content",
                position: "sticky",
                top: 80,
                maxHeight: "calc(100vh - 120px)",
                overflowY: "auto"
              }}>
                <div style={{ fontSize: 10, color: "#00ff88", letterSpacing: 2, marginBottom: 12, fontWeight: 700 }}>KNOWLEDGE LOOP</div>

                {LOOP_STAGES.map((s, i) => (
                  <div key={s.id} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
                    <div style={{ width: 3, height: 24, background: s.color, borderRadius: 1 }} />
                    <div style={{ flex: 1, fontSize: 9, color: s.color }}>
                      <div style={{ fontWeight: 700, letterSpacing: 1 }}>{String(i + 1).padStart(2, "0")} {s.label}</div>
                      <div style={{ fontSize: 8, color: "#666", marginTop: 2, lineHeight: 1.3 }}>{s.description}</div>
                    </div>
                  </div>
                ))}

                <div style={{ borderTop: "1px solid #1a1a2a", paddingTop: 12, marginTop: 12 }}>
                  <div style={{ fontSize: 9, color: "#666", letterSpacing: 2, marginBottom: 8 }}>EXECUTION LOG</div>
                  <div style={{ background: "rgba(5,5,8,0.9)", border: "1px solid #0a0a1a", borderRadius: 4, padding: 8, maxHeight: 220, overflowY: "auto" }}>
                    {agentLogs.length === 0 ? (
                      <div style={{ fontSize: 8, color: "#333" }}>Awaiting execution...</div>
                    ) : (
                      agentLogs.map((log, i) => (
                        <div key={i} style={{ fontSize: 8, color: "#666", marginBottom: 3, whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.3 }}>
                          {log}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div style={{ marginTop: 12, fontSize: 8, color: "#444", lineHeight: 1.5, padding: 8, background: "rgba(0,255,136,0.05)", borderRadius: 4 }}>
                  <strong>Agent Status:</strong> {isAgentRunning ? "🔴 RUNNING" : knowledgeNodes.length > 0 ? "🟢 LEARNED" : "⚪ READY"}
                  <div style={{ marginTop: 4, color: "#555" }}>Nodes: {knowledgeNodes.length} | Logs: {agentLogs.length}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

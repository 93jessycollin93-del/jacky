import { useState, useEffect, useRef } from "react";

// ====== LOOP STAGES ======
const LOOP_STAGES = [
  { id: "fetch", label: "FETCH", color: "#00ff88", description: "Scan sources", short: "Collect" },
  { id: "filter", label: "FILTER", color: "#00ccff", description: "Score novelty", short: "Filter" },
  { id: "compress", label: "COMPRESS", color: "#aa88ff", description: "Extract insight", short: "Extract" },
  { id: "internalize", label: "INTERNALIZE", color: "#ff8844", description: "Store & link", short: "Store" },
  { id: "act", label: "ACT", color: "#ff4488", description: "Apply knowledge", short: "Act" },
];

// ====== DOMAINS ======
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
  { id: "EYE", label: "All-Seeing Eye", symbol: "👁", color: "#ffd700", angle: 15 },
  { id: "CADUCEUS", label: "Caduceus", symbol: "⚕", color: "#c0c0c0", angle: 45 },
  { id: "PHI", label: "Golden Ratio", symbol: "φ", color: "#daa520", angle: 75 },
  { id: "SERPENT", label: "Ouroboros", symbol: "∞", color: "#8b4513", angle: 105 },
  { id: "ANKH", label: "Ankh", symbol: "☥", color: "#cd853f", angle: 135 },
  { id: "TREE", label: "Tree of Life", symbol: "🌳", color: "#228b22", angle: 165 },
  { id: "MOON", label: "Triple Moon", symbol: "☽◯☾", color: "#b0c4de", angle: 195 },
  { id: "FLAME", label: "Sacred Flame", symbol: "🔥", color: "#ff4500", angle: 225 },
  { id: "WHEEL", label: "Dharma Wheel", symbol: "☸", color: "#ff8c00", angle: 255 },
  { id: "STAR6", label: "Hexagram", symbol: "✡", color: "#4169e1", angle: 285 },
  { id: "SPIRAL", label: "Fibonacci Spiral", symbol: "🌀", color: "#20b2aa", angle: 315 },
  { id: "BINDU", label: "Bindu", symbol: "◉", color: "#9400d3", angle: 345 },
];

const ALL_DOMAINS = [...TECH_DOMAINS, ...ESOTERIC_DOMAINS];

const COLLECTION_SOURCES = [
  { id: "memory_archive", name: "Memory Archive", icon: "📚", desc: "Personal memory files" },
  { id: "system_state", name: "System State", icon: "⚙", desc: "CPU, memory, disk metrics" },
  { id: "project_files", name: "Project Files", icon: "📁", desc: "Config and project data" },
];

export default function JackyUnifiedEnhanced() {
  // ====== STATE ======
  const [screen, setScreen] = useState("login");
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [tab, setTab] = useState("home");

  // Collector state
  const [collectorRunning, setCollectorRunning] = useState(false);
  const [collectorStatus, setCollectorStatus] = useState(null);
  const [graphNodes, setGraphNodes] = useState([]);
  const [collectionLogs, setCollectionLogs] = useState([]);
  const [activeSources, setActiveSources] = useState(["memory_archive", "system_state", "project_files"]);

  // Agent/analyzer state
  const [scamInput, setScamInput] = useState("");
  const [scamResult, setScamResult] = useState(null);
  const [knowledgeNodes, setKnowledgeNodes] = useState([]);
  const [showAgent, setShowAgent] = useState(false);
  const [isAgentRunning, setIsAgentRunning] = useState(false);

  // Canvas
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const timeRef = useRef(0);

  // ====== COLLECTION POLLING ======
  useEffect(() => {
    if (!authenticated || screen !== "hub") return;

    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch("http://localhost:5000/api/collector/status");
        if (res.ok) {
          const data = await res.json();
          setCollectorStatus(data);
          if (data.recent_logs) {
            setCollectionLogs(data.recent_logs);
          }
        }
      } catch (e) {
        console.log("Collector status unavailable");
      }
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [authenticated, screen]);

  // ====== COLLECTION CONTROLS ======
  const startCollector = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/collector/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ interval: 60 }),
      });
      const data = await res.json();
      if (data.status === "started") {
        setCollectorRunning(true);
      }
    } catch (e) {
      console.error("Failed to start collector:", e);
    }
  };

  const stopCollector = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/collector/stop", {
        method: "POST",
      });
      const data = await res.json();
      if (data.status === "stopped") {
        setCollectorRunning(false);
      }
    } catch (e) {
      console.error("Failed to stop collector:", e);
    }
  };

  const collectNow = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/collector/collect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sources: activeSources }),
      });
      const data = await res.json();
      console.log("Collection result:", data);
    } catch (e) {
      console.error("Collection failed:", e);
    }
  };

  const loadGraph = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/collector/graph");
      if (res.ok) {
        const data = await res.json();
        setGraphNodes(data.nodes || []);
      }
    } catch (e) {
      console.log("Graph load failed");
    }
  };

  // ====== CANVAS ANIMATION ======
  useEffect(() => {
    if (screen !== "hub" || tab !== "home") return;

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

      // Outer particles
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

      // Domains
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

      // Star
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

      // Prism
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

      // Core
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

  // ====== HANDLERS ======
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

      {/* LOGIN */}
      {screen === "login" && (
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div style={{ maxWidth: 600, width: "100%" }}>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <div style={{ fontSize: 48, marginBottom: 20 }}>∞</div>
              <h1 style={{ margin: 0, fontSize: 36, fontWeight: 700, color: "#fff", letterSpacing: -1, marginBottom: 8 }}>JACKY v3</h1>
              <p style={{ margin: 0, color: "#888", fontSize: 14, letterSpacing: 2 }}>INFINITE PRISM · AGENT-ENHANCED · DATA COLLECTOR</p>
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
                }}
              >
                AUTHENTICATE
              </button>
            </form>

            <div style={{ marginTop: 32, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              {[
                { label: "BACKGROUND", desc: "Data collector runs autonomously" },
                { label: "24 DOMAINS", desc: "Knowledge graph construction" },
                { label: "PIPELINE", desc: "FETCH → ACT refinement loop" },
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

      {/* HUB */}
      {screen === "hub" && authenticated && (
        <div>
          {/* NAV */}
          <div style={{ background: "rgba(5,5,8,0.97)", borderBottom: "1px solid #00ff8844", padding: "12px 16px", position: "sticky", top: 0, zIndex: 100 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: collectorRunning ? "#00ff88" : "#333", boxShadow: collectorRunning ? "0 0 12px #00ff88" : "none" }} />
              <span style={{ fontSize: 16, fontWeight: 700, color: "#fff", letterSpacing: 2 }}>JACKY v3</span>
              <span style={{ fontSize: 9, color: "#444", letterSpacing: 3, marginLeft: "auto" }}>
                {collectorRunning ? "🔴 COLLECTING" : "⚪ IDLE"} · {collectorStatus?.graph_size || 0} NODES
              </span>
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
              {["home", "collector", "knowledge"].map(t => (
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
            </div>
          </div>

          {/* CONTENT */}
          <div style={{ padding: "24px 16px", maxWidth: "1200px", margin: "0 auto" }}>

            {/* HOME TAB */}
            {tab === "home" && (
              <div>
                <div style={{ position: "relative", marginBottom: 32 }}>
                  <canvas ref={canvasRef} style={{ width: "100%", height: 500, display: "block", background: "radial-gradient(ellipse at center, #0d0d1f 0%, #050508 70%)", borderRadius: 8, border: "1px solid #0a0a1a" }} />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                  {[
                    { name: "Esoteric", color: "#ff44cc", desc: "Hidden patterns & archetypes" },
                    { name: "Shadow", color: "#aa88ff", desc: "Overlooked threats & insights" },
                    { name: "Cybernetic", color: "#00ccff", desc: "Systems & feedback loops" },
                  ].map(l => (
                    <div key={l.name} style={{ background: "rgba(10,10,20,0.8)", border: `1px solid ${l.color}33`, borderRadius: 6, padding: 16, borderTop: `2px solid ${l.color}` }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: l.color, marginBottom: 8, letterSpacing: 1 }}>{l.name.toUpperCase()}</div>
                      <div style={{ fontSize: 10, color: "#888", lineHeight: 1.7 }}>{l.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* COLLECTOR TAB */}
            {tab === "collector" && (
              <div>
                <div style={{ fontSize: 13, color: "#00ff88", letterSpacing: 2, marginBottom: 20 }}>📊 BACKGROUND DATA COLLECTOR & REFINER</div>

                {/* Controls */}
                <div style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #00ff8844", borderRadius: 8, padding: 20, marginBottom: 20 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
                    <div>
                      <div style={{ fontSize: 10, color: "#666", letterSpacing: 2, marginBottom: 8 }}>COLLECTION STATUS</div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: collectorRunning ? "#00ff88" : "#666" }}>
                        {collectorRunning ? "🔴 RUNNING" : "⚪ STOPPED"}
                      </div>
                      <div style={{ fontSize: 9, color: "#555", marginTop: 4 }}>Graph: {collectorStatus?.graph_size || 0} nodes</div>
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                      {collectorRunning ? (
                        <button onClick={stopCollector} style={{
                          flex: 1,
                          background: "#ff2244",
                          color: "#fff",
                          border: "none",
                          borderRadius: 4,
                          padding: "10px 16px",
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: "pointer"
                        }}>STOP</button>
                      ) : (
                        <button onClick={startCollector} style={{
                          flex: 1,
                          background: "#00ff88",
                          color: "#050508",
                          border: "none",
                          borderRadius: 4,
                          padding: "10px 16px",
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: "pointer"
                        }}>START</button>
                      )}
                      <button onClick={collectNow} style={{
                        flex: 1,
                        background: "#00ccff",
                        color: "#000",
                        border: "none",
                        borderRadius: 4,
                        padding: "10px 16px",
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: "pointer"
                      }}>COLLECT NOW</button>
                      <button onClick={loadGraph} style={{
                        flex: 1,
                        background: "#aa88ff",
                        color: "#fff",
                        border: "none",
                        borderRadius: 4,
                        padding: "10px 16px",
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: "pointer"
                      }}>LOAD GRAPH</button>
                    </div>
                  </div>

                  {/* Sources */}
                  <div>
                    <div style={{ fontSize: 10, color: "#666", letterSpacing: 2, marginBottom: 8 }}>DATA SOURCES</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                      {COLLECTION_SOURCES.map(src => (
                        <button
                          key={src.id}
                          onClick={() => setActiveSources(prev => prev.includes(src.id) ? prev.filter(s => s !== src.id) : [...prev, src.id])}
                          style={{
                            background: activeSources.includes(src.id) ? src.id === "memory_archive" ? "rgba(0,255,136,0.2)" : src.id === "system_state" ? "rgba(0,204,255,0.2)" : "rgba(255,136,68,0.2)" : "rgba(10,10,20,0.5)",
                            border: `1px solid ${activeSources.includes(src.id) ? src.id === "memory_archive" ? "#00ff88" : src.id === "system_state" ? "#00ccff" : "#ff8844" : "#333"}`,
                            borderRadius: 4,
                            padding: "10px 12px",
                            fontSize: 10,
                            color: activeSources.includes(src.id) ? src.id === "memory_archive" ? "#00ff88" : src.id === "system_state" ? "#00ccff" : "#ff8844" : "#666",
                            cursor: "pointer",
                            textAlign: "center"
                          }}
                        >
                          <div style={{ fontWeight: 700, marginBottom: 2 }}>{src.icon} {src.name}</div>
                          <div style={{ fontSize: 8, opacity: 0.7 }}>{src.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Pipeline Status */}
                {collectorStatus && (
                  <div style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #333", borderRadius: 8, padding: 20, marginBottom: 20 }}>
                    <div style={{ fontSize: 10, color: "#666", letterSpacing: 2, marginBottom: 12 }}>PIPELINE STATS</div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
                      {LOOP_STAGES.map(s => (
                        <div key={s.id} style={{ background: "rgba(5,5,8,0.8)", border: `1px solid ${s.color}44`, borderRadius: 4, padding: 10, textAlign: "center" }}>
                          <div style={{ fontSize: 8, color: s.color, fontWeight: 700, marginBottom: 4 }}>{s.label}</div>
                          <div style={{ fontSize: 16, fontWeight: 700, color: s.color }}>
                            {collectorStatus.pipeline_stats[s.id.toLowerCase()] || 0}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Logs */}
                <div style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #333", borderRadius: 8, padding: 20 }}>
                  <div style={{ fontSize: 10, color: "#666", letterSpacing: 2, marginBottom: 12 }}>COLLECTION LOG</div>
                  <div style={{ background: "rgba(5,5,8,0.8)", border: "1px solid #0a0a1a", borderRadius: 4, padding: 12, maxHeight: 300, overflowY: "auto" }}>
                    {collectionLogs.length === 0 ? (
                      <div style={{ fontSize: 10, color: "#333" }}>No collections yet</div>
                    ) : (
                      collectionLogs.map((log, i) => (
                        <div key={i} style={{ fontSize: 9, color: "#666", marginBottom: 4, fontFamily: "'Courier New', monospace" }}>
                          {log}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* KNOWLEDGE TAB */}
            {tab === "knowledge" && (
              <div>
                <div style={{ fontSize: 13, color: "#aa88ff", letterSpacing: 2, marginBottom: 20 }}>🧠 KNOWLEDGE GRAPH</div>
                {graphNodes.length === 0 ? (
                  <div style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #333", borderRadius: 6, padding: 20, textAlign: "center", color: "#666" }}>
                    Click "LOAD GRAPH" in Collector tab to view knowledge nodes
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: 11, color: "#666", marginBottom: 12 }}>Total: {graphNodes.length} nodes</div>
                    {graphNodes.map((n, i) => (
                      <div key={i} style={{ background: "rgba(10,10,20,0.8)", border: "1px solid #1a1a2a", borderLeft: "2px solid #aa88ff", borderRadius: 6, padding: 12, marginBottom: 8 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: "#aa88ff" }}>{n.source}</div>
                          <div style={{ fontSize: 9, color: "#555" }}>{n.status}</div>
                        </div>
                        <div style={{ fontSize: 10, color: "#666", marginBottom: 4 }}>{n.core_insight}</div>
                        <div style={{ fontSize: 9, color: "#555" }}>
                          Novelty: {(n.novelty_score * 100).toFixed(0)}% | Durability: {(n.durability_score * 100).toFixed(0)}%
                        </div>
                        {n.tags.length > 0 && (
                          <div style={{ fontSize: 8, color: "#666", marginTop: 6 }}>
                            Tags: {n.tags.join(", ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

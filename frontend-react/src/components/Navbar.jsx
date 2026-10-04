export default function Navbar({ apiOnline, onScrollHistory, onRunScan, scanning }) {
  return (
    <nav className="navbar">
      <div className="nav-logo">
        <img src="/logo.png" alt="CatchPhish" />
        <span className="nav-wordmark">CATCHPHISH</span>
      </div>

      <div className="nav-links">
        <button className="nav-link"><span className="num">01</span>SCAN</button>
        <button className="nav-link" onClick={onScrollHistory}><span className="num">02</span>HISTORY</button>
      </div>

      <div className="nav-cta">
        <span className="btn-outline" style={{ cursor: "default" }}>
          {apiOnline ? "● BACKEND ONLINE" : "○ BACKEND OFFLINE"}
        </span>
        <button className="btn-gold" onClick={onRunScan} disabled={scanning}>
          <span className="live-dot" />
          {scanning ? "SCANNING…" : "RUN SCAN"}
        </button>
      </div>
    </nav>
  );
}
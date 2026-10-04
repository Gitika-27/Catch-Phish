export default function Hero({ url, setUrl, mode, setMode, onScan, scanning, result }) {
  const hasResult = !!result;
  const tier = result?.final_tier;
  const score = result?.final_risk_score;
  const active = result ? (result.deep || result.fast) : null;
  const signalCount = active?.reasons?.length || 0;
  const scanExamples = ["https://github.com", "https://раypal.com/login", "http://paypal-secure-login.tk/verify"];

  return (
    <section className="hero">
      <div className="hero-eyebrow"><span className="rdot" />{hasResult ? `LIVE ANALYSIS // ${result.domain}` : "REAL-TIME URL INTELLIGENCE // CATCHPHISH"}</div>
      {!hasResult ? <h1 className="hero-headline">PASTE A URL.<br /><span className="accent">WE'LL FIND</span><br />THE RISK.</h1> : (
        <>
          <div className={`explanation-headline ${tier}`}>
            <span className="explanation-kicker">WHY THIS RESULT // SHAP + RULES</span>
            <strong>{result.reason_headline || "The model completed its analysis."}</strong>
          </div>
          <h1 className="hero-headline">THIS URL HAS<br /><span className={tier === "Dangerous" ? "danger" : tier === "Safe" ? "safe" : "accent"}>{score}%</span><br />RISK SCORE.</h1>
        </>
      )}
      {hasResult ? <div className={`verdict-banner ${tier}`}><span className="verdict-pulse" />VERDICT: {tier?.toUpperCase()} <span className="banner-divider">/</span> {signalCount} SIGNALS ANALYZED</div> : <div className="verdict-banner"><span className="verdict-pulse" />SEE THE VERDICT IN UNDER 100ms</div>}
      <p className="hero-desc">{hasResult ? <><b>{result.escalated ? "Tier-2 deep scan" : "Tier-1 / Tier-1.5 fast path"}</b> completed in <b>{result.total_latency_ms}ms</b>. Every decision is exposed as a human-readable signal, not a black-box label.</> : <>CatchPhish combines <b>trusted-domain intelligence</b>, lexical ML, Unicode homograph defense, and SHAP reasoning to make phishing detection fast and explainable.</>}</p>
      <form className="scan-form" onSubmit={(e) => { e.preventDefault(); onScan(); }}>
        <div className="input-shell"><span className="input-prefix">https://</span><input className="scan-input" type="text" placeholder="paste a suspicious URL to investigate" value={url} onChange={(e) => setUrl(e.target.value)} spellCheck={false} autoComplete="off" /></div>
        <button className="btn-gold" type="submit" disabled={scanning}><span className="live-dot" />{scanning ? "SCANNING…" : "RUN SCAN →"}</button>
      </form>
      <div className="mode-row"><button className={`mode-chip ${mode === "fast" ? "active" : ""}`} onClick={() => setMode("fast")} type="button">FAST PATH <small>URL + host</small></button><button className={`mode-chip ${mode === "deep" ? "active" : ""}`} onClick={() => setMode("deep")} type="button">DEEP PATH <small>live page</small></button></div>
      <div className="example-row"><span>TRY A SIGNAL:</span>{scanExamples.map((example) => <button key={example} type="button" onClick={() => setUrl(example)}>{example.replace(/^https?:\/\//, '').slice(0, 27)}</button>)}</div>
      <div className="telemetry-grid"><div><span className="telemetry-value">3</span><span className="telemetry-label">RISK TIERS</span></div><div><span className="telemetry-value">45+</span><span className="telemetry-label">FEATURES</span></div><div><span className="telemetry-value">1.5</span><span className="telemetry-label">HOMOGRAPH GUARD</span></div></div>
    </section>
  );
}

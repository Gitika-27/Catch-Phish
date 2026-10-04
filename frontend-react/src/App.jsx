import { useState, useEffect, useRef, useCallback } from "react";
import Navbar from "./components/Navbar.jsx";
import Hero from "./components/Hero.jsx";
import CodePanel from "./components/CodePanel.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";
import { checkHealth, fetchHistory, scanUrl, clearHistory } from "./api.js";

export default function App() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState("fast");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [apiOnline, setApiOnline] = useState(false);
  const historyRef = useRef(null);

  const refreshHealth = useCallback(async () => {
    try {
      await checkHealth();
      setApiOnline(true);
    } catch {
      setApiOnline(false);
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const data = await fetchHistory();
      setHistory(data);
    } catch {
      /* backend not up yet — ignore */
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    refreshHistory();
    const t = setInterval(refreshHealth, 15000);
    return () => clearInterval(t);
  }, [refreshHealth, refreshHistory]);

  const runScan = useCallback(async () => {
    if (!url.trim() || scanning) return;
    setScanning(true);
    try {
      const data = await scanUrl(url.trim(), mode);
      if (data.error) {
        alert(data.error);
      } else {
        setResult(data);
        refreshHistory();
      }
    } catch {
      alert("Could not reach the CatchPhish API. Check the Render service or your VITE_API_URL setting.");
    } finally {
      setScanning(false);
    }
  }, [url, mode, scanning, refreshHistory]);

  const scrollToHistory = () => {
    historyRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleClearHistory = useCallback(async () => {
    try {
      await clearHistory();
      setHistory([]);
    } catch {
      alert("Could not clear history — check the CatchPhish API connection.");
    }
  }, []);

  return (
    <div className="app">
      <Navbar
        apiOnline={apiOnline}
        onScrollHistory={scrollToHistory}
        onRunScan={runScan}
        scanning={scanning}
      />

      <div className="hero-wrap">
        <Hero
          url={url}
          setUrl={setUrl}
          mode={mode}
          setMode={setMode}
          onScan={runScan}
          scanning={scanning}
          result={result}
        />
        <CodePanel result={result} scanning={scanning} />
      </div>

      <HistoryPanel history={history} innerRef={historyRef} onClear={handleClearHistory} />

      <div className="footer-strip">
        Tier-1: XGBoost, 17 lexical/host features · Tier-2: +content features on live fetch · Tier-0: trusted registry · SHAP-explained
      </div>
    </div>
  );
}
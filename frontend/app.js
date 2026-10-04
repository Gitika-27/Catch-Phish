const API_BASE = ""; // same origin, backend serves this file too

const urlInput = document.getElementById("urlInput");
const scanBtn = document.getElementById("scanBtn");
const modeFast = document.getElementById("modeFast");
const modeDeep = document.getElementById("modeDeep");
const modeHint = document.getElementById("modeHint");
const sweepTrack = document.getElementById("sweepTrack");
const resultEmpty = document.getElementById("resultEmpty");
const resultCard = document.getElementById("resultCard");
const resultUrl = document.getElementById("resultUrl");
const resultDomain = document.getElementById("resultDomain");
const verdictBadge = document.getElementById("verdictBadge");
const scoreBarFill = document.getElementById("scoreBarFill");
const scoreValue = document.getElementById("scoreValue");
const tierTrace = document.getElementById("tierTrace");
const reasonsList = document.getElementById("reasonsList");
const fetchError = document.getElementById("fetchError");
const historyList = document.getElementById("historyList");
const apiStatus = document.getElementById("apiStatus");

let currentMode = "fast";

const TIER_COLOR = { Safe: "var(--safe)", Suspicious: "var(--suspicious)", Dangerous: "var(--dangerous)" };

modeFast.addEventListener("click", () => setMode("fast"));
modeDeep.addEventListener("click", () => setMode("deep"));

function setMode(mode) {
  currentMode = mode;
  modeFast.classList.toggle("active", mode === "fast");
  modeDeep.classList.toggle("active", mode === "deep");
  modeHint.textContent = mode === "fast"
    ? "Fast mode reads only URL structure — no page fetch, sub-second. Switches to Deep automatically if the verdict is uncertain."
    : "Deep mode fetches the live page and inspects 28 additional content features (forms, redirects, scripts, etc). Slower, more thorough.";
}

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      apiStatus.classList.add("online");
      apiStatus.classList.remove("offline");
      apiStatus.innerHTML = `<span class="dot"></span> backend online`;
    } else throw new Error();
  } catch {
    apiStatus.classList.add("offline");
    apiStatus.innerHTML = `<span class="dot"></span> backend unreachable`;
  }
}
checkHealth();
setInterval(checkHealth, 15000);

async function loadHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/history`);
    const data = await res.json();
    renderHistory(data);
  } catch { /* ignore */ }
}
loadHistory();

function renderHistory(items) {
  if (!items.length) {
    historyList.innerHTML = `<div class="history-empty">No scans yet this session.</div>`;
    return;
  }
  historyList.innerHTML = items.map(item => `
    <div class="history-item">
      <div class="history-url">${escapeHtml(item.url)}</div>
      <div class="history-meta">
        <span class="history-badge ${item.tier}">${item.tier.toUpperCase()}</span>
        <span class="history-time">${timeAgo(item.timestamp)}</span>
      </div>
    </div>
  `).join("");
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso + "Z").getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

scanBtn.addEventListener("click", runScan);
urlInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runScan(); });

async function runScan() {
  const url = urlInput.value.trim();
  if (!url) { urlInput.focus(); return; }

  scanBtn.disabled = true;
  scanBtn.textContent = "Scanning…";
  sweepTrack.classList.add("active");
  resultEmpty.style.display = "none";

  try {
    const res = await fetch(`${API_BASE}/api/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, mode: currentMode }),
    });
    const data = await res.json();
    if (data.error) {
      alert(data.error);
    } else {
      renderResult(data);
      loadHistory();
    }
  } catch (e) {
    alert("Could not reach the CatchPhish backend. Is it running on port 8000?");
  } finally {
    scanBtn.disabled = false;
    scanBtn.textContent = "Scan";
    sweepTrack.classList.remove("active");
  }
}

function renderResult(data) {
  resultCard.hidden = false;
  resultUrl.textContent = data.url;
  resultDomain.textContent = data.domain + (data.scheme ? ` · ${data.scheme.toUpperCase()}` : "");

  verdictBadge.textContent = data.final_tier.toUpperCase();
  verdictBadge.className = "verdict-badge " + data.final_tier;

  scoreValue.textContent = data.final_risk_score;
  scoreBarFill.style.width = `${data.final_risk_score}%`;
  scoreBarFill.style.background = TIER_COLOR[data.final_tier] || "var(--accent)";

  // tier trace chips
  let chips = [`<span class="trace-chip">Tier-1 (fast) <b>${data.fast.tier}</b> · ${data.fast.latency_ms}ms</span>`];
  if (data.escalated && data.deep) {
    chips.push(`<span class="trace-chip">→ Tier-2 (deep) <b>${data.deep.tier}</b> · ${data.deep.latency_ms}ms</span>`);
  } else if (data.mode_requested === "deep" && data.fetch_error) {
    chips.push(`<span class="trace-chip">→ Tier-2 fetch failed, showing Tier-1 result</span>`);
  }
  chips.push(`<span class="trace-chip">total <b>${data.total_latency_ms}ms</b></span>`);
  tierTrace.innerHTML = chips.join("");

  // reasons
  const activeResult = data.deep || data.fast;
  reasonsList.innerHTML = activeResult.reasons.map(r => `
    <div class="reason-row">
      <div class="reason-feature">${r.feature}</div>
      <div class="reason-bar-track">
        <div class="reason-bar-fill ${r.direction === 'raises risk' ? 'raises' : 'lowers'}"
             style="width:${Math.min(Math.abs(r.impact) * 40, 50)}%"></div>
      </div>
      <div class="reason-dir ${r.direction === 'raises risk' ? 'raises' : 'lowers'}">${r.direction === 'raises risk' ? '▲ risk' : '▼ risk'}</div>
    </div>
  `).join("");

  if (data.fetch_error) {
    fetchError.hidden = false;
    fetchError.textContent = `Deep scan note: could not fetch live page (${data.fetch_error}). Showing Tier-1 fast result only.`;
  } else {
    fetchError.hidden = true;
  }
}

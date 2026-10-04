const API_BASE = import.meta.env.VITE_API_URL || "https://catchphish-cef6.onrender.com";

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("backend unreachable");
  return res.json();
}

export async function fetchHistory() {
  const res = await fetch(`${API_BASE}/api/history`);
  return res.json();
}

export async function clearHistory() {
  const res = await fetch(`${API_BASE}/api/history`, { method: "DELETE" });
  return res.json();
}

export async function scanUrl(url, mode) {
  const res = await fetch(`${API_BASE}/api/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, mode }),
  });
  return res.json();
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso + "Z").getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function HistoryPanel({ history, innerRef, onClear }) {
  const handleClear = () => {
    if (history.length === 0) return;
    if (window.confirm(`Delete all ${history.length} scan${history.length === 1 ? "" : "s"} from history? This can't be undone.`)) {
      onClear();
    }
  };

  return (
    <div className="history-section" ref={innerRef}>
      <div className="section-title-row">
        <div className="section-title"><span className="num">02 //</span> SCAN HISTORY</div>
        {history.length > 0 && (
          <button className="clear-history-btn" onClick={handleClear} type="button">
            CLEAR HISTORY
          </button>
        )}
      </div>
      {history.length === 0 ? (
        <div className="history-empty">No scans yet this session — run one above.</div>
      ) : (
        <div className="history-grid">
          {history.map((item) => (
            <div className="history-card" key={item.id}>
              <div className="hurl">{item.url}</div>
              <div className="hmeta">
                <span className={`htag ${item.tier}`}>{item.tier.toUpperCase()}</span>
                <span className="htime">{timeAgo(item.timestamp)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
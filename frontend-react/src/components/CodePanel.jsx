function Line({ n, children }) {
  return (
    <div className="code-line">
      <span className="ln">{String(n).padStart(2, "0")}</span>
      <span>{children}</span>
    </div>
  );
}

export default function CodePanel({ result, scanning }) {
  const active = result ? (result.deep || result.fast) : null;
  const contentSummary = result?.deep?.content_summary;
  const reasonCount = active ? active.reasons.length : 0;
  const failedFetch = result && result.fetch_error;

  return (
    <div className="code-panel-wrap">
      <div className="code-toolbar">
        <div className="code-dots"><span /><span /><span /></div>
        <span className="code-filename">
          SCAN_RESULT.LOG — {result ? `${result.domain}.cfg` : "awaiting_input.cfg"}
        </span>
        <span className={`live-badge ${scanning || result ? "" : "idle"}`}>
          <span className="dot" />
          {scanning ? "SCANNING" : result ? "LIVE SCAN" : "IDLE"}
        </span>
      </div>

      <div className="code-body">
        {!result && !scanning && (
          <>
            <Line n={1}><span className="c-comment">// CATCHPHISH_ENGINE.CFG — Tier-1 XGBoost</span></Line>
            <Line n={2}></Line>
            <Line n={3}><span className="c-key">status</span><span className="c-punct">: </span><span className="c-string">"awaiting_scan"</span><span className="c-punct">;</span></Line>
            <Line n={4}></Line>
            <Line n={5}><span className="c-comment">// paste a url on the left and hit RUN SCAN</span></Line>
            <Line n={6}><span className="c-comment">// to populate this panel with live model output</span></Line>
          </>
        )}

        {scanning && (
          <>
            <Line n={1}><span className="c-comment">// CATCHPHISH_ENGINE.CFG</span></Line>
            <Line n={2}></Line>
            <Line n={3}><span className="c-key">status</span><span className="c-punct">: </span><span className="c-string">"extracting_features..."</span><span className="c-punct">;</span></Line>
          </>
        )}

        {result && (
          <>
            <Line n={1}><span className="c-comment">// CATCHPHISH_ENGINE.CFG — {active.model}</span></Line>
            <Line n={2}></Line>
            <Line n={3}><span className="c-key">URL</span><span className="c-punct">: </span><span className="c-string">"{result.url}"</span></Line>
            <Line n={4}></Line>
            <Line n={5}><span className="c-key">ANALYSIS</span> <span className="c-punct">{"{"}</span></Line>
            <Line n={6}>
              &nbsp;&nbsp;<span className="c-key">verdict</span><span className="c-punct">: </span>
              <span className={result.final_tier === "Dangerous" ? "c-bool-true" : "c-bool-false"}>
                "{result.final_tier.toUpperCase()}"
              </span><span className="c-punct">;</span>
            </Line>
            <Line n={7}>
              &nbsp;&nbsp;<span className="c-key">risk_score</span><span className="c-punct">: </span>
              <span className="c-number">{result.final_risk_score}</span><span className="c-punct">;</span>
            </Line>
            <Line n={8}>
              &nbsp;&nbsp;<span className="c-key">confidence</span><span className="c-punct">: </span>
              <span className="c-number">{(active.proba_legit * 100).toFixed(2)}%</span><span className="c-punct">;</span>
            </Line>
            <Line n={9}>
              &nbsp;&nbsp;<span className="c-key">tier0_trusted</span><span className="c-punct">: </span>
              <span className={result.tier0_trusted ? "c-bool-false" : "c-bool-true"}>
                {result.tier0_trusted ? "true" : "false"}
              </span><span className="c-punct">;</span>
            </Line>
            <Line n={10}>
              &nbsp;&nbsp;<span className="c-key">escalated_to_tier2</span><span className="c-punct">: </span>
              <span className={result.escalated ? "c-bool-true" : "c-bool-false"}>
                {result.escalated ? "true" : "false"}
              </span><span className="c-punct">;</span>
            </Line>
            <Line n={11}>
              &nbsp;&nbsp;<span className="c-key">latency_ms</span><span className="c-punct">: </span>
              <span className="c-number">{result.total_latency_ms}</span><span className="c-punct">;</span>
            </Line>
            <Line n={12}></Line>
            <Line n={13}>&nbsp;&nbsp;<span className="c-comment">// top {reasonCount} contributing factors ({result.escalated ? "Tier-2 deep" : "Tier-1 fast"})</span></Line>
            {active.reasons.map((r, i) => (
              <Line n={14 + i} key={r.feature}>
                &nbsp;&nbsp;<span className="c-key">{r.feature}</span><span className="c-punct">: </span>
                <span className={r.direction === "raises risk" ? "c-raise" : "c-lower"}>
                  {r.direction.replace(" ", "_")}
                </span>
                <span className="c-punct"> ({r.impact > 0 ? "+" : ""}{r.impact});</span>
              </Line>
            ))}
            <Line n={14 + reasonCount}><span className="c-punct">{"}"}</span></Line>

            {/* --- Deep-tier only: live page content analysis --- */}
            {contentSummary && (
              <>
                <Line n={15 + reasonCount}></Line>
                <Line n={16 + reasonCount}>
                  <span className="c-key">CONTENT_ANALYSIS</span> <span className="c-punct">{"{"}</span>
                  <span className="c-comment"> // live page fetch, Tier-2 only</span>
                </Line>
                <Line n={17 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">page_title</span><span className="c-punct">: </span>
                  <span className="c-string">"{contentSummary.page_title.slice(0, 48)}"</span><span className="c-punct">;</span>
                </Line>
                <Line n={18 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">domain_title_match</span><span className="c-punct">: </span>
                  <span className="c-number">{contentSummary.domain_title_match}</span><span className="c-punct">;</span>
                </Line>
                <Line n={19 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">has_password_field</span><span className="c-punct">: </span>
                  <span className={contentSummary.has_password_field ? "c-raise" : "c-lower"}>{String(contentSummary.has_password_field)}</span><span className="c-punct">;</span>
                </Line>
                <Line n={20 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">has_hidden_fields</span><span className="c-punct">: </span>
                  <span className={contentSummary.has_hidden_fields ? "c-raise" : "c-lower"}>{String(contentSummary.has_hidden_fields)}</span><span className="c-punct">;</span>
                </Line>
                <Line n={21 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">external_form_submit</span><span className="c-punct">: </span>
                  <span className={contentSummary.has_external_form_submit ? "c-raise" : "c-lower"}>{String(contentSummary.has_external_form_submit)}</span><span className="c-punct">;</span>
                </Line>
                <Line n={22 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">mentions_bank_pay_crypto</span><span className="c-punct">: </span>
                  <span className={contentSummary.mentions_bank_pay_crypto ? "c-raise" : "c-lower"}>{String(contentSummary.mentions_bank_pay_crypto)}</span><span className="c-punct">;</span>
                </Line>
                <Line n={23 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">iframes</span><span className="c-punct">: </span>
                  <span className="c-number">{contentSummary.num_iframes}</span><span className="c-punct">,</span>
                  &nbsp;<span className="c-key">redirects</span><span className="c-punct">: </span>
                  <span className="c-number">{contentSummary.num_redirects}</span><span className="c-punct">;</span>
                </Line>
                <Line n={24 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">links</span><span className="c-punct">: </span>
                  <span className="c-punct">{"{ "}</span>self: <span className="c-number">{contentSummary.num_self_links}</span>,
                  &nbsp;external: <span className="c-number">{contentSummary.num_external_links}</span><span className="c-punct">{" }"}</span><span className="c-punct">;</span>
                </Line>
                <Line n={25 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">images</span><span className="c-punct">: </span>
                  <span className="c-number">{contentSummary.num_images}</span><span className="c-punct">,</span>
                  &nbsp;<span className="c-key">scripts</span><span className="c-punct">: </span>
                  <span className="c-number">{contentSummary.num_scripts}</span><span className="c-punct">;</span>
                </Line>
                <Line n={26 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">has_favicon</span><span className="c-punct">: </span>
                  <span className={contentSummary.has_favicon ? "c-lower" : "c-raise"}>{String(contentSummary.has_favicon)}</span><span className="c-punct">,</span>
                  &nbsp;<span className="c-key">responsive</span><span className="c-punct">: </span>
                  <span className={contentSummary.is_responsive ? "c-lower" : "c-raise"}>{String(contentSummary.is_responsive)}</span><span className="c-punct">;</span>
                </Line>
                <Line n={27 + reasonCount}>
                  &nbsp;&nbsp;<span className="c-key">has_copyright_notice</span><span className="c-punct">: </span>
                  <span className={contentSummary.has_copyright_notice ? "c-lower" : "c-raise"}>{String(contentSummary.has_copyright_notice)}</span><span className="c-punct">,</span>
                  &nbsp;<span className="c-key">robots_txt</span><span className="c-punct">: </span>
                  <span className={contentSummary.robots_txt_present ? "c-lower" : "c-raise"}>{String(contentSummary.robots_txt_present)}</span><span className="c-punct">;</span>
                </Line>
                <Line n={28 + reasonCount}><span className="c-punct">{"}"}</span></Line>
              </>
            )}

            <Line n={30 + reasonCount}></Line>
            {failedFetch ? (
              <>
                <Line n={31 + reasonCount}><span className="c-comment">// STATUS: Tier-2 deep fetch skipped</span></Line>
                <Line n={32 + reasonCount}><span className="c-raise">// reason: {result.fetch_error}</span></Line>
                <Line n={33 + reasonCount}><span className="c-comment">// showing Tier-1 fast result only. try a real, live URL to see Tier-2 in action.</span></Line>
              </>
            ) : (
              <Line n={31 + reasonCount}><span className="c-comment">// STATUS: ok</span></Line>
            )}
          </>
        )}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Header } from "./components/Header.jsx";
import { MlPaperDashboard } from "./components/MlPaperDashboard.jsx";

function fetchFounderStatus() {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  const url = base ? `${base}/founder/status` : "/founder/status";
  return fetch(`${url}?t=${Date.now()}`).then((res) => {
    if (!res.ok) throw new Error(`status ${res.status}`);
    return res.json();
  });
}

function leanPlain(k, v) {
  const s = String(v || "HOLD");
  if (s.includes("BUY_CE") || s === "CE") return `${k} leaning CALL`;
  if (s.includes("BUY_PE") || s === "PE") return `${k} leaning PUT`;
  return `${k} HOLD`;
}

export function FounderPm() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function pull() {
      try {
        const json = await fetchFounderStatus();
        if (!cancelled) {
          setData(json);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || String(err));
      }
    }
    pull();
    const id = setInterval(pull, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const issues = data?.issues || [];
  const agents = data?.agents || [];
  const paper = agents.find((a) => a.id === "paper-loop");
  const api = (data?.services || []).find((s) => s.id === "api");
  const vite = (data?.services || []).find((s) => s.id === "vite");

  return (
    <div className="desk cleanup-desk">
      <Header
        title="Founder desk"
        kicker="D4 · /pm"
        sub="Unique paper P/L · TARGET vs TIME vs STOP · no live orders"
        sourceLabel={data?.mode || "PAPER"}
      />
      <p className="desk-sub">
        <a href="/">Customer /</a>
        {" · "}
        <a href="/desk">Research /desk</a>
        {data?.as_of ? ` · ${data.as_of}` : " · Loading…"}
      </p>

      {error && (
        <p className="desk-error">
          Cannot reach founder status ({error}). Start API on :8000. Tokens are never shown.
        </p>
      )}

      {data && (
        <>
          <div className="fx-health" aria-label="Process health">
            <span className={`cleanup-pill ${paper?.alive ? "done" : "pending"}`}>
              paper {paper?.alive ? "ON" : "OFF"}
            </span>
            <span className={`cleanup-pill ${api?.tone === "green" ? "done" : "pending"}`}>API</span>
            <span className={`cleanup-pill ${vite?.tone === "green" ? "done" : "pending"}`}>site</span>
            <span className="cleanup-pill pending">NO_PROMOTE</span>
            <span className="cleanup-pill pending">orders refused</span>
          </div>

          {issues.length > 0 ? (
            <article className="cleanup-card founder-red">
              <div className="cleanup-status">Fix first</div>
              <strong>{data.next_action}</strong>
              <ul className="cleanup-keep">
                {issues.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </article>
          ) : (
            <article className="cleanup-card founder-green">
              <div className="cleanup-status">Watch</div>
              <strong>Paper loop is the product today. Do not promote. Do not send Super Orders.</strong>
              <p>Read unique net and TARGET hits below — clone wr is not founder skill.</p>
            </article>
          )}

          <h2 className="cleanup-h">Session money</h2>
          <MlPaperDashboard compact />

          <h2 className="cleanup-h">Index lean (not a fill)</h2>
          <div className="cleanup-grid">
            {Object.entries(data.leans || {}).map(([k, v]) => {
              const chain = (data.chain_metrics || {})[k] || {};
              return (
                <article key={k} className="cleanup-card">
                  <div className="cleanup-status">{leanPlain(k, v)}</div>
                  <strong>{k}</strong>
                  <p>
                    spot {chain.spot ?? "—"} · PCR {chain.pcr_oi ?? "—"}
                  </p>
                </article>
              );
            })}
          </div>

          <details className="desk-context">
            <summary>Agents and services</summary>
            <div className="cleanup-grid">
              {agents.map((a) => (
                <article key={a.id} className={`cleanup-card founder-${a.tone || "grey"}`}>
                  <div className="cleanup-status">{a.alive ? "RUNNING" : "DOWN"}</div>
                  <strong>{a.name}</strong>
                  <p>{a.detail}</p>
                </article>
              ))}
              {(data.services || []).map((s) => (
                <article key={s.id} className={`cleanup-card founder-${s.tone || "grey"}`}>
                  <div className="cleanup-status">{s.tone}</div>
                  <strong>{s.name}</strong>
                  <p>{s.detail}</p>
                </article>
              ))}
            </div>
          </details>
          <p className="desk-sub">{(data.honesty || []).join(" ")}</p>
        </>
      )}
    </div>
  );
}

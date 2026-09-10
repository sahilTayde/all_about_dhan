import { useEffect, useState } from "react";
import { Header } from "./components/Header.jsx";

function fetchFounderStatus() {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  const url = base ? `${base}/founder/status` : "/founder/status";
  return fetch(`${url}?t=${Date.now()}`).then((res) => {
    if (!res.ok) throw new Error(`status ${res.status}`);
    return res.json();
  });
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

  return (
    <div className="desk cleanup-desk">
      <Header
        title="Founder PM"
        kicker="D4 · /pm"
        sub="Who is running · what they do · red = broken. Not the customer desk. No orders."
        sourceLabel={data?.mode || "PAPER"}
      />
      <p className="desk-sub">
        <a href="/">Customer /</a>
        {" · "}
        <a href="/desk">Research /desk</a>
        {data?.as_of ? ` · Updated ${data.as_of}` : " · Loading…"}
      </p>
      {error && (
        <p className="desk-error">
          Cannot reach founder status ({error}). Start API on :8000. Tokens are never shown.
        </p>
      )}
      {data && (
        <>
          <article className={`cleanup-card ${issues.length ? "founder-red" : "founder-green"}`}>
            <div className="cleanup-status">{issues.length ? "Attention" : "Next"}</div>
            <strong>{data.next_action}</strong>
            <p>
              Gate {data.gate}. Promote={String(data.promote)}. Orders {data.orders}.
              {data.stopped ? " STOP flag is on." : ""}
            </p>
          </article>
          {issues.length > 0 && (
            <>
              <h2 className="cleanup-h">Issues</h2>
              <ul className="cleanup-keep">
                {issues.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </>
          )}
          <h2 className="cleanup-h">Agents</h2>
          <div className="cleanup-grid">
            {(data.agents || []).map((a) => (
              <article key={a.id} className={`cleanup-card founder-${a.tone || "grey"}`}>
                <div className="cleanup-status">
                  {a.alive ? "RUNNING" : "DOWN"}
                  {a.pid ? ` · pid ${a.pid}` : ""}
                </div>
                <strong>
                  {a.name}
                </strong>
                <p>{a.task}</p>
                <p className="desk-sub">{a.detail}</p>
              </article>
            ))}
          </div>
          <h2 className="cleanup-h">Services</h2>
          <div className="cleanup-grid">
            {(data.services || []).map((s) => (
              <article key={s.id} className={`cleanup-card founder-${s.tone || "grey"}`}>
                <div className="cleanup-status">{s.tone}</div>
                <strong>{s.name}</strong>
                <p>{s.detail}</p>
              </article>
            ))}
          </div>
          <h2 className="cleanup-h">Paper leans (not fills)</h2>
          <div className="cleanup-grid">
            {Object.entries(data.leans || {}).map(([k, v]) => {
              const chain = (data.chain_metrics || {})[k] || {};
              return (
                <article key={k} className="cleanup-card">
                  <div className="cleanup-status">{k}</div>
                  <strong>{String(v)}</strong>
                  <p>
                    spot {chain.spot ?? "—"} · PCR {chain.pcr_oi ?? "—"} · ATM{" "}
                    {chain.option_ltp ?? "—"} · {chain.source || "no chain"}
                  </p>
                  <p className="desk-sub">
                    INDEX 1m source: {(data.index_bar_source || {})[k] || "—"}
                  </p>
                </article>
              );
            })}
          </div>
          <p className="desk-sub">
            Signals {data.signals ?? "—"} · shadow {data.shadow ?? "—"} · LLM {data.llm_status || "—"}
            {data.started_at_ist ? ` · started ${data.started_at_ist}` : ""}
          </p>
          <p className="desk-sub">{(data.honesty || []).join(" ")}</p>
        </>
      )}
    </div>
  );
}

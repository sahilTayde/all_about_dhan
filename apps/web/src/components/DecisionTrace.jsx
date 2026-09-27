import { useEffect, useRef, useState } from "react";
import { fetchTrace } from "../lib/feed.js";

function Value({ v }) {
  if (Array.isArray(v)) {
    return (
      <ul>
        {v.map((x, i) => (
          <li key={i}>{String(x)}</li>
        ))}
      </ul>
    );
  }
  if (v && typeof v === "object") return <code>{JSON.stringify(v)}</code>;
  return String(v);
}

/** Decision trace (§49): Data → Analysts → Boss → Risk → Desk → Broker → Fill, from recorded logs only. */
export function DecisionTrace({ tradeId, label, refreshKey }) {
  const [trace, setTrace] = useState(null);
  const [err, setErr] = useState(null);
  const [pick, setPick] = useState(null);
  const shownId = useRef(null);

  // refreshKey changes whenever an open ticket updates, so its trace follows the trade.
  useEffect(() => {
    if (!tradeId) return undefined;
    const ac = new AbortController();
    const switched = shownId.current !== tradeId;
    if (switched) {
      setErr(null);
      setTrace(null);
    }
    fetchTrace(tradeId, { signal: ac.signal })
      .then((t) => {
        shownId.current = tradeId;
        setTrace(t);
        if (switched) setPick((t.steps || []).find((s) => s.status !== "NO_DATA")?.id || null);
      })
      .catch((e) => e?.name !== "AbortError" && setErr("Trace needs the API (read-only /paper/trace)."));
    return () => ac.abort();
  }, [tradeId, refreshKey]);

  const steps = trace?.steps || [];
  const sel = steps.find((s) => s.id === pick);
  return (
    <section className="panel trace-panel">
      <div className="panel__head">
        <h2>Decision trace</h2>
        <span className="muted small">{tradeId ? label || tradeId : "click a trade row"}</span>
      </div>
      {!tradeId ? (
        <p className="muted">Pick a trade in the table to see who decided what, step by step.</p>
      ) : err ? (
        <p className="muted">{err}</p>
      ) : !trace ? (
        <p className="muted">Loading trace…</p>
      ) : !trace.ok ? (
        <p className="muted">{trace.reason}</p>
      ) : (
        <>
          <ol className="trace-flow">
            {steps.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className={`trace-node trace-node--${s.status.toLowerCase()}${pick === s.id ? " is-on" : ""}`}
                  onClick={() => setPick(s.id)}
                  aria-pressed={pick === s.id}
                >
                  <span className="trace-node__title">{s.title}</span>
                  <span className="trace-node__decided">{s.status === "NO_DATA" ? "no record" : s.decided || s.status}</span>
                </button>
              </li>
            ))}
          </ol>
          {sel ? (
            <div className={`trace-detail trace-detail--${sel.status.toLowerCase()}`}>
              <p>
                <strong>{sel.title}</strong> · {sel.status === "NO_DATA" ? "no recorded data for this step" : sel.decided}
                {sel.source ? <span className="muted"> · source: {sel.source}</span> : null}
              </p>
              {sel.why ? <p className="trace-detail__why">Why: {sel.why}</p> : null}
              {Object.keys(sel.fields || {}).length ? (
                <dl className="trace-detail__fields">
                  {Object.entries(sel.fields).map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>
                        <Value v={v} />
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

import { useEffect, useState } from "react";
import { Header } from "./components/Header.jsx";

function tone(status) {
  const s = String(status || "pending").toLowerCase();
  if (s === "done" || s === "completed" || s === "finished") return "done";
  if (s === "in_progress" || s === "progress") return "in_progress";
  return "pending";
}

function label(status) {
  const t = tone(status);
  if (t === "done") return "Completed";
  if (t === "in_progress") return "In progress";
  return "Pending";
}

export function CleanupCanvas() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function pull() {
      try {
        const res = await fetch(`/cleanup-status.json?t=${Date.now()}`);
        if (!res.ok) throw new Error(`status ${res.status}`);
        const json = await res.json();
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

  return (
    <div className="desk cleanup-desk">
      <Header
        title="Cleanup canvas"
        kicker="founder monitor"
        sub="DhanHQ keep · non-Dhan wipe · not a P/L board"
        sourceLabel={data?.phase || "cleanup"}
      />
      {error && <p className="desk-error">Status JSON: {error}</p>}
      <p className="desk-sub">{data?.updated_ist ? `Updated ${data.updated_ist}` : "Loading…"}</p>
      <div className="cleanup-legend">
        <span className="cleanup-pill done">Completed</span>
        <span className="cleanup-pill in_progress">In progress</span>
        <span className="cleanup-pill pending">Pending</span>
      </div>
      <h2 className="cleanup-h">Agents</h2>
      <div className="cleanup-grid">
        {(data?.agents || []).map((a) => (
          <article key={a.id} className={`cleanup-card ${tone(a.status)}`}>
            <div className="cleanup-status">{label(a.status)}</div>
            <strong>
              {a.id} · {a.name}
            </strong>
            <p>{a.task}</p>
          </article>
        ))}
      </div>
      <h2 className="cleanup-h">Phases</h2>
      <div className="cleanup-grid">
        {(data?.phases || []).map((p) => (
          <article key={p.id} className={`cleanup-card ${tone(p.status)}`}>
            <div className="cleanup-status">{label(p.status)}</div>
            <strong>
              {p.id} · {p.name}
            </strong>
            <p>{p.detail}</p>
            <p className="desk-sub">
              Removed: {p.removed || "—"}
              <br />
              Kept: {p.kept || "—"}
            </p>
          </article>
        ))}
      </div>
      <h2 className="cleanup-h">Keep</h2>
      <ul className="cleanup-keep">
        {(data?.keep || []).map((k) => (
          <li key={k}>{k}</li>
        ))}
      </ul>
      <p className="desk-sub">
        Static twin: <a href="/cleanup-canvas.html">/cleanup-canvas.html</a>
      </p>
    </div>
  );
}

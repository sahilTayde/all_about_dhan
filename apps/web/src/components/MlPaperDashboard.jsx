import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

async function fetchMlPaperBoard() {
  const url = API_URL
    ? `${API_URL}/paper/ml-books`
    : "/mock/ml_paper_dashboard.json";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`ml paper board HTTP ${res.status}`);
  return res.json();
}

export function MlPaperDashboard({ compact = false }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchMlPaperBoard()
      .then((j) => {
        if (!cancelled) setData(j);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <section className="panel" aria-labelledby="ml-paper-title">
        <h2 id="ml-paper-title">ML paper scalpers</h2>
        <p className="muted">
          Board missing ({error}). Run{" "}
          <code>python -m desk_ml paper-scalp --replay</code>. No npm restart.
        </p>
      </section>
    );
  }
  if (!data) {
    return (
      <section className="panel">
        <h2>ML paper scalpers</h2>
        <p className="muted">Loading…</p>
      </section>
    );
  }

  const models = data.models || [];
  const board = data.leaderboard || [];
  const gaps = (data.inventory && data.inventory.data_gaps) || data.data_gaps || [];
  const closed = data.closed_trades || [];
  const open = data.open_trades || [];

  return (
    <section className="panel" aria-labelledby="ml-paper-title">
      <h2 id="ml-paper-title">ML / paper scalper board</h2>
      <p className="muted">
        Gate {data.gate || "not RESEARCH_READY_FOR_PROGRAMMING"}. Promote=
        {String(data.promote)}. win_rate=null. Independent books. Closed premium
        P/L only. Updated {data.as_of_ist || "—"}.
      </p>
      <h3>Models</h3>
      <div className="cleanup-grid">
        {models.map((m) => (
          <article key={m.model_id} className="cleanup-card">
            <div className="cleanup-status">{m.model_id}</div>
            <strong>
              closed {m.n_closed} · open {m.n_open}
            </strong>
            <p>{m.what}</p>
            <p className="desk-sub">last {m.last_run_ist || "—"}</p>
          </article>
        ))}
      </div>
      <h3>Closed-premium leaderboard</h3>
      {board.length === 0 ? (
        <p className="muted">No CLOSED paper rows yet.</p>
      ) : (
        <ul className="cleanup-keep">
          {board.map((r) => (
            <li key={`${r.book_id}-${r.underlying}`}>
              {r.book_id} {r.underlying}: n={r.n_closed} sum={r.sum_premium_pnl}{" "}
              (win_rate null)
            </li>
          ))}
        </ul>
      )}
      {!compact && (
        <>
          <h3>Open vs closed</h3>
          <p className="muted">
            Open {open.length} · Closed {closed.length}. Exits: stop / target /{" "}
            {data.scalper_exits?.time || "8m"} / 15:00 IST flatten.
          </p>
          <h3>DATA_INSUFFICIENT</h3>
          {gaps.length === 0 ? (
            <p className="muted">None on this snapshot.</p>
          ) : (
            <ul className="cleanup-keep">
              {gaps.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

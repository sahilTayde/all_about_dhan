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
    const load = () => {
      fetchMlPaperBoard()
        .then((j) => {
          if (!cancelled) {
            setData(j);
            setError(null);
          }
        })
        .catch((e) => {
          if (!cancelled) setError(e.message || String(e));
        });
    };
    load();
    const id = setInterval(load, 20000);
    return () => {
      cancelled = true;
      clearInterval(id);
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
  const ranks = data.book_rank || [];
  const today = data.today || {};
  const indexNotes = data.index_notes || [];
  const gaps = (data.inventory && data.inventory.data_gaps) || data.data_gaps || [];
  const closed = data.closed_trades || [];
  const open = data.open_trades || [];
  const netByIndex = today.net_by_index || {};
  const bestMl = today.best_ml_book || {};

  return (
    <section className="panel" aria-labelledby="ml-paper-title">
      <h2 id="ml-paper-title">{data.title || "ML / paper scalper board"}</h2>
      <p className="muted">
        Gate {data.gate || "not RESEARCH_READY_FOR_PROGRAMMING"}. Promote=
        {String(data.promote)}. Session {data.session_ist_date || "—"}. paper win_rate=
        {data.win_rate_pct ?? "—"}% ({data.n_wins ?? "—"} win / {data.n_losses ?? "—"} loss /{" "}
        {data.n_closed ?? "—"} filled). Gross ₹{data.overall_gross_pnl_inr ?? today.gross_pnl_inr ?? "—"} −
        charges ₹{data.overall_charges_inr ?? today.charges_inr ?? "—"} (Groww+GST+STT VERIFY) ={" "}
        <strong>net ₹{data.overall_pnl_inr ?? today.net_pnl_inr ?? "—"}</strong> (won ₹
        {data.money_won_inr ?? "—"} / lost ₹{data.money_lost_inr ?? "—"}). ₹
        {data.starting_capital_inr_per_book ?? 10000} / book. Open {open.length}. Updated{" "}
        {data.as_of_ist || "—"}.
      </p>
      <p className="desk-sub">
        Filled {today.n_filled ?? "—"} · cancelled {today.n_cancelled ?? "—"} · brokerage ₹
        {today.brokerage_inr ?? "—"} · GST ₹{today.gst_inr ?? "—"} · STT ₹{today.stt_inr ?? "—"}.
        {Object.keys(netByIndex).length > 0
          ? " Index net (8 books): " +
            Object.entries(netByIndex)
              .map(([k, v]) => `${k} ₹${v}`)
              .join(" · ") +
            "."
          : ""}
        {today.unique_net_pnl_inr != null
          ? ` Unique books net ₹${today.unique_net_pnl_inr}.`
          : ""}
        {bestMl.book_id
          ? ` Best ML: ${bestMl.book_id} rank ${bestMl.rank} net ₹${bestMl.sum_pnl_inr}.`
          : ""}
        {` SIDEWAYS HOLD skips ${data.n_skip_sideways ?? today.n_skip_sideways ?? 0} new opens (${data.n_sideways_bars ?? today.n_sideways_bars ?? 0} bars). SL-hits ${data.n_sl_hit ?? today.n_sl_hit ?? "—"}.`}
      </p>
      <h3>Ranked by net P/L</h3>
      {ranks.length === 0 ? (
        <p className="muted">No ranked books yet.</p>
      ) : (
        <ul className="cleanup-keep">
          {ranks.map((r) => (
            <li key={r.book_id}>
              #{r.rank} {r.book_id} ({r.kind}): {r.n_wins}W/{r.n_losses}L filled=
              {r.n_filled} cancel={r.n_cancelled} wr={r.win_rate_pct ?? "—"}% gross₹=
              {r.sum_gross_pnl_inr ?? "—"} charges₹={r.sum_charges_inr ?? "—"}{" "}
              <strong>net₹={r.sum_pnl_inr}</strong>
            </li>
          ))}
        </ul>
      )}
      <h3>Models</h3>
      <div className="cleanup-grid">
        {models.map((m) => (
          <article key={m.model_id} className="cleanup-card">
            <div className="cleanup-status">{m.model_id}</div>
            <strong>
              {m.n_wins ?? 0}W / {m.n_losses ?? 0}L · wr {m.win_rate_pct ?? "—"}% · ₹
              {m.equity_inr ?? "—"}
            </strong>
            <p>{m.what}</p>
            <p className="desk-sub">last {m.last_run_ist || "—"}</p>
          </article>
        ))}
      </div>
      <h3>Book × index (ranked by net ₹)</h3>
      {board.length === 0 ? (
        <p className="muted">No CLOSED paper rows yet.</p>
      ) : (
        <ul className="cleanup-keep">
          {board.map((r) => (
            <li key={`${r.book_id}-${r.underlying}`}>
              #{r.rank} {r.book_id} {r.underlying}: {r.n_wins}W/{r.n_losses}L n={r.n_closed} wr=
              {r.win_rate_pct ?? "—"}% pts={r.sum_premium_pnl} gross₹={r.sum_gross_pnl_inr ?? "—"}{" "}
              charges₹={r.sum_charges_inr ?? "—"} <strong>net₹={r.sum_pnl_inr ?? "—"}</strong>
            </li>
          ))}
        </ul>
      )}
      {!compact && (
        <>
          <h3>Index / ML notes</h3>
          {indexNotes.length === 0 ? (
            <p className="muted">Replay the live session to fill notes.</p>
          ) : (
            <ul className="cleanup-keep">
              {indexNotes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
          <h3>Open vs closed</h3>
          <p className="muted">
            Open {open.length} · Closed {closed.length}. Exits: stop / target /{" "}
            {data.scalper_exits?.time || "8m"} / 15:00 IST flatten. Closed newest first.
          </p>
          <h3>Closed tickets (newest first)</h3>
          {closed.length === 0 ? (
            <p className="muted">No closed tickets yet.</p>
          ) : (
            <ul className="cleanup-keep">
              {(data.closed_trades_sample || closed).slice(0, 20).map((t) => (
                <li key={t.trade_id}>
                  {t.book_id} {t.underlying} {t.side} strike={t.atm_strike} limit=
                  {t.limit_price} tgt={t.target} sl={t.stop} status={t.status} sl_hit=
                  {String(t.sl_hit)} lost₹={t.sl_loss_inr ?? (t.result === "LOSS" ? t.realized_pnl_inr : "—")}{" "}
                  pnl₹={t.realized_pnl_inr ?? "—"} {t.result} regime={t.index_regime || "—"}
                </li>
              ))}
            </ul>
          )}
          <h3>Open tickets (strike / limit / SL / CE|PE / status)</h3>
          {open.length === 0 ? (
            <p className="muted">No OPEN paper rows this session.</p>
          ) : (
            <ul className="cleanup-keep">
              {open.map((t) => (
                <li key={t.trade_id}>
                  {t.book_id} {t.underlying} {t.side} strike={t.atm_strike} limit=
                  {t.limit_price} tgt={t.target} sl={t.stop} status={t.status || "OPEN_PAPER"}{" "}
                  regime={t.index_regime || "—"}
                </li>
              ))}
            </ul>
          )}
          <h3>Mistakes (paper params only)</h3>
          {(data.paper_param_notes || []).map((n) => (
            <p key={n} className="muted">
              {n}
            </p>
          ))}
          {(data.mistakes || []).length === 0 ? (
            <p className="muted">No LOSS rows this snapshot.</p>
          ) : (
            <ul className="cleanup-keep">
              {(data.mistakes || []).slice(-12).map((t) => (
                <li key={t.trade_id}>
                  {t.book_id} {t.underlying} {t.side} strike={t.atm_strike} lost₹=
                  {t.money_lost_inr} {t.lesson}
                </li>
              ))}
            </ul>
          )}
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

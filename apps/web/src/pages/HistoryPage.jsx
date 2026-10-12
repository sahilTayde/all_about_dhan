import { PnlChart } from "../components/PnlChart.jsx";
import { inr, tone, tradeCsv } from "../lib/deskModel.js";
import { TradeLine } from "./parts.jsx";

export function HistoryPage({ snap, dd }) {
  const days = snap?.days || [];
  const indexing = snap?.history_complete === false;
  let run = 0;
  const curve = [...days].sort((a, b) => a.day.localeCompare(b.day)).map((d) => ({ ...d, run: (run += d.net || 0) }));
  const max = Math.max(1, ...curve.map((d) => Math.abs(d.run)));
  return (
    <div className="history" data-testid="history-page">
      <section className="card">
        <header className="card__head"><h2>Account over time (after charges)</h2>
          <button type="button" className="chip-btn" onClick={() => tradeCsv(dd.closed)} data-testid="csv">Download today's trades (CSV)</button>
        </header>
        {indexing ? <p className="muted">Still reading the trade log…</p> : null}
        {curve.length ? (
          <svg className="equity" viewBox={`0 0 ${curve.length * 40} 120`} preserveAspectRatio="none" role="img" aria-label="Running account P&L by day">
            <line x1="0" x2={curve.length * 40} y1="60" y2="60" className="equity__zero" />
            <polyline points={curve.map((d, i) => `${i * 40 + 20},${60 - (d.run / max) * 55}`).join(" ")} className="equity__line" />
            {curve.map((d, i) => <rect key={d.day} x={i * 40 + 8} width="24" y={d.net >= 0 ? 60 - (d.net / max) * 55 : 60} height={Math.abs(d.net / max) * 55} className={d.net >= 0 ? "equity__up" : "equity__down"}><title>{`${d.day}: ${inr(d.net)}`}</title></rect>)}
          </svg>
        ) : <p className="muted">No past days yet.</p>}
        {snap?.account ? <p className="muted small">Since {snap.account.first_day}: {inr(snap.account.net_inr)} after {inr(snap.account.charges_inr, { signed: false })} charges · account now {inr(snap.account.equity_inr, { signed: false })}</p> : null}
      </section>
      <PnlChart trades={dd.closed} height={200} />
      <section className="card">
        <header className="card__head"><h2>Days</h2></header>
        <ul className="day-list">
          {days.map((d) => (
            <li key={d.day}><span>{d.day}</span><span className="muted">{d.n} trades · {d.wins} won · charges {inr(d.charges, { signed: false })}</span><strong className={tone(d.net)}>{inr(d.net)}</strong></li>
          ))}
        </ul>
      </section>
      <section className="card">
        <header className="card__head"><h2>Today's trades</h2></header>
        <ul className="trade-list">{[...dd.closed].sort((a, b) => (b.closed_ts || 0) - (a.closed_ts || 0)).map((t) => <TradeLine key={t.trade_id} t={t} />)}</ul>
      </section>
    </div>
  );
}

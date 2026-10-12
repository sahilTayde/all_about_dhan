import { PnlChart } from "../components/PnlChart.jsx";
import { CHARGES_LABEL, inr, tone, tradeCsv } from "../lib/deskModel.js";
import { TradeTable } from "./parts.jsx";

function Calendar({ days }) {
  const by = Object.fromEntries(days.map((d) => [d.day, d]));
  if (!days.length) return <div className="empty">No past days yet.</div>;
  const sorted = [...days].sort((a, b) => a.day.localeCompare(b.day));
  const first = new Date(`${sorted[0].day}T00:00:00Z`);
  const last = new Date(`${sorted.at(-1).day}T00:00:00Z`);
  const start = new Date(first); start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7));
  const max = Math.max(1, ...days.map((d) => Math.abs(d.net || 0)));
  const weeks = [];
  for (let d = new Date(start); d <= last; d.setUTCDate(d.getUTCDate() + 7)) {
    weeks.push([0, 1, 2, 3, 4].map((i) => { const x = new Date(d); x.setUTCDate(x.getUTCDate() + i); return x.toISOString().slice(0, 10); }));
  }
  return (
    <div className="cal" data-testid="calendar">
      <div className="cal__head">{["Mon", "Tue", "Wed", "Thu", "Fri"].map((w) => <span key={w}>{w}</span>)}</div>
      {weeks.map((w) => (
        <div key={w[0]} className="cal__row">
          {w.map((day) => {
            const d = by[day];
            const a = d ? Math.max(0.15, Math.abs(d.net || 0) / max) : 0;
            const bg = !d ? "transparent" : (d.net || 0) >= 0 ? `rgba(38,194,129,${a})` : `rgba(240,82,79,${a})`;
            return (
              <div key={day} className={`cal__cell ${d ? "" : "is-empty"}`} style={{ background: bg }} title={d ? `${day}: ${inr(d.net)} · ${d.n} trades` : day}>
                <span className="cal__d">{day.slice(8)}</span>
                {d ? <b className="num">{inr(d.net)}</b> : null}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

export function HistoryPage({ snap, dd }) {
  const days = snap?.days || [];
  const acct = snap?.account;
  let run = 0;
  const curve = [...days].sort((a, b) => a.day.localeCompare(b.day)).map((d) => ({ ...d, run: (run += d.net || 0) }));
  const max = Math.max(1, ...curve.map((d) => Math.abs(d.run)));
  const W = Math.max(1, curve.length - 1);
  const won = days.filter((d) => (d.net || 0) > 0).length;
  return (
    <div className="page" data-testid="history-page">
      <div className="kpis">
        <div><span>Since {acct?.first_day || "—"}</span><b className={`num ${tone(acct?.net_inr)}`}>{inr(acct?.net_inr)}</b><em>after charges</em></div>
        <div><span>Capital now</span><b className="num">{inr(acct?.equity_inr, { signed: false })}</b><em>start {inr(acct?.starting_capital_inr, { signed: false })} + net P&amp;L</em></div>
        <div><span>Charges paid</span><b className="num">{inr(acct?.charges_inr, { signed: false })}</b><em>{CHARGES_LABEL}</em></div>
        <div><span>Green days</span><b className="num">{won} / {days.length}</b><em>days with a profit</em></div>
      </div>
      <div className="grid-2-1">
        <section className="panel">
          <header className="panel__head"><h2>Equity curve</h2><span className="muted">running net after charges</span></header>
          {curve.length > 1 ? (
            <svg className="eq" viewBox="0 0 100 50" preserveAspectRatio="none" role="img" aria-label="Running net by day">
              <line x1="0" x2="100" y1="25" y2="25" className="eq__zero" />
              <polygon className={run >= 0 ? "eq__fill--up" : "eq__fill--down"} points={`0,25 ${curve.map((d, i) => `${(i / W) * 100},${25 - (d.run / max) * 23}`).join(" ")} 100,25`} />
              <polyline className="eq__line" points={curve.map((d, i) => `${(i / W) * 100},${25 - (d.run / max) * 23}`).join(" ")} />
            </svg>
          ) : <div className="empty">Need two days for a curve.</div>}
          <div className="eq__axis"><span>{curve[0]?.day || ""}</span><span>{curve.at(-1)?.day || ""}</span></div>
        </section>
        <section className="panel">
          <header className="panel__head"><h2>Daily P&amp;L</h2></header>
          <Calendar days={days} />
        </section>
      </div>
      <PnlChart trades={dd.closed} height={200} />
      <section className="panel">
        <header className="panel__head"><h2>Today's desk trades</h2><button type="button" className="btn" onClick={() => tradeCsv(dd.closed)} data-testid="csv">Download CSV</button></header>
        <TradeTable rows={[...dd.closed].sort((a, b) => (b.closed_ts || 0) - (a.closed_ts || 0))} />
      </section>
      <section className="panel">
        <header className="panel__head"><h2>Days</h2></header>
        <div className="tbl-wrap"><table className="tbl"><thead><tr><th>Day</th><th className="r">Trades</th><th className="r">Won</th><th className="r">Charges</th><th className="r">Net</th></tr></thead>
          <tbody>{days.map((d) => <tr key={d.day}><td className="num">{d.day}</td><td className="r num">{d.n}</td><td className="r num">{d.wins}</td><td className="r num">{inr(d.charges, { signed: false })}</td><td className={`r num ${tone(d.net)}`}>{inr(d.net)}</td></tr>)}</tbody></table></div>
      </section>
    </div>
  );
}

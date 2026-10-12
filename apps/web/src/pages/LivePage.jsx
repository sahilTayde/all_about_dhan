import { PnlChart } from "../components/PnlChart.jsx";
import { RULES, agedAlerts, exitRule, inr, num, strategyName, strikeOf, tone } from "../lib/deskModel.js";
import { AlertList, DayLossGauge, Reason, TradeLine } from "./parts.jsx";

function SideCard({ und, dd }) {
  const open = dd.open.filter((t) => t.underlying === und);
  const last = dd.closed.filter((t) => t.underlying === und).sort((a, b) => (b.closed_ts || 0) - (a.closed_ts || 0))[0];
  const blocked = dd.guardBlocked.filter((t) => t.underlying === und);
  return (
    <section className="card side-card" data-testid={`side-${und}`}>
      <header className="card__head"><h2>{und}</h2><span className="muted small">{RULES.lots} lots · qty {RULES.qty[und]}</span></header>
      {open.length ? (
        open.map((t) => {
          const pnl = num(t.unrealized_pnl_inr) ?? (num(t.last_ltp) != null && num(t.entry) != null ? (t.last_ltp - t.entry) * (num(t.qty) || RULES.qty[und]) : null);
          return (
            <div key={t.trade_id} className="side-card__trade">
              <p className="side-card__title"><span className="badge badge--live">OPEN</span> {strikeOf(t) ?? "—"} {t.side} · {strategyName(t.book_id)}</p>
              <dl className="kv">
                <div><dt>Bought at</dt><dd>{num(t.entry) ?? "—"}</dd></div>
                <div><dt>Now</dt><dd>{num(t.last_ltp) ?? "—"}</dd></div>
                <div><dt>P&amp;L</dt><dd className={tone(pnl)}>{inr(pnl)}</dd></div>
              </dl>
              <p className="exit-rule">{exitRule(t).text}</p>
            </div>
          );
        })
      ) : (
        <p className="side-card__flat">No open trade.</p>
      )}
      {blocked.length ? <p className="reason reason--muted">Blocked: opposite side ({blocked.map((b) => b.entry_min || "").join(", ")})</p> : null}
      {last ? (
        <p className="side-card__last muted small">
          Last: {strikeOf(last)} {last.side} closed {String(last.closed_ist || "").slice(11, 16)} · <Reason code={last.exit_reason} /> · <strong className={tone(last.realized_pnl_inr)}>{inr(last.realized_pnl_inr)}</strong>
        </p>
      ) : null}
    </section>
  );
}

export function LivePage({ snap, dd, conn }) {
  const allAlerts = agedAlerts(snap?.alerts);
  return (
    <div className="live" data-testid="live-page">
      <section className="card total-card">
        <div>
          <p className="muted small">Today after charges {dd.total.fromFeed ? "" : "(from visible trades)"}</p>
          <p className={`total-card__big ${tone(dd.total.net)}`} data-testid="day-total">{inr(dd.total.net)}</p>
          <p className="muted small">charges {inr(dd.total.charges, { signed: false })} · {dd.total.n ?? 0} trades</p>
        </div>
        <div className="books">
          <div><span>Research book (live + shadow)</span><strong className={tone(dd.research.net)}>{inr(dd.research.net)}</strong><em>{dd.research.trades} trades · charges {inr(dd.research.charges, { signed: false })}</em></div>
          <div><span>Old MIX book (off)</span><strong className={tone(dd.mix.net)}>{inr(dd.mix.net)}</strong><em>{dd.mix.trades} trades · charges {inr(dd.mix.charges, { signed: false })}</em></div>
        </div>
        <DayLossGauge net={dd.live.net} losers={dd.losers} />
        <p className="muted small">Live strategy trades today {dd.live.trades} of {RULES.maxTradesPerDay} · open {dd.open.length} of {RULES.maxOpen} · never opposite sides across NIFTY / SENSEX</p>
      </section>
      <div className="side-by-side">
        <SideCard und="NIFTY" dd={dd} />
        <SideCard und="SENSEX" dd={dd} />
      </div>
      <PnlChart trades={dd.closed} />
      <details className="card details" data-testid="details">
        <summary>Details: today's trades, warnings, health</summary>
        <h3>Today's trades</h3>
        <ul className="trade-list">{[...dd.closed].sort((a, b) => (b.closed_ts || 0) - (a.closed_ts || 0)).map((t) => <TradeLine key={t.trade_id} t={t} />)}</ul>
        <h3>Warnings and engine alerts</h3>
        <AlertList alerts={allAlerts} />
        <h3>Health</h3>
        <ul className="health-list">{(snap?.health || []).map((h) => <li key={h.id}><i className={`dot dot--${h.tone}`} /> {h.name}: <span className="muted">{h.detail}</span></li>)}</ul>
        <p className="muted small">Feed: {conn}</p>
      </details>
    </div>
  );
}

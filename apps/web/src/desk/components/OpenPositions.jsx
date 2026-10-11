import { clock as clockOf, fmtElapsed, inr, moneyClass, outcomeLabel, pathProgress, pnlPct, px, ticketState, tradeNow } from "../../lib/paperBoard.js";
import { premiumMarks } from "../../lib/tradeMarks.js";
import { PremiumSpark } from "./EquitySpark.jsx";
import { RadialGauge } from "./RadialGauge.jsx";

function Cell({ label, value, tone, title }) {
  return (
    <div className="kv" title={title}>
      <dt>{label}</dt>
      <dd className={tone || ""}>{value}</dd>
    </div>
  );
}

const pts = (n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2)}`);

function PositionCard({ t, clock, nowMs, selected, onSelect }) {
  const n = tradeNow(t, { nowMs });
  const s = ticketState(t, { clock });
  const prog = pathProgress(n.entry, n.ltp, n.stop, n.t1 === "hit" ? t.target : n.t1);
  const pct = pnlPct(n.entry, n.ltp);
  return (
    <li>
      <button
        type="button"
        className={`pos-card current-trade${selected ? " is-selected" : ""}`}
        data-testid="pos-card"
        data-und={t.underlying}
        onClick={() => onSelect?.(t)}
      >
        <header>
          <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
          <strong>
            {t.underlying} {t.atm_strike ?? "—"}
          </strong>
          <span className={`state-pill state-pill--${s.key}`}>{s.label}</span>
        </header>
        <div className="pos-card__body">
          <dl className="kv-grid">
            <Cell label="Entry" value={px(n.entry)} />
            <Cell label="Premium" value={px(n.ltp)} tone={moneyClass(n.pts)} />
            <Cell label="P&L ₹" value={inr(n.inr)} tone={moneyClass(n.inr)} title="(LTP − entry) × qty" />
            <Cell label="P&L %" value={pct == null ? "—" : `${pct > 0 ? "+" : ""}${pct}%`} tone={moneyClass(pct)} />
            <Cell label="SL" value={px(n.stop)} />
            <Cell label="Target" value={px(typeof n.t1 === "number" ? n.t1 : t.target)} />
            <Cell label="Time" value={fmtElapsed(n.elapsedMs)} />
            <Cell label="Pts" value={pts(n.pts)} tone={moneyClass(n.pts)} />
          </dl>
          <RadialGauge progress={prog} label={`${t.underlying} path`} />
          <PremiumSpark points={premiumMarks(t).points} label={`${t.underlying} premium`} width={168} height={52} />
        </div>
      </button>
    </li>
  );
}

/** Open paper fills. NIFTY and SENSEX sit side by side when both are live. */
export function OpenPositions({ rows, clock, hold, last, onSelect, selectedId }) {
  const list = rows || [];
  if (!list.length) {
    return (
      <section className="widget current-trade" data-testid="open-positions">
        <header className="widget__head">
          <h2>Open</h2>
          <span className={`state-pill state-pill--${hold ? "hold" : "waiting"}`}>{hold ? "ON HOLD" : "FLAT"}</span>
        </header>
        <div className="current-trade__empty">
          <p className="current-trade__big">{hold ? "On hold" : "No open paper fill"}</p>
          <p className="muted">{hold || "Empty book. The next CE/PE lands here when the board writes it."}</p>
          {last ? (
            <dl className="kv-grid kv-grid--3 last-ticket">
              <div className="kv">
                <dt>Last ticket</dt>
                <dd>{`${last.underlying} ${last.side} ${last.atm_strike ?? ""}`}</dd>
              </div>
              <div className="kv">
                <dt>Net ₹</dt>
                <dd className={moneyClass(last.realized_pnl_inr)}>{inr(last.realized_pnl_inr)}</dd>
              </div>
              <div className="kv">
                <dt>Out</dt>
                <dd>{clockOf(last.closed_ist) === "—" ? outcomeLabel(last) : clockOf(last.closed_ist)}</dd>
              </div>
            </dl>
          ) : null}
        </div>
      </section>
    );
  }
  const nowMs = clock?.replay && clock.ms != null ? clock.ms : Date.now();
  const totals = list.reduce(
    (acc, t) => {
      const n = tradeNow(t, { nowMs });
      if (n.inr != null) acc.inr += n.inr;
      acc.n += 1;
      return acc;
    },
    { inr: 0, n: 0 },
  );
  return (
    <section className="widget open-positions" data-testid="open-positions">
      <header className="widget__head">
        <h2>Open</h2>
        <span className="muted small">{list.length} paper fill{list.length === 1 ? "" : "s"}</span>
      </header>
      <ul className={`pos-list${list.length > 1 ? " pos-list--dual" : ""}`}>
        {list.map((t) => (
          <PositionCard key={t.trade_id} t={t} clock={clock} nowMs={nowMs} selected={selectedId === t.trade_id} onSelect={onSelect} />
        ))}
      </ul>
      {list.length > 1 ? (
        <div className="pos-total" data-testid="pos-total">
          <span>Combined</span>
          <strong className={moneyClass(totals.inr)}>{inr(totals.inr)}</strong>
          <span className="muted small">{totals.n} opens · before charges</span>
        </div>
      ) : null}
    </section>
  );
}

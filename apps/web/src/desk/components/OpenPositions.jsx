import { clock as clockOf, fmtElapsed, inr, moneyClass, outcomeLabel, px, ticketState, tradeNow } from "../../lib/paperBoard.js";
import { premiumMarks } from "../../lib/tradeMarks.js";
import { PremiumSpark } from "./EquitySpark.jsx";

function Cell({ label, value, tone, title }) {
  return (
    <div className="kv" title={title}>
      <dt>{label}</dt>
      <dd className={tone || ""}>{value}</dd>
    </div>
  );
}

const pts = (n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2)}`);

/** Open paper fills: live premium, P&L, time-in-trade. Click opens the drawer. */
export function OpenPositions({ rows, clock, hold, last, onSelect, selectedId }) {
  const list = rows || [];
  if (!list.length) {
    return (
      <section className="panel current-trade" data-testid="open-positions">
        <div className="panel__head">
          <h2>Open</h2>
          <span className={`state-pill state-pill--${hold ? "hold" : "waiting"}`}>{hold ? "ON HOLD" : "FLAT"}</span>
        </div>
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
  return (
    <section className="panel open-positions" data-testid="open-positions">
      <div className="panel__head">
        <h2>Open</h2>
        <span className="muted small">{list.length} paper fill{list.length === 1 ? "" : "s"}</span>
      </div>
      <ul className="pos-list">
        {list.map((t) => {
          const n = tradeNow(t, { nowMs });
          const s = ticketState(t, { clock });
          const selected = selectedId === t.trade_id;
          return (
            <li key={t.trade_id}>
              <button
                type="button"
                className={`pos-card current-trade${selected ? " is-selected" : ""}`}
                onClick={() => onSelect?.(t)}
              >
                <header>
                  <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>BUY {t.side}</span>
                  <strong>
                    {t.underlying} {t.atm_strike ?? "—"}
                  </strong>
                  <span className={`state-pill state-pill--${s.key}`}>{s.label}</span>
                </header>
                <div className="pos-card__body">
                  <dl className="kv-grid">
                    <Cell label="Premium" value={px(n.ltp)} tone={moneyClass(n.pts)} />
                    <Cell label="LTP" value={px(n.ltp)} tone={moneyClass(n.pts)} />
                    <Cell label="Entry" value={px(n.entry)} />
                    <Cell label="P&L ₹" value={inr(n.inr)} tone={moneyClass(n.inr)} title="(LTP − entry) × qty, before charges" />
                    <Cell label="Pts" value={pts(n.pts)} tone={moneyClass(n.pts)} />
                    <Cell label="Time" value={fmtElapsed(n.elapsedMs)} />
                  </dl>
                  <PremiumSpark points={premiumMarks(t).points} label={`${t.underlying} premium`} width={168} height={52} />
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

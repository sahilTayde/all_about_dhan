import { clock, inr, moneyClass, outcomeLabel, px } from "../../lib/paperBoard.js";

/** Compact today tape. Click a row to open the trade drawer. */
export function TradeTimeline({ rows, onSelect, selectedId }) {
  const list = rows || [];
  return (
    <section className="widget trade-timeline" data-testid="trade-timeline">
      <header className="widget__head">
        <h2>Today’s tape</h2>
        <span className="muted small">{list.length ? `${list.length} prints` : "empty"}</span>
      </header>
      {!list.length ? (
        <p className="empty-state" data-testid="timeline-empty">
          No paper tickets today.
        </p>
      ) : (
        <ol className="tape panel-scroll">
          {list.map((t) => {
            const open = !t.closed_ist && t.exit == null;
            const pnl = t.realized_pnl_inr;
            return (
              <li key={t.trade_id}>
                <button
                  type="button"
                  className={`tape-row${selectedId === t.trade_id ? " is-selected" : ""}`}
                  onClick={() => onSelect?.(t)}
                >
                  <span className="tape-row__time">{clock(t.opened_ist)}</span>
                  <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
                  <strong>
                    {t.underlying} {t.atm_strike ?? "—"}
                  </strong>
                  <span className="tape-row__px">
                    {px(t.entry ?? t.limit_price)}
                    {t.exit != null ? ` → ${px(t.exit)}` : t.last_ltp != null ? ` · ${px(t.last_ltp)}` : ""}
                  </span>
                  <span className={`tape-row__pnl ${moneyClass(open ? null : pnl)}`}>{open ? "OPEN" : inr(pnl)}</span>
                  <span className="tape-row__why">{open ? "IN TRADE" : outcomeLabel(t)}</span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

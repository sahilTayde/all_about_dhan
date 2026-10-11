import { lazy, Suspense } from "react";
import { DecisionTrace } from "../../components/DecisionTrace.jsx";
import { fmtElapsed, inr, moneyClass, outcomeLabel, px, tradeNow } from "../../lib/paperBoard.js";
import { premiumMarks } from "../../lib/tradeMarks.js";

const PremiumChart = lazy(() => import("./PremiumChart.jsx").then((m) => ({ default: m.PremiumChart })));

/** Right-hand trade detail. Chart + exit reason + market type at entry. */
export function TradeDrawer({ trade, clock, onClose }) {
  if (!trade) return null;
  const nowMs = clock?.replay && clock.ms != null ? clock.ms : Date.now();
  const n = tradeNow(trade, { nowMs });
  const marks = premiumMarks(trade);
  const market = marks.marketKind || "—";
  const reason = marks.reason ? outcomeLabel(trade) : "—";
  return (
    <div className="drawer-root" data-testid="trade-drawer">
      <button type="button" className="drawer-scrim" aria-label="Close trade" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-labelledby="drawer-title">
        <header className="drawer__head">
          <div>
            <p className="desk-kicker">Paper fill</p>
            <h2 id="drawer-title">
              {trade.underlying} {trade.side} {trade.atm_strike ?? ""}
            </h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <dl className="drawer__facts">
          <div>
            <dt>Exit</dt>
            <dd>{reason}</dd>
          </div>
          <div>
            <dt>Market at entry</dt>
            <dd>{market}</dd>
          </div>
          <div>
            <dt>Net ₹</dt>
            <dd className={moneyClass(trade.realized_pnl_inr)}>{inr(trade.realized_pnl_inr)}</dd>
          </div>
          <div>
            <dt>Premium</dt>
            <dd>
              {px(n.entry)}
              {trade.exit != null ? ` → ${px(trade.exit)}` : n.ltp != null ? ` · ${px(n.ltp)}` : ""}
            </dd>
          </div>
          <div>
            <dt>Time in trade</dt>
            <dd>{trade.closed_ts && trade.opened_ts ? fmtElapsed((Number(trade.closed_ts) - Number(trade.opened_ts)) * 1000) : fmtElapsed(n.elapsedMs)}</dd>
          </div>
        </dl>
        <Suspense fallback={<p className="muted">Loading chart…</p>}>
          <PremiumChart marks={marks} />
        </Suspense>
        <DecisionTrace
          refreshKey={trade.last_updated_ts}
          tradeId={trade.trade_id}
          label={`${trade.underlying} ${trade.side} ${trade.atm_strike ?? ""}`}
        />
      </aside>
    </div>
  );
}

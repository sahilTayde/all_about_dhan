import { AccountPanel } from "../../components/AccountPanel.jsx";
import { DecisionTrace } from "../../components/DecisionTrace.jsx";
import { FounderControls } from "../../components/FounderControls.jsx";
import { HealthPanel } from "../../components/HealthPanel.jsx";
import { SpillLedger } from "../../components/SpillLedger.jsx";
import { TradeHistory } from "../../components/TradeHistory.jsx";

/** Raw desk dump. Hidden until Advanced is on. */
export function AdvancedPanel({
  snap,
  d,
  clock,
  conn,
  indexing,
  today,
  traceRow,
  onSelect,
  traceId,
}) {
  return (
    <div className="advanced-panel grid" data-testid="advanced-panel">
      <p className="muted small span-12">
        Advanced · debug dump. Not the trader view. PAPER only. No live orders.
      </p>
      <div className="span-8">
        <HealthPanel rows={snap?.health} founder={snap?.founder} conn={conn} />
      </div>
      <div className="span-4">
        <AccountPanel account={snap?.account} today={today} founderBook={snap?.founder_book} indexing={indexing} />
      </div>
      <div className="span-12">
        <FounderControls compact />
      </div>
      <div className="span-12">
        <DecisionTrace
          refreshKey={traceRow?.last_updated_ts}
          tradeId={traceId}
          label={
            traceRow
              ? `${traceRow.underlying} ${traceRow.side} ${traceRow.atm_strike ?? ""} · ${String(traceRow.opened_ist || "").slice(11, 19)}`
              : null
          }
        />
      </div>
      <section className="panel span-12">
        <h2>Trade history</h2>
        <TradeHistory
          indexing={indexing}
          rows={[...(d?.uniqueOpen || []), ...(d?.uniqueClosed || [])]}
          days={snap?.days}
          liveDay={snap?.board?.session_ist_date}
          clock={clock}
          onSelect={onSelect}
          selectedId={traceId}
        />
      </section>
      <div className="span-12">
        <SpillLedger exam={snap?.exam} />
      </div>
    </div>
  );
}

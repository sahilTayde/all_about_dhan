import { inr, moneyClass, pct } from "../../lib/paperBoard.js";
import { EquitySpark } from "./EquitySpark.jsx";

function Stat({ label, value, tone }) {
  return (
    <div className="slot-stat">
      <span>{label}</span>
      <strong className={tone || ""}>{value}</strong>
    </div>
  );
}

export function StrategyCard({ card, onOpen }) {
  const empty = !card.nFilled && !card.nOpen;
  return (
    <article
      className={`slot-card slot-card--${String(card.badge).toLowerCase()}${card.shadow ? " slot-card--shadow" : ""}`}
      data-testid="strategy-card"
      data-book={card.id}
      data-name={card.name}
      data-badge={card.badge}
    >
      <header>
        <div>
          <p className="slot-card__kind">{card.shadow ? "Shadow" : card.kind}</p>
          <h3>{card.name}</h3>
          <p className="slot-card__id">{card.bookId}</p>
        </div>
        <span className={`slot-badge slot-badge--${String(card.badge).toLowerCase()}`}>{card.badge}</span>
      </header>
      {empty ? (
        <p className="empty-state">No paper fills on this book.</p>
      ) : (
        <>
          <p className={`slot-card__net ${moneyClass(card.net)}`}>{inr(card.net)}</p>
          <EquitySpark curve={card.curve} label={card.bookId} />
          <div className="slot-card__grid">
            <Stat label="Trades" value={card.nFilled ?? "—"} />
            <Stat label="Win %" value={card.winPct == null ? "—" : pct(card.winPct)} />
            <Stat label="vs random" value={card.vsRandom == null ? "—" : `${card.vsRandom > 0 ? "+" : ""}${Number(card.vsRandom).toFixed(1)} pt`} />
            <Stat label="Avg win" value={inr(card.avgWin)} tone={moneyClass(card.avgWin)} />
            <Stat label="Avg loss" value={inr(card.avgLoss)} tone={moneyClass(card.avgLoss)} />
            <Stat label="Max DD" value={card.maxDd == null ? "—" : inr(-card.maxDd)} tone="is-down" />
          </div>
        </>
      )}
      {onOpen && card.nFilled ? (
        <button type="button" className="link-btn" onClick={() => onOpen(card)}>
          Latest fill
        </button>
      ) : null}
    </article>
  );
}

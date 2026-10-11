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

export function StrategyCard({ card, onOpen, onPause }) {
  const empty = !card.nFilled && !card.nOpen;
  const vs = card.vsRandom == null && card.randomWin == null ? "pending" : card.vsRandom == null ? "pending" : `${card.vsRandom > 0 ? "+" : ""}${Number(card.vsRandom).toFixed(1)} pt`;
  return (
    <article
      className={`widget slot-card slot-card--${String(card.badge).toLowerCase()}${card.shadow ? " slot-card--shadow" : ""}`}
      data-testid="strategy-card"
      data-book={card.id}
      data-name={card.name}
      data-badge={card.badge}
    >
      <header className="widget__head">
        <div>
          <p className="slot-card__kind">{card.shadow ? "Shadow" : card.kind}</p>
          <h3>{card.name}</h3>
          <p className="slot-card__id">{card.bookId}</p>
        </div>
        <span className={`slot-badge slot-badge--${String(card.badge).toLowerCase()}`}>
          {card.badge}
          <small> n={card.nFilled || 0}</small>
        </span>
      </header>
      {empty ? (
        <p className="empty-state">No paper fills on this book.</p>
      ) : (
        <>
          <p className={`slot-card__net ${moneyClass(card.net)}`}>{inr(card.net)}</p>
          <EquitySpark curve={card.curve} label={card.bookId} />
          <ol className="dot-streak" aria-label="Last fills">
            {(card.dots || []).map((d, i) => (
              <li key={`${d}-${i}`} className={`dot-streak__el dot-streak__el--${d}`} />
            ))}
          </ol>
          <div className="slot-card__grid">
            <Stat label="Trades" value={card.nFilled ?? "—"} />
            <Stat label="Win %" value={card.winPct == null ? "—" : pct(card.winPct)} />
            <Stat label="vs random" value={vs} />
            <Stat label="Payoff" value={card.payoff == null ? "—" : card.payoff.toFixed(2)} />
            <Stat label="Avg win" value={inr(card.avgWin)} tone={moneyClass(card.avgWin)} />
            <Stat label="Avg loss" value={inr(card.avgLoss)} tone={moneyClass(card.avgLoss)} />
            <Stat label="Max DD" value={card.maxDd == null ? "—" : inr(-card.maxDd)} tone="is-down" />
            <Stat label="Random wr" value={card.randomWin == null ? "pending" : pct(card.randomWin)} />
          </div>
        </>
      )}
      <div className="btn-row">
        {onOpen && card.nFilled ? (
          <button type="button" className="btn btn--ghost" onClick={() => onOpen(card)}>
            Latest fill
          </button>
        ) : null}
        {onPause ? (
          <button type="button" className="btn btn--secondary" onClick={() => onPause(card)}>
            Pause slot
          </button>
        ) : null}
      </div>
    </article>
  );
}

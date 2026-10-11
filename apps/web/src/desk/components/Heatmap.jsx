import { inr, moneyClass } from "../../lib/paperBoard.js";

const KINDS = ["TREND", "CHOP", "COIL", "EXPIRY"];

function kindOf(t) {
  const raw = String(t.market_kind_open || t.index_regime || "").toUpperCase();
  if (raw.includes("EXPIR")) return "EXPIRY";
  if (raw.includes("COIL") || raw.includes("PIN")) return "COIL";
  if (raw.includes("CHOP") || raw.includes("SIDE")) return "CHOP";
  if (raw.includes("TREND")) return "TREND";
  return "CHOP";
}

/** Strategy × market-type net heatmap. Empty cells stay empty. */
export function Heatmap({ cards, trades }) {
  const rows = (cards || []).filter((c) => !c.shadow);
  const cells = {};
  for (const t of trades || []) {
    const id = t.strategy_id || t.book_id;
    const k = kindOf(t);
    const key = `${id}|${k}`;
    cells[key] = (cells[key] || 0) + (Number(t.realized_pnl_inr) || 0);
  }
  return (
    <section className="widget" data-testid="heatmap">
      <header className="widget__head">
        <h2>Playbook</h2>
        <span className="muted small">Net ₹ after costs</span>
      </header>
      <div className="heatmap">
        <div className="heatmap__corner" />
        {KINDS.map((k) => (
          <div key={k} className="heatmap__colh">
            {k}
          </div>
        ))}
        {rows.map((c) => (
          <div key={c.id} className="heatmap__row">
            <div className="heatmap__rowh">{c.name}</div>
            {KINDS.map((k) => {
              const v = cells[`${c.bookId}|${k}`];
              const tone = v == null ? "empty" : v > 0 ? "up" : v < 0 ? "down" : "flat";
              return (
                <div key={k} className={`heatmap__cell heatmap__cell--${tone}`} title={v == null ? undefined : String(v)}>
                  {v == null ? "—" : <span className={moneyClass(v)}>{inr(v)}</span>}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

import { inr, moneyClass } from "../../lib/paperBoard.js";

/** Animated gradient ₹ net after costs. */
export function DayPnlHero({ net, charges, gross, trades, clock, indexing }) {
  const empty = net == null && !indexing;
  const tone = moneyClass(net);
  return (
    <section className={`widget day-pnl day-pnl--glow ${tone}`} data-testid="day-pnl">
      <p className="day-pnl__kicker">Today · every ₹ is net after Dhan costs</p>
      {indexing ? (
        <p className="day-pnl__num needs-history">
          <span className="indexing">Indexing history…</span>
        </p>
      ) : empty ? (
        <p className="day-pnl__num day-pnl__num--empty">—</p>
      ) : (
        <p className={`day-pnl__num ${tone}`}>{inr(net)}</p>
      )}
      <ul className="day-pnl__meta">
        <li>Gross {gross == null ? "—" : inr(gross)}</li>
        <li>Charges {charges == null ? "—" : inr(charges, { signed: false })}</li>
        <li>{trades == null ? "—" : `${trades} trade${Number(trades) === 1 ? "" : "s"}`}</li>
        <li>{clock?.label || "—"}</li>
      </ul>
    </section>
  );
}

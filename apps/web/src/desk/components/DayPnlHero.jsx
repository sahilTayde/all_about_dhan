import { inr, moneyClass } from "../../lib/paperBoard.js";

/** Big ₹ net after costs for the session day. Empty when the board has no today net. */
export function DayPnlHero({ net, charges, gross, trades, clock, indexing }) {
  const empty = net == null && !indexing;
  return (
    <section className={`day-pnl ${moneyClass(net)}`} data-testid="day-pnl">
      <p className="day-pnl__kicker">Today · net after costs</p>
      {indexing ? (
        <p className="day-pnl__num needs-history">
          <span className="indexing">Indexing history…</span>
        </p>
      ) : empty ? (
        <p className="day-pnl__num day-pnl__num--empty">—</p>
      ) : (
        <p className={`day-pnl__num ${moneyClass(net)}`}>{inr(net)}</p>
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

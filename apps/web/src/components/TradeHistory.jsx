import { useMemo, useState } from "react";
import {
  clock,
  inr,
  moneyClass,
  outcomeLabel,
  outcomeSlug,
  px,
} from "../lib/paperBoard.js";

function OutcomePill({ label }) {
  return <span className={`out-pill out-pill--${outcomeSlug(label)}`}>{label}</span>;
}

export function TradeHistory({ rows, regimes, fillRooms, onOpen, pageSize = 12 }) {
  const [index, setIndex] = useState("ALL");
  const [side, setSide] = useState("ALL");
  const [out, setOut] = useState("ALL");
  const [more, setMore] = useState(false);

  const filtered = useMemo(() => {
    return (rows || []).filter((t) => {
      if (index !== "ALL" && t.underlying !== index) return false;
      if (side !== "ALL" && t.side !== side) return false;
      if (out !== "ALL" && outcomeLabel(t) !== out) return false;
      return true;
    });
  }, [rows, index, side, out]);

  const shown = more ? filtered : filtered.slice(0, pageSize);

  return (
    <div>
      <div className="filter-row" role="group" aria-label="Filter book">
        {["ALL", "NIFTY", "BANKNIFTY", "SENSEX"].map((v) => (
          <button key={v} type="button" className={`chip ${index === v ? "chip--active" : ""}`} onClick={() => setIndex(v)}>
            {v}
          </button>
        ))}
        {["ALL", "CE", "PE"].map((v) => (
          <button key={v} type="button" className={`chip ${side === v ? "chip--active" : ""}`} onClick={() => setSide(v)}>
            {v}
          </button>
        ))}
        {["ALL", "TARGET HIT", "TARGET 2 HIT", "STOP LOSS HIT", "STOP LOSS TRAIL HIT", "CANCELLED", "TIME"].map((v) => (
          <button key={v} type="button" className={`chip ${out === v ? "chip--active" : ""}`} onClick={() => setOut(v)}>
            {v === "ALL" ? "ALL exits" : v}
          </button>
        ))}
      </div>
      <p className="muted">
        {filtered.length} trades in this filter · {shown.length} shown
      </p>
      <div className="book-table-wrap">
        <table className="book-table desk-history">
          <thead>
            <tr>
              <th>Time</th>
              <th>Index</th>
              <th>CE/PE</th>
              <th>Strike</th>
              <th>Spot</th>
              <th>Entry</th>
              <th>SL</th>
              <th>Target</th>
              <th>P/L</th>
              <th>Status</th>
              <th>Models</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((t) => {
              const label = outcomeLabel(t);
              const spotPx = t.spot_at_entry ?? regimes?.[t.underlying]?.itm_bin?.index;
              const hasRoom = fillRooms?.[t.trade_id];
              return (
                <tr
                  key={t.trade_id}
                  className={hasRoom ? "is-click" : ""}
                  onClick={() => hasRoom && onOpen && onOpen(t)}
                >
                  <td>{clock(t.last_updated_ist || t.closed_ist)}</td>
                  <td>{t.underlying}</td>
                  <td>
                    <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
                  </td>
                  <td className="num">{t.atm_strike}</td>
                  <td className="num">{px(spotPx)}</td>
                  <td className="num">{px(t.entry ?? t.limit_price)}</td>
                  <td className="num">{px(t.stop)}</td>
                  <td className="num">{px(t.target)}</td>
                  <td className={`num ${moneyClass(t.realized_pnl_inr)}`}>{inr(t.realized_pnl_inr)}</td>
                  <td>
                    <OutcomePill label={label} />
                  </td>
                  <td>{(t.books || [t.book_id]).join(", ")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {filtered.length > pageSize ? (
        <button type="button" className="refresh-btn" onClick={() => setMore((m) => !m)}>
          {more ? "Show less" : `Show all ${filtered.length}`}
        </button>
      ) : null}
    </div>
  );
}

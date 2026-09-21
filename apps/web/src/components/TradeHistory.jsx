import { useMemo, useState } from "react";
import {
  inr,
  moneyClass,
  outcomeLabel,
  outcomeSlug,
  px,
} from "../lib/paperBoard.js";

function OutcomePill({ label }) {
  return <span className={`out-pill out-pill--${outcomeSlug(label)}`}>{label}</span>;
}

function fullClock(ist) {
  if (!ist) return "—";
  return String(ist).replace("T", " ").slice(0, 19);
}

function modelsFor(t) {
  const names = [...(t.model_names || [])];
  if (!names.length) {
    for (const b of t.books || []) if (b && b !== "MIX-DEFAULT-BUY") names.push(b);
  }
  return names.length ? names.join(", ") : t.book_id || "—";
}

function Field({ label, value, onChange, options }) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt === "ALL" ? `All ${label.toLowerCase()}` : opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export function TradeHistory({ rows, regimes, fillRooms, onOpen, pageSize = 12 }) {
  const [index, setIndex] = useState("ALL");
  const [side, setSide] = useState("ALL");
  const [out, setOut] = useState("ALL");
  const [more, setMore] = useState(false);

  const indexOpts = useMemo(() => {
    const seen = [...new Set((rows || []).map((t) => t.underlying).filter(Boolean))].sort();
    return ["ALL", ...seen];
  }, [rows]);
  const sideOpts = useMemo(() => {
    const seen = [...new Set((rows || []).map((t) => t.side).filter(Boolean))].sort();
    return ["ALL", ...seen];
  }, [rows]);
  const outOpts = useMemo(() => {
    const seen = [...new Set((rows || []).map((t) => outcomeLabel(t)).filter(Boolean))].sort();
    return ["ALL", ...seen];
  }, [rows]);

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
        <Field label="Index" value={index} onChange={setIndex} options={indexOpts} />
        <Field label="Side" value={side} onChange={setSide} options={sideOpts} />
        <Field label="Exit" value={out} onChange={setOut} options={outOpts} />
      </div>
      <p className="muted">
        {filtered.length} trades in this filter · {shown.length} shown
      </p>
      <div className="book-table-wrap">
        <table className="book-table desk-history">
          <thead>
            <tr>
              <th>Start</th>
              <th>End</th>
              <th>Index</th>
              <th>CE/PE</th>
              <th>Strike</th>
              <th>Spot</th>
              <th>Lot size</th>
              <th>Lots</th>
              <th>Investment</th>
              <th>Entry</th>
              <th>Exit / cancel premium</th>
              <th>Points</th>
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
              const points = t.realized_pnl ?? (t.exit != null && t.entry != null ? Number(t.exit) - Number(t.entry) : null);
              return (
                <tr
                  key={t.trade_id}
                  className={hasRoom ? "is-click" : ""}
                  onClick={() => hasRoom && onOpen && onOpen(t)}
                >
                  <td>{fullClock(t.opened_ist)}</td>
                  <td>{fullClock(t.closed_ist || t.last_updated_ist)}</td>
                  <td>{t.underlying}</td>
                  <td>
                    <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
                  </td>
                  <td className="num">{t.atm_strike}</td>
                  <td className="num">{px(spotPx)}</td>
                  <td className="num">{t.lot_size ?? "—"}</td>
                  <td className="num">{t.lots ?? "—"}</td>
                  <td className="num">{inr(t.notional_inr, { signed: false })}</td>
                  <td className="num">{px(t.entry ?? t.limit_price)}</td>
                  <td className="num">{px(t.exit)}</td>
                  <td className={`num ${moneyClass(points)}`}>{points == null ? "—" : Number(points).toFixed(2)}</td>
                  <td className="num">{px(t.stop)}</td>
                  <td className="num">{px(t.target)}</td>
                  <td className={`num ${moneyClass(t.realized_pnl_inr)}`}>{inr(t.realized_pnl_inr)}</td>
                  <td>
                    <OutcomePill label={label} />
                  </td>
                  <td>{modelsFor(t)}</td>
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

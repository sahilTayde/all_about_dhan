import { useEffect, useMemo, useState } from "react";
import {
  inr,
  moneyClass,
  outcomeLabel,
  outcomeSlug,
  px,
} from "../lib/paperBoard.js";

const COLS_KEY = "desk.tradeHistory.columns.v1";

const COLUMNS = [
  { id: "start", label: "Start", long: false },
  { id: "end", label: "End", long: false },
  { id: "index", label: "Index", long: false },
  { id: "side", label: "CE/PE", long: false },
  { id: "strike", label: "Strike", long: false },
  { id: "spot", label: "Spot", long: false },
  { id: "lotSize", label: "Lot size", long: false },
  { id: "lots", label: "Lots", long: false },
  { id: "investment", label: "Investment", long: false },
  { id: "entry", label: "Entry", long: false },
  { id: "exitPx", label: "Exit / cancel premium", long: false },
  { id: "points", label: "Points", long: false },
  { id: "sl", label: "SL", long: false },
  { id: "target", label: "Target", long: false },
  { id: "pnl", label: "P/L", long: false },
  { id: "status", label: "Status", long: false },
  { id: "ticket", label: "Ticket", long: false },
  { id: "models", label: "Models", long: true },
  { id: "notes", label: "Notes / reason", long: true },
  { id: "details", label: "Details", long: true },
];

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

function detailsFor(t) {
  return JSON.stringify({
    trade_id: t.trade_id || null,
    books: t.books || [t.book_id],
    exit_reason: t.exit_reason || t.status || null,
    filled: t.filled ?? null,
    qty: t.qty ?? null,
    expiry: t.expiry || t.expiry_ist || null,
  });
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

function loadHidden() {
  try {
    const raw = localStorage.getItem(COLS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) return parsed.filter((id) => COLUMNS.some((c) => c.id === id));
  } catch {
    /* ignore */
  }
  return [];
}

export function TradeHistory({ rows, regimes, fillRooms, onOpen, pageSize = 12 }) {
  const [index, setIndex] = useState("ALL");
  const [side, setSide] = useState("ALL");
  const [out, setOut] = useState("ALL");
  const [more, setMore] = useState(false);
  const [hidden, setHidden] = useState(() => loadHidden());
  const [colsOpen, setColsOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(COLS_KEY, JSON.stringify(hidden));
    } catch {
      /* ignore */
    }
  }, [hidden]);

  const visible = useMemo(() => COLUMNS.filter((c) => !hidden.includes(c.id)), [hidden]);

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

  function cell(t, id) {
    const label = outcomeLabel(t);
    const spotPx = t.spot_at_entry ?? regimes?.[t.underlying]?.itm_bin?.index;
    const points = t.realized_pnl ?? (t.exit != null && t.entry != null ? Number(t.exit) - Number(t.entry) : null);
    switch (id) {
      case "start":
        return fullClock(t.opened_ist);
      case "end":
        return fullClock(t.closed_ist || t.last_updated_ist);
      case "index":
        return t.underlying;
      case "side":
        return <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>;
      case "strike":
        return t.atm_strike ?? "—";
      case "spot":
        return px(spotPx);
      case "lotSize":
        return t.lot_size ?? "—";
      case "lots":
        return t.lots ?? "—";
      case "investment":
        return inr(t.notional_inr, { signed: false });
      case "entry":
        return px(t.entry ?? t.limit_price);
      case "exitPx":
        return px(t.exit);
      case "points":
        return <span className={moneyClass(points)}>{points == null ? "—" : Number(points).toFixed(2)}</span>;
      case "sl":
        return px(t.stop);
      case "target":
        return px(t.target);
      case "pnl":
        return <span className={moneyClass(t.realized_pnl_inr)}>{inr(t.realized_pnl_inr)}</span>;
      case "status":
        return <OutcomePill label={label} />;
      case "ticket":
        return t.trade_id || "—";
      case "models":
        return modelsFor(t);
      case "notes":
        return t.justification || t.exit_reason || t.status || "—";
      case "details":
        return detailsFor(t);
      default:
        return "—";
    }
  }

  return (
    <div>
      <div className="filter-row" role="group" aria-label="Filter book">
        <Field label="Index" value={index} onChange={setIndex} options={indexOpts} />
        <Field label="Side" value={side} onChange={setSide} options={sideOpts} />
        <Field label="Exit" value={out} onChange={setOut} options={outOpts} />
        <button type="button" className="refresh-btn" onClick={() => setColsOpen((v) => !v)}>
          {colsOpen ? "Hide column picker" : "Columns"}
        </button>
      </div>
      {colsOpen ? (
        <div className="col-picker" role="group" aria-label="Show or hide columns">
          {COLUMNS.map((c) => (
            <label key={c.id}>
              <input
                type="checkbox"
                checked={!hidden.includes(c.id)}
                onChange={() =>
                  setHidden((prev) => (prev.includes(c.id) ? prev.filter((x) => x !== c.id) : [...prev, c.id]))
                }
              />
              {c.label}
            </label>
          ))}
        </div>
      ) : null}
      <p className="muted">
        {filtered.length} trades in this filter · {shown.length} shown · this table scrolls inside the section
      </p>
      <div className="table-scroll table-scroll--history">
        <table className="book-table desk-history">
          <thead>
            <tr>
              {visible.map((c) => (
                <th key={c.id} className={c.long ? "cell-wrap" : ""}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((t) => {
              const hasRoom = fillRooms?.[t.trade_id];
              return (
                <tr
                  key={t.trade_id}
                  className={hasRoom ? "is-click" : ""}
                  onClick={() => hasRoom && onOpen && onOpen(t)}
                >
                  {visible.map((c) => (
                    <td
                      key={c.id}
                      className={`${c.long ? "cell-wrap" : ""} ${["strike", "spot", "lotSize", "lots", "investment", "entry", "exitPx", "points", "sl", "target", "pnl"].includes(c.id) ? "num" : ""}`}
                    >
                      {cell(t, c.id)}
                    </td>
                  ))}
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

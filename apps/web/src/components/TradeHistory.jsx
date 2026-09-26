import { Fragment, useEffect, useMemo, useState } from "react";
import {
  inr,
  moneyClass,
  outcomeLabel,
  outcomeSlug,
  px,
} from "../lib/paperBoard.js";

const COLS_KEY = "desk.tradeHistory.columns.v2";

// `key` columns are on by default and sized to fit at 1280px; the rest live in the row detail
// and can be switched on with the column picker (the table then scrolls inside its box).
const COLUMNS = [
  { id: "start", label: "In", key: true },
  { id: "end", label: "Out", key: true },
  { id: "index", label: "Index", key: true },
  { id: "side", label: "Side", key: true },
  { id: "strike", label: "Strike", key: true, num: true },
  { id: "spot", label: "Spot @ entry", key: true, num: true },
  { id: "entry", label: "Entry", key: true, num: true },
  { id: "exitPx", label: "Exit", key: true, num: true },
  { id: "points", label: "Pts", key: true, num: true },
  { id: "pnl", label: "P/L ₹", key: true, num: true },
  { id: "status", label: "Status", key: true },
  { id: "notes", label: "Notes", key: true, notes: true },
  { id: "sl", label: "SL", num: true },
  { id: "target", label: "Target", num: true },
  { id: "lotSize", label: "Lot size", num: true },
  { id: "lots", label: "Lots", num: true },
  { id: "investment", label: "Investment", num: true },
  { id: "ticket", label: "Ticket" },
  { id: "models", label: "Models" },
];
const DEFAULT_HIDDEN = COLUMNS.filter((c) => !c.key).map((c) => c.id);

function OutcomePill({ label }) {
  return <span className={`out-pill out-pill--${outcomeSlug(label)}`}>{label}</span>;
}

function fullClock(ist) {
  if (!ist) return "—";
  return String(ist).replace("T", " ").slice(0, 19);
}

function shortClock(ist, withDate) {
  if (!ist) return "—";
  const s = fullClock(ist);
  return withDate ? s.slice(5, 16) : s.slice(11, 19);
}

function modelsFor(t) {
  const names = [...(t.model_names || [])];
  if (!names.length) {
    for (const b of t.books || []) if (b && b !== "MIX-DEFAULT-BUY") names.push(b);
  }
  return names.length ? names.join(", ") : t.book_id || "—";
}

function noteFor(t) {
  return t.justification || t.exit_reason || t.status || "—";
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
    const parsed = raw ? JSON.parse(raw) : null;
    if (Array.isArray(parsed)) return parsed.filter((id) => COLUMNS.some((c) => c.id === id));
  } catch {
    /* ignore */
  }
  return DEFAULT_HIDDEN;
}

function RowDetail({ t, spotSrc }) {
  const items = [
    ["Opened", fullClock(t.opened_ist)],
    ["Closed", fullClock(t.closed_ist || t.last_updated_ist)],
    ["SL", px(t.stop)],
    ["Target", px(t.target)],
    ["Lots × size", `${t.lots ?? "—"} × ${t.lot_size ?? "—"}`],
    ["Investment", inr(t.notional_inr, { signed: false })],
    ["Charges", inr(t.charges_inr, { signed: false })],
    ["Spot source", spotSrc],
    ["Ticket", t.trade_id || "—"],
    ["Models", modelsFor(t)],
    ["Exit reason", t.exit_reason || t.status || "—"],
  ];
  return (
    <div className="trade-detail">
      <dl>
        {items.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <p className="trade-detail__note">{noteFor(t)}</p>
    </div>
  );
}

export function TradeHistory({ rows, fillRooms, onOpen, pageSize = 12 }) {
  const [index, setIndex] = useState("ALL");
  const [side, setSide] = useState("ALL");
  const [out, setOut] = useState("ALL");
  const [more, setMore] = useState(false);
  const [hidden, setHidden] = useState(() => loadHidden());
  const [colsOpen, setColsOpen] = useState(false);
  const [openId, setOpenId] = useState(null);

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
  const multiDay = useMemo(
    () => new Set((rows || []).map((t) => String(t.opened_ist || "").slice(0, 10))).size > 1,
    [rows],
  );

  const filtered = useMemo(() => {
    return (rows || []).filter((t) => {
      if (index !== "ALL" && t.underlying !== index) return false;
      if (side !== "ALL" && t.side !== side) return false;
      if (out !== "ALL" && outcomeLabel(t) !== out) return false;
      return true;
    });
  }, [rows, index, side, out]);

  const shown = more ? filtered : filtered.slice(0, pageSize);

  function toggle(t) {
    setOpenId((cur) => (cur === t.trade_id ? null : t.trade_id));
    if (fillRooms?.[t.trade_id] && onOpen) onOpen(t);
  }

  function cell(t, id) {
    const points = t.realized_pnl ?? (t.exit != null && t.entry != null ? Number(t.exit) - Number(t.entry) : null);
    switch (id) {
      case "start":
        return <span title={fullClock(t.opened_ist)}>{shortClock(t.opened_ist, multiDay)}</span>;
      case "end": {
        const end = t.closed_ist || (t.exit != null ? t.last_updated_ist : null);
        return <span title={fullClock(end)}>{end ? shortClock(end, multiDay) : "open"}</span>;
      }
      case "index":
        return t.underlying;
      case "side":
        return <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>;
      case "strike":
        return t.atm_strike ?? "—";
      case "spot":
        return px(t.spot_at_entry);
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
        return <OutcomePill label={outcomeLabel(t)} />;
      case "ticket":
        return t.trade_id || "—";
      case "models":
        return modelsFor(t);
      case "notes":
        return (
          <button
            type="button"
            className="note-btn"
            aria-expanded={openId === t.trade_id}
            title="Show full note and details"
            onClick={(e) => {
              e.stopPropagation();
              toggle(t);
            }}
          >
            {noteFor(t)}
          </button>
        );
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
          <button type="button" className="link-btn" onClick={() => setHidden(DEFAULT_HIDDEN)}>
            Reset columns
          </button>
        </div>
      ) : null}
      <p className="muted">
        {filtered.length} trades in this filter · {shown.length} shown · click a row for the full note
      </p>
      <div className="table-scroll table-scroll--history">
        <table className="book-table desk-history">
          <thead>
            <tr>
              {visible.map((c) => (
                <th key={c.id} className={`col-${c.id}${c.num ? " num" : ""}`} scope="col">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((t) => {
              const isOpen = openId === t.trade_id;
              return (
                <Fragment key={t.trade_id}>
                  <tr className={`is-click${isOpen ? " is-open" : ""}`} onClick={() => toggle(t)}>
                    {visible.map((c) => (
                      <td key={c.id} data-label={c.label} className={`col-${c.id}${c.num ? " num" : ""}`}>
                        {cell(t, c.id)}
                      </td>
                    ))}
                  </tr>
                  {isOpen ? (
                    <tr className="detail-row">
                      <td colSpan={visible.length}>
                        <RowDetail t={t} spotSrc={t.spot_at_entry == null ? "not recorded" : t.spot_at_entry_src || "trade record"} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
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

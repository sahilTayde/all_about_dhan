import { Fragment, useEffect, useMemo, useState } from "react";
import { fetchDay } from "../lib/feed.js";
import { inr, moneyClass, outcomeLabel, px, ticketState, uniqueFills } from "../lib/paperBoard.js";

const COLS_KEY = "desk.tradeHistory.columns.v3";
const STATE_WORD = { progress: "IN PROGRESS", stale: "STALE", target: "TARGET HIT", stopped: "STOPPED", dead: "DEAD" };

// `key` columns are on by default and sized to fit at 1280px; the rest are one click away in the
// column picker (the table then scrolls inside its own box) and always shown in the row detail.
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
  { id: "reason", label: "Reason", key: true },
  { id: "notes", label: "Notes", key: true, notes: true },
  { id: "gross", label: "Gross ₹", num: true },
  { id: "charges", label: "Charges ₹", num: true },
  { id: "slippage", label: "Slippage", num: true },
  { id: "sl", label: "SL", num: true },
  { id: "target", label: "Target", num: true },
  { id: "lots", label: "Lots", num: true },
  { id: "lotSize", label: "Lot size", num: true },
  { id: "investment", label: "Investment", num: true },
  { id: "book", label: "Book" },
  { id: "ticket", label: "Ticket" },
  { id: "models", label: "Models" },
  { id: "source", label: "Source" },
];
const DEFAULT_HIDDEN = COLUMNS.filter((c) => !c.key).map((c) => c.id);
const PAGE_SIZES = [12, 25, 50, 0];

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

function slippage(t) {
  const a = t.entry_slippage;
  const b = t.exit_slippage;
  if (a == null && b == null) return null;
  return `${a == null ? "—" : Number(a).toFixed(2)} / ${b == null ? "—" : Number(b).toFixed(2)}`;
}

function noteFor(t) {
  return t.justification || t.exit_reason || t.status || "—";
}

function reasonFor(t) {
  return t.exit_reason || t.cancel_reason || (t.exit == null ? "—" : t.status) || "—";
}

function Field({ label, value, onChange, options, render }) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {render ? render(opt) : opt === "ALL" ? `All ${label.toLowerCase()}` : opt}
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

function RowDetail({ t }) {
  const items = [
    ["Opened", fullClock(t.opened_ist)],
    ["Closed", fullClock(t.closed_ist || (t.exit != null ? t.last_updated_ist : null))],
    ["Gross ₹", inr(t.gross_pnl_inr)],
    ["Charges ₹", inr(t.charges_inr, { signed: false })],
    ["Net ₹", inr(t.realized_pnl_inr)],
    ["Slippage in / out", slippage(t) ?? "— (paper fills at LTP)"],
    ["SL", px(t.stop)],
    ["Target", px(t.target)],
    ["Lots × size", `${t.lots ?? "—"} × ${t.lot_size ?? "—"}`],
    ["Investment", inr(t.notional_inr, { signed: false })],
    ["Spot source", t.spot_at_entry == null ? "not recorded" : t.spot_at_entry_src || "trade record"],
    ["Exit / cancel reason", `${reasonFor(t)} · ${outcomeLabel(t)}`],
    ["Ticket", t.trade_id || "—"],
    ["Models", modelsFor(t)],
    ["Record source", t.source || "board"],
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

function DaySummary({ s }) {
  if (!s) return null;
  const wr = s.n ? Math.round((s.wins / s.n) * 1000) / 10 : null;
  return (
    <dl className="day-summary">
      <div>
        <dt>Trades</dt>
        <dd>{s.n}</dd>
      </div>
      <div>
        <dt>Win %</dt>
        <dd>{wr == null ? "—" : `${wr}%`}</dd>
      </div>
      <div>
        <dt>Gross</dt>
        <dd className={moneyClass(s.gross)}>{inr(s.gross)}</dd>
      </div>
      <div>
        <dt>Charges</dt>
        <dd className="is-down">{inr(-s.charges)}</dd>
      </div>
      <div>
        <dt>Net</dt>
        <dd className={moneyClass(s.net)}>{inr(s.net)}</dd>
      </div>
    </dl>
  );
}

export function TradeHistory({ rows, days, liveDay, clock, fillRooms, onOpen, onSelect, selectedId }) {
  const [index, setIndex] = useState("ALL");
  const [side, setSide] = useState("ALL");
  const [state, setState] = useState("ALL");
  const [reason, setReason] = useState("ALL");
  const [query, setQuery] = useState("");
  const [pageSize, setPageSize] = useState(12);
  const [hidden, setHidden] = useState(() => loadHidden());
  const [colsOpen, setColsOpen] = useState(false);
  const [openId, setOpenId] = useState(null);
  const [day, setDay] = useState("LIVE");
  const [dayRows, setDayRows] = useState(null);
  const [dayErr, setDayErr] = useState(null);

  useEffect(() => {
    try {
      localStorage.setItem(COLS_KEY, JSON.stringify(hidden));
    } catch {
      /* ignore */
    }
  }, [hidden]);

  useEffect(() => {
    if (day === "LIVE") return undefined;
    const ac = new AbortController();
    setDayRows(null);
    setDayErr(null);
    fetchDay(day, { signal: ac.signal })
      .then((j) => setDayRows(uniqueFills(j.trades || [])))
      .catch((e) => e?.name !== "AbortError" && setDayErr("Past days need the API (read-only /paper/history)."));
    return () => ac.abort();
  }, [day]);

  const source = day === "LIVE" ? rows || [] : dayRows || [];
  const visible = useMemo(() => COLUMNS.filter((c) => !hidden.includes(c.id)), [hidden]);
  const stateOf = (t) => ticketState(t, { clock }).key;
  const opts = (fn) => ["ALL", ...[...new Set(source.map(fn).filter(Boolean))].sort()];
  const multiDay = useMemo(() => new Set(source.map((t) => String(t.opened_ist || "").slice(0, 10))).size > 1, [source]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return source.filter((t) => {
      if (index !== "ALL" && t.underlying !== index) return false;
      if (side !== "ALL" && t.side !== side) return false;
      if (state !== "ALL" && stateOf(t) !== state) return false;
      if (reason !== "ALL" && reasonFor(t) !== reason) return false;
      if (q && !`${noteFor(t)} ${t.trade_id} ${t.atm_strike}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [source, index, side, state, reason, query, clock]);

  const shown = pageSize ? filtered.slice(0, pageSize) : filtered;
  const pastDays = (days || []).map((d) => d.day).filter((d) => d !== liveDay);
  const summary = (days || []).find((d) => d.day === (day === "LIVE" ? liveDay : day));

  function toggle(t) {
    setOpenId((cur) => (cur === t.trade_id ? null : t.trade_id));
    if (onSelect) onSelect(t);
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
      case "entry":
        return px(t.entry ?? t.limit_price);
      case "exitPx":
        return px(t.exit);
      case "points":
        return <span className={moneyClass(points)}>{points == null ? "—" : Number(points).toFixed(2)}</span>;
      case "pnl":
        return <span className={moneyClass(t.realized_pnl_inr)}>{inr(t.realized_pnl_inr)}</span>;
      case "gross":
        return <span className={moneyClass(t.gross_pnl_inr)}>{inr(t.gross_pnl_inr)}</span>;
      case "charges":
        return inr(t.charges_inr, { signed: false });
      case "slippage":
        return slippage(t) ?? "—";
      case "status": {
        const s = ticketState(t, { clock });
        return <span className={`state-pill state-pill--${s.key}`} title={s.label}>{STATE_WORD[s.key] || s.label}</span>;
      }
      case "reason":
        return <span title={outcomeLabel(t)}>{reasonFor(t)}</span>;
      case "sl":
        return px(t.stop);
      case "target":
        return px(t.target);
      case "lotSize":
        return t.lot_size ?? "—";
      case "lots":
        return t.lots ?? "—";
      case "investment":
        return inr(t.notional_inr, { signed: false });
      case "book":
        return t.book_id || "—";
      case "ticket":
        return t.trade_id || "—";
      case "models":
        return modelsFor(t);
      case "source":
        return t.source || "board";
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
      <div className="filter-row" role="group" aria-label="Filter trades">
        <Field
          label="Day"
          value={day}
          onChange={setDay}
          options={["LIVE", ...pastDays]}
          render={(d) => (d === "LIVE" ? `${liveDay || "Today"} · live board` : d)}
        />
        <Field label="Index" value={index} onChange={setIndex} options={opts((t) => t.underlying)} />
        <Field label="Side" value={side} onChange={setSide} options={opts((t) => t.side)} />
        <Field
          label="Status"
          value={state}
          onChange={setState}
          options={opts(stateOf)}
          render={(o) => (o === "ALL" ? "All status" : STATE_WORD[o] || o)}
        />
        <Field label="Reason" value={reason} onChange={setReason} options={opts(reasonFor)} />
        <label className="filter-field filter-field--grow">
          <span>Search</span>
          <input type="search" value={query} placeholder="note, ticket, strike" onChange={(e) => setQuery(e.target.value)} />
        </label>
        <button type="button" className="refresh-btn" onClick={() => setColsOpen((v) => !v)} aria-expanded={colsOpen}>
          Columns
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
      <DaySummary s={summary} />
      <p className="muted small table-meta">
        {dayErr || (day !== "LIVE" && !dayRows ? "Loading day…" : `${filtered.length} trades · ${shown.length} shown · click a row for the trace and full note`)}
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
                  <tr
                    className={`is-click${isOpen ? " is-open" : ""}${selectedId === t.trade_id ? " is-selected" : ""}`}
                    onClick={() => toggle(t)}
                  >
                    {visible.map((c) => (
                      <td key={c.id} data-label={c.label} className={`col-${c.id}${c.num ? " num" : ""}`}>
                        {cell(t, c.id)}
                      </td>
                    ))}
                  </tr>
                  {isOpen ? (
                    <tr className="detail-row">
                      <td colSpan={visible.length}>
                        <RowDetail t={t} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="table-foot">
        <label className="filter-field filter-field--inline">
          <span>Rows</span>
          <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n || "All"}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}

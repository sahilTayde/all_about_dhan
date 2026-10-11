import { useEffect, useState } from "react";
import { fmtElapsed, inr, moneyClass, pathInfo, plainWhy, px, strikeOf, ticketState, tickEdge, tradeNow } from "../lib/paperBoard.js";
import { strategyName } from "../lib/tradePipeline.js";

function clamp01(n) {
  if (n == null || Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function Tick({ pct, label, value }) {
  if (pct == null || value == null || Number.isNaN(Number(value))) return null;
  const edge = tickEdge(pct);
  return (
    <span className={`fx-path__tick fx-path__tick--${edge}`} style={{ left: `${clamp01(pct) * 100}%` }}>
      {label} {px(value)}
    </span>
  );
}

function TicketPath({ t }) {
  const p = pathInfo(t);
  const mark = p.markLabel || "now";
  const exitOnStop =
    p.closed && p.stop != null && p.last != null && Math.abs(p.last - p.stop) < 1e-9;
  if (p.entry == null && p.last == null && p.stop == null && p.target == null) return null;
  return (
    <div className="fx-path">
      <div className="fx-range" aria-hidden="true">
        <i className="fx-range__fill" />
        {p.entryPct != null ? (
          <b className="fx-range__entry" style={{ left: `${clamp01(p.entryPct) * 100}%` }} title="Entry" />
        ) : null}
        {p.pct != null ? (
          <em
            className={p.closed ? "fx-range__exit" : "fx-range__now"}
            style={{ left: `${clamp01(p.pct) * 100}%` }}
            title={p.closed ? "Exit" : "Now"}
          />
        ) : null}
      </div>
      <div className="fx-path__ticks">
        {exitOnStop ? (
          <Tick pct={p.stopPct} label="stop / exit" value={p.stop} />
        ) : p.stop != null ? (
          <Tick pct={p.stopPct} label={p.trailing ? "Trail SL" : "Stop"} value={p.stop} />
        ) : null}
        <Tick pct={p.entryPct} label="entry" value={p.entry} />
        {exitOnStop ? null : <Tick pct={p.pct} label={mark} value={p.last} />}
        <Tick pct={p.targetPct} label="target" value={p.target} />
      </div>
    </div>
  );
}

export function HumanManage({ current, busy, onCancel, onSetLevels }) {
  const p = pathInfo(current);
  const [target, setTarget] = useState(Number.isFinite(p.target) ? String(p.target) : "");
  const [stop, setStop] = useState(Number.isFinite(p.stop) ? String(p.stop) : "");
  const [confirm, setConfirm] = useState(false);
  useEffect(() => {
    const next = pathInfo(current);
    setTarget(Number.isFinite(next.target) ? String(next.target) : "");
    setStop(Number.isFinite(next.stop) ? String(next.stop) : "");
    setConfirm(false);
  }, [current.trade_id]);
  const filled = current.filled !== false;
  const tgtN = Number(target);
  const stopN = Number(stop);
  const entry = Number(current.entry ?? current.limit_price);
  const orderOk = Number.isFinite(tgtN) && Number.isFinite(stopN) && tgtN > entry && entry > stopN;
  const canApply = filled && confirm && orderOk && !busy;

  if (!filled) {
    return (
      <div className="human-control">
        <button type="button" className="refresh-btn" onClick={onCancel} disabled={busy}>
          Human priority: Cancel working ticket
        </button>
        <span>Unfilled paper limit only. No live broker order.</span>
      </div>
    );
  }

  return (
    <form
      className="human-control human-control--manage"
      onSubmit={(e) => {
        e.preventDefault();
        if (!canApply) return;
        onSetLevels({ target: tgtN, stop: stopN });
      }}
    >
      <p className="human-control__lead">
        Human override — set paper TARGET and STOP. Immediate exit is refused (suicide on an open fill). No live
        broker order.
      </p>
      <div className="human-fields">
        <label>
          Paper target (required)
          <input type="number" step="0.05" min="0" required value={target} onChange={(e) => setTarget(e.target.value)} />
        </label>
        <label>
          Paper stop (required)
          <input type="number" step="0.05" min="0" required value={stop} onChange={(e) => setStop(e.target.value)} />
        </label>
      </div>
      <p className="desk-sub">
        Long premium order: target {Number.isFinite(tgtN) ? tgtN.toFixed(2) : "—"} &gt; entry{" "}
        {Number.isFinite(entry) ? entry.toFixed(2) : "—"} &gt; stop {Number.isFinite(stopN) ? stopN.toFixed(2) : "—"}.
        {orderOk ? "" : " Fix the order before confirm."}
      </p>
      <label className="human-confirm">
        <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
        I confirm these paper levels. Do not flatten this ticket.
      </label>
      <button type="submit" className="refresh-btn" disabled={!canApply}>
        {busy ? "Sending…" : "Apply paper target & stop"}
      </button>
    </form>
  );
}

function Cell({ label, value, tone, title }) {
  if (value == null || value === "" || value === "—") return null;
  return (
    <div className="kv" title={title}>
      <dt>{label}</dt>
      <dd className={tone || ""}>{value}</dd>
    </div>
  );
}

function ExplainLine({ t }) {
  if (!t?.llm_explanation && !t?.market_type) return null;
  return (
    <p className="desk-sub current-trade__explain" data-testid="trade-explain">
      {t.market_type ? <strong>{t.market_type}. </strong> : null}
      {t.llm_explanation || ""}
    </p>
  );
}

function LastTicket({ t, clock }) {
  const s = ticketState(t, { clock });
  return (
    <>
      <dl className="kv-grid kv-grid--3 last-ticket">
        <Cell label="Last ticket" value={`${t.underlying} ${t.side} ${strikeOf(t) ?? ""}`.trim()} />
        <Cell label="State" value={<span className={`state-pill state-pill--${s.key}`}>{s.label}</span>} />
        <Cell label="Reason" value={ticketState(t, { clock }).label} />
        <Cell label="Entry → exit" value={`${px(t.entry)} → ${px(t.exit)}`} />
        <Cell label="Net ₹" value={inr(t.realized_pnl_inr)} tone={moneyClass(t.realized_pnl_inr)} />
        <Cell label="Closed" value={String(t.closed_ist || "").slice(11, 19) || "—"} />
      </dl>
      <ExplainLine t={t} />
    </>
  );
}

const pts = (n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(2)}`);

/** Current Trade (§49): every field from the ticket record; missing ones read "—". */
export function CurrentTrade({ t, last, clock, hold, indexNow, children, title = "Current trade" }) {
  const [tick, setTick] = useState(0);
  const live = t && !clock?.replay;
  useEffect(() => {
    if (!live) return undefined;
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [live]);
  void tick;

  const state = t ? ticketState(t, { clock }) : hold ? { key: "hold", label: "ON HOLD" } : ticketState(null);
  const nowMs = clock?.replay && clock.ms != null ? clock.ms : Date.now();
  const n = t ? tradeNow(t, { nowMs }) : null;
  return (
    <section className="panel current-trade">
      <div className="panel__head">
        <h2>{title}</h2>
        <span className={`state-pill state-pill--${state.key}`}>{state.label}</span>
      </div>
      {!t ? (
        <div className="current-trade__empty">
          <p className="current-trade__big">{hold ? "On hold" : "Waiting for next signal"}</p>
          <p className="muted">{hold ? `Why: ${hold}` : "No open paper ticket. The next call or put lands here the moment the board writes it."}</p>
          {last ? <LastTicket t={last} clock={clock} /> : null}
        </div>
      ) : (
        <>
          <div className="current-trade__title">
            <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>BUY {t.side}</span>
            <strong>
              {t.underlying} {strikeOf(t) ?? ""}
            </strong>
            {strategyName(t) ? <span className="muted">{strategyName(t)}</span> : null}
          </div>
          <dl className="kv-grid">
            <Cell label="Signal" value={t.side ? `BUY ${t.side}` : null} />
            <Cell label="Strike" value={strikeOf(t)} />
            <Cell label="Entry" value={n.entry != null ? px(n.entry) : null} />
            <Cell label={n.closed ? "Exit" : "LTP"} value={n.ltp != null ? px(n.ltp) : null} tone={moneyClass(n.pts)} />
            <Cell label="Stop" value={n.stop != null ? px(n.stop) : null} />
            <Cell label="T1" value={n.t1 === "hit" ? "hit" : n.t1 != null ? px(n.t1) : null} />
            <Cell label="T2" value={n.t2 != null ? px(n.t2) : null} />
            <Cell label="Trailing SL" value={n.trailing != null ? px(n.trailing) : null} />
            <Cell label="P&L pts" value={n.pts != null ? pts(n.pts) : null} tone={moneyClass(n.pts)} />
            <Cell
              label={n.closed ? "P&L ₹ after charges" : "P&L ₹ gross"}
              value={inr(n.closed ? n.netInr ?? n.inr : n.inr)}
              tone={moneyClass(n.closed ? n.netInr ?? n.inr : n.inr)}
              title={n.closed ? "Net after Dhan/NSE charges" : "(LTP − entry) × qty, before charges"}
            />
            <Cell label="Elapsed" value={n.elapsedMs != null ? fmtElapsed(n.elapsedMs) : null} title={clock?.replay ? "Against the session clock (replay)" : "Since entry"} />
            <Cell label="MFE" value={n.mfe != null ? pts(n.mfe) : null} tone={moneyClass(n.mfe)} title="Best premium seen since entry − entry" />
            <Cell label="MAE" value={n.mae != null ? pts(n.mae) : null} tone={moneyClass(n.mae)} title="Worst premium seen since entry − entry" />
            <Cell label="Spot @ entry" value={t.spot_at_entry != null ? px(t.spot_at_entry) : null} />
            <Cell label="Index now" value={indexNow != null ? px(indexNow) : null} />
            <Cell label="Qty" value={n.qty} />
          </dl>
          <TicketPath t={t} />
          {plainWhy(t) ? <p className="desk-sub current-trade__why">Why: {plainWhy(t)}</p> : null}
          <ExplainLine t={t} />
          {children}
        </>
      )}
    </section>
  );
}

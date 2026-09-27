import { useEffect, useState } from "react";
import { fmtElapsed, inr, moneyClass, pathInfo, px, shortWhy, ticketState, tradeNow } from "../lib/paperBoard.js";

function clamp01(n) {
  if (n == null || Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function TicketPath({ t }) {
  const p = pathInfo(t);
  return (
    <div className="fx-path">
      <div className="fx-range" aria-hidden="true">
        <i className="fx-range__fill" />
        <b className="fx-range__entry" style={{ left: `${clamp01(p.entryPct) * 100}%` }} title="Entry" />
        <em className="fx-range__now" style={{ left: `${clamp01(p.pct) * 100}%` }} title="Now" />
      </div>
      <div className="fx-path__ticks">
        <span>
          {p.trailing ? "Trail SL" : "Stop"} {px(p.stop)}
        </span>
        <span>entry {px(p.entry)}</span>
        <span>now {px(p.last)}</span>
        <span>target {px(p.target)}</span>
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
  return (
    <div className="kv" title={title}>
      <dt>{label}</dt>
      <dd className={tone || ""}>{value}</dd>
    </div>
  );
}

function LastTicket({ t, clock }) {
  const s = ticketState(t, { clock });
  return (
    <dl className="kv-grid kv-grid--3 last-ticket">
      <Cell label="Last ticket" value={`${t.underlying} ${t.side} ${t.atm_strike ?? ""}`} />
      <Cell label="State" value={<span className={`state-pill state-pill--${s.key}`}>{s.label}</span>} />
      <Cell label="Reason" value={t.exit_reason || t.status || "—"} />
      <Cell label="Entry → exit" value={`${px(t.entry)} → ${px(t.exit)}`} />
      <Cell label="Net ₹" value={inr(t.realized_pnl_inr)} tone={moneyClass(t.realized_pnl_inr)} />
      <Cell label="Closed" value={String(t.closed_ist || "").slice(11, 19) || "—"} />
    </dl>
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
          <p className="muted">{hold ? `Why: ${hold}` : "No open MIX-DEFAULT-BUY ticket. The next CE/PE lands here the moment the board writes it."}</p>
          {last ? <LastTicket t={last} clock={clock} /> : null}
        </div>
      ) : (
        <>
          <div className="current-trade__title">
            <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>BUY {t.side}</span>
            <strong>
              {t.underlying} {t.atm_strike ?? "—"}
            </strong>
            <span className="muted">{(t.books || [t.book_id]).filter(Boolean).join(" · ")}</span>
          </div>
          <dl className="kv-grid">
            <Cell label="Signal" value={`BUY ${t.side}`} title={t.book_id || undefined} />
            <Cell label="Strike" value={t.atm_strike ?? "—"} />
            <Cell label="Entry" value={px(n.entry)} />
            <Cell label="LTP" value={px(n.ltp)} tone={moneyClass(n.pts)} />
            <Cell label="Stop" value={px(n.stop)} />
            <Cell label="T1" value={n.t1 === "hit" ? "hit" : px(n.t1)} />
            <Cell label="T2" value={px(n.t2)} />
            <Cell label="Trailing SL" value={px(n.trailing)} />
            <Cell label="P&L pts" value={pts(n.pts)} tone={moneyClass(n.pts)} />
            <Cell label="P&L ₹ gross" value={inr(n.inr)} tone={moneyClass(n.inr)} title="(LTP − entry) × qty, before charges" />
            <Cell label="Elapsed" value={fmtElapsed(n.elapsedMs)} title={clock?.replay ? "Against the tape clock (replay)" : "Since entry"} />
            <Cell label="MFE" value={pts(n.mfe)} tone={moneyClass(n.mfe)} title="Best premium seen since entry − entry" />
            <Cell label="MAE" value={pts(n.mae)} tone={moneyClass(n.mae)} title="Worst premium seen since entry − entry" />
            <Cell label="Spot @ entry" value={px(t.spot_at_entry)} />
            <Cell label="Index now" value={px(indexNow)} />
            <Cell label="Qty" value={n.qty ?? "—"} />
          </dl>
          <TicketPath t={t} />
          <p className="desk-sub current-trade__why">Why: {shortWhy(t.justification)}</p>
          {children}
        </>
      )}
    </section>
  );
}

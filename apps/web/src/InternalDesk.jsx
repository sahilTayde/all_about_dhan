import { useEffect, useMemo, useState } from "react";
import { AppNav } from "./components/AppNav.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { Header } from "./components/Header.jsx";
import { IstMarketClock } from "./components/IstMarketClock.jsx";
import { SodFillGraph, WatcherStrip } from "./components/SodFillGraph.jsx";
import { TradeHistory } from "./components/TradeHistory.jsx";
import {
  derivePaperBoard,
  deskLifeStatus,
  discardOutcome,
  discardTradeLabel,
  discardedWho,
  fetchFounderLab,
  fetchMlPaperBoard,
  moneyClass,
  pathInfo,
  postHumanOverride,
  px,
  shortWhy,
  skipPlain,
} from "./lib/paperBoard.js";

function StatusPill({ status }) {
  return <span className={`life-pill life-pill--${String(status || "dead").toLowerCase()}`}>{status}</span>;
}

function clamp01(n) {
  if (n == null || Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function TicketPath({ t }) {
  const p = pathInfo(t);
  const nowPct = clamp01(p.pct) * 100;
  const entryPct = clamp01(p.entryPct) * 100;
  const remainW = clamp01(p.remainingPctOfRange) * 100;
  const riskW = clamp01(p.riskPctOfRange) * 100;
  return (
    <div className="fx-path">
      <p className="fx-path__legend">
        Position on the paper range: stop → entry → target. Marker is last premium. Not a win rate.
      </p>
      <div className="fx-range" aria-hidden="true">
        <i className="fx-range__fill" />
        <b className="fx-range__entry" style={{ left: `${entryPct}%` }} title="Entry" />
        <em className="fx-range__now" style={{ left: `${nowPct}%` }} title="Now" />
      </div>
      <div className="fx-path__ticks">
        <span>
          {p.trailing ? "Trail SL" : "Stop"} {px(p.stop)}
        </span>
        <span>entry {px(p.entry)}</span>
        <span>now {px(p.last)}</span>
        <span>target {px(p.target)}</span>
      </div>
      <div className="path-meters">
        <div className="path-meter path-meter--target">
          <span>Remaining path to target</span>
          <strong>
            {p.remainingToTarget == null ? "—" : `${p.remainingToTarget.toFixed(1)} pts left`}
          </strong>
          <div className="path-meter__bar" aria-hidden="true">
            <i style={{ width: `${remainW}%` }} />
          </div>
          <small>How far the last print still is from target. Independent of stop.</small>
        </div>
        <div className="path-meter path-meter--stop">
          <span>Risk distance to stop</span>
          <strong>{p.riskToStop == null ? "—" : `${p.riskToStop.toFixed(1)} pts of room`}</strong>
          <div className="path-meter__bar" aria-hidden="true">
            <i style={{ width: `${riskW}%` }} />
          </div>
          <small>How far the last print still is from stop. Independent of target.</small>
        </div>
      </div>
    </div>
  );
}

function HumanManage({ current, busy, onCancel, onSetLevels }) {
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
          <input
            type="number"
            step="0.05"
            min="0"
            required
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
        </label>
        <label>
          Paper stop (required)
          <input
            type="number"
            step="0.05"
            min="0"
            required
            value={stop}
            onChange={(e) => setStop(e.target.value)}
          />
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

export function InternalDesk() {
  const [board, setBoard] = useState(null);
  const [lab, setLab] = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [roomId, setRoomId] = useState(null);
  const [humanMsg, setHumanMsg] = useState("");

  async function load(force = true, signal) {
    setBusy(true);
    try {
      const [json, overlay] = await Promise.all([
        fetchMlPaperBoard({ force, signal }),
        fetchFounderLab({ signal }),
      ]);
      setBoard(json);
      setLab(overlay);
      setError(null);
      setTick((n) => n + 1);
    } catch (err) {
      if (err?.name !== "AbortError") setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const ac = new AbortController();
    load(true, ac.signal);
    const id = setInterval(() => load(false, ac.signal), 12000);
    return () => {
      ac.abort();
      clearInterval(id);
    };
  }, []);

  const d = useMemo(() => derivePaperBoard(board, lab), [board, lab]);
  const current = d?.current;
  const life = deskLifeStatus(current);
  const path = current ? pathInfo(current) : null;
  const spot =
    current && d?.regimes?.[current.underlying]
      ? current.spot_at_entry ??
        d.regimes[current.underlying].itm_bin?.index ??
        d.regimes[current.underlying].vwap
      : null;
  const room = roomId && d?.fillRooms?.[roomId] ? d.fillRooms[roomId] : d?.currentRoom;

  async function humanCancelWorking() {
    if (!current) return;
    setHumanMsg("");
    setBusy(true);
    try {
      const res = await postHumanOverride({
        action: "CANCEL",
        trade_id: current.trade_id,
        underlying: current.underlying,
        side: current.side,
      });
      if (res?.ok === false) {
        setHumanMsg(res.note || res.error || "Cancel refused");
      } else {
        setHumanMsg("Human cancel sent for the unfilled paper limit. No live broker order.");
      }
      await load(true);
    } catch (err) {
      setHumanMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  async function humanSetLevels({ target, stop }) {
    if (!current) return;
    setHumanMsg("");
    setBusy(true);
    try {
      const res = await postHumanOverride({
        action: "SET_LEVELS",
        trade_id: current.trade_id,
        underlying: current.underlying,
        side: current.side,
        target,
        stop,
      });
      if (res?.ok === false) {
        setHumanMsg(res.note || res.error || "Levels refused");
      } else {
        setHumanMsg(
          `Paper target ${Number(target).toFixed(2)} / stop ${Number(stop).toFixed(2)} queued. Applies on next paper tick. No flatten. No live broker order.`,
        );
      }
      await load(true);
    } catch (err) {
      setHumanMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell shell--internal">
      <AppNav current="/desk" />
      <Header
        title="Desk"
        kicker="Revalidate the ticket"
        sub="Live path, watchers, compare history to the signal that filled it."
        sourceLabel={board?.live_session ? "PAPER" : "MOCK"}
      />

      <div className="desk-refresh">
        <p className="desk-sub">
          {board?.as_of_ist ? board.as_of_ist.replace("T", " ").slice(0, 19) : "—"} · 12s light poll · #{tick}
        </p>
        <IstMarketClock />
        <button type="button" className="refresh-btn" onClick={() => load(true)} disabled={busy}>
          {busy ? "Refreshing…" : "Refresh now"}
        </button>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}
      {!d ? (
        <p className="muted">Loading desk…</p>
      ) : (
        <>
          <section className="panel current-signal">
            <div className="panel__head">
              <div>
                <h2>Current trade signal</h2>
                <p className="fx-kicker">PAPER · not a broker fill</p>
              </div>
              <StatusPill status={current ? life : "DEAD"} />
            </div>
            {!current ? (
              <p className="muted">No open ticket. Waiting for MIX-DEFAULT-BUY.</p>
            ) : (
              <>
                <div className="current-signal__hero">
                  <div>
                    <span className={`side-mini side-mini--${String(current.side).toLowerCase()}`}>{current.side}</span>
                    <h3 className="current-signal__name">
                      {current.underlying} {current.atm_strike}
                    </h3>
                    <p className="desk-sub">{(current.books || [current.book_id]).join(" · ")}</p>
                  </div>
                  <dl className="level-strip">
                    <div>
                      <dt>Spot</dt>
                      <dd>{px(spot)}</dd>
                    </div>
                    <div>
                      <dt>Entry</dt>
                      <dd>{px(path.entry)}</dd>
                    </div>
                    <div>
                      <dt>Now</dt>
                      <dd>{px(path.last)}</dd>
                    </div>
                    <div>
                      <dt>{path.trailing ? "Trail SL" : "Stop"}</dt>
                      <dd>{px(path.stop)}</dd>
                    </div>
                    <div>
                      <dt>Target</dt>
                      <dd>{px(path.target)}</dd>
                    </div>
                    <div>
                      <dt>Open P/L</dt>
                      <dd className={moneyClass(path.vsEntry)}>
                        {path.vsEntry == null ? "—" : `${path.vsEntry.toFixed(1)} pts`}
                      </dd>
                    </div>
                  </dl>
                </div>
                <TicketPath t={current} />
                <HumanManage
                  current={current}
                  busy={busy}
                  onCancel={humanCancelWorking}
                  onSetLevels={humanSetLevels}
                />
                {humanMsg ? <p className="muted">{humanMsg}</p> : null}
              </>
            )}
          </section>

          <section className="panel">
            <h2>Who is watching · how it filled</h2>
            <SodFillGraph room={room} />
            <WatcherStrip watchers={room?.watchers} />
            {current ? (
              <p className="desk-sub">
                Why: {shortWhy(current.justification)} · {current.index_regime || "—"} / {current.regime_reason || "—"}
              </p>
            ) : null}
          </section>

          <section className="panel">
            <h2>Trade history</h2>
            <TradeHistory
              rows={d.uniqueClosed}
              regimes={d.regimes}
              fillRooms={d.fillRooms}
              onOpen={(t) => setRoomId(t.trade_id)}
            />
          </section>

          <section className="panel">
            <h2>Discarded by boss or dealer</h2>
            <p className="muted">
              Index START/STOP is the founder desk on /pm. Tape still records all three. Each row is one ticket or
              spoken signal — not a grouped slogan.
            </p>
            {d.actorCounts?.length ? (
              <p className="discard-actors">
                Who acted:{" "}
                {d.actorCounts.map((a) => (
                  <span key={a.who} className="discard-who">
                    {a.who} ×{a.n}
                  </span>
                ))}
              </p>
            ) : null}
            {d.discardedRows.length === 0 ? (
              <p className="muted">Nothing discarded on this snapshot.</p>
            ) : (
              <ul className="discard-list">
                {d.discardedRows.slice(0, 24).map((g, i) => (
                  <li key={g.trade_id || `${g.reason}-${g.underlying}-${g.side || g.seen_side}-${g.ts || i}`}>
                    <div>
                      <strong>{discardTradeLabel(g)}</strong>
                      <span className="discard-who">{discardedWho(g)}</span>
                      <span className="fx-skips__n">{discardOutcome(g)}</span>
                    </div>
                    <p>
                      {g.book_id || g.source || "—"} · fill {g.filled === true ? "yes" : "no"} · lots {g.lots ?? "—"} ·
                      qty {g.qty ?? "—"} · ticket {g.trade_id || "none (no fill)"}
                    </p>
                    <p>
                      {skipPlain(g.reason || g.vs_picker)}
                      {g.why || g.detail || g.observation
                        ? ` — ${String(g.why || g.detail || g.observation).slice(0, 180)}`
                        : ""}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
      <Disclaimer />
    </div>
  );
}

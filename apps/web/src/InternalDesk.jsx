import { useEffect, useMemo, useState } from "react";
import { AppNav } from "./components/AppNav.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { Header } from "./components/Header.jsx";
import { IstMarketClock } from "./components/IstMarketClock.jsx";
import { SodFillGraph, WatcherStrip } from "./components/SodFillGraph.jsx";
import { SpillLedger } from "./components/SpillLedger.jsx";
import { TradeHistory } from "./components/TradeHistory.jsx";
import {
  derivePaperBoard,
  deskLifeStatus,
  fetchFounderLab,
  fetchMlPaperBoard,
  fetchSodExam,
  BOARD_POLL_MS,
  moneyClass,
  pathInfo,
  postHumanOverride,
  px,
  shortWhy,
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
    <div className="fx-path fx-path--compact">
      <div className="fx-range" aria-hidden="true">
        <i className="fx-range__fill" />
        <b className="fx-range__entry" style={{ left: `${entryPct}%` }} title="Entry" />
        <em className="fx-range__now" style={{ left: `${nowPct}%` }} title="Now" />
      </div>
      <div className="path-meters path-meters--inline">
        <div className="path-meter path-meter--target">
          <span>To target</span>
          <strong>{p.toTarget == null ? "—" : `${p.toTarget.toFixed(1)} pts`}</strong>
          <div className="path-meter__bar" aria-hidden="true">
            <i style={{ width: `${remainW}%` }} />
          </div>
        </div>
        <div className="path-meter path-meter--stop">
          <span>SL room</span>
          <strong>{p.slRoom == null ? "—" : `${p.slRoom.toFixed(1)} pts`}</strong>
          <div className="path-meter__bar" aria-hidden="true">
            <i style={{ width: `${riskW}%` }} />
          </div>
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
  const last = Number(current.last_ltp ?? current.entry ?? current.limit_price);
  const orderOk = Number.isFinite(tgtN) && Number.isFinite(stopN) && tgtN > stopN;
  const canApply = filled && confirm && orderOk && !busy;
  const throughTarget = orderOk && Number.isFinite(last) && last >= tgtN;

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
      <div className="human-fields">
        <label>
          Target
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
          Stop
          <input
            type="number"
            step="0.05"
            min="0"
            required
            value={stop}
            onChange={(e) => setStop(e.target.value)}
          />
        </label>
        <label className="human-confirm">
          <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
          Lock these
        </label>
        <button type="submit" className="refresh-btn" disabled={!canApply}>
          {busy ? "Sending…" : "Apply"}
        </button>
      </div>
      <p className="desk-sub">
        Keep or change. Target must be above stop. These replace the system levels. No unwind flatten.
        {throughTarget ? " Last is already through target — next tick books TARGET." : ""}
        {orderOk ? "" : " Target must be above stop."}
      </p>
    </form>
  );
}

export function InternalDesk() {
  const [board, setBoard] = useState(null);
  const [lab, setLab] = useState(null);
  const [exam, setExam] = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [roomId, setRoomId] = useState(null);
  const [humanMsg, setHumanMsg] = useState("");

  async function load(force = true, signal) {
    setBusy(true);
    try {
      const [json, overlay, examJson] = await Promise.all([
        fetchMlPaperBoard({ force, signal }),
        fetchFounderLab({ signal }),
        fetchSodExam({ signal }),
      ]);
      setBoard(json);
      setLab(overlay);
      setExam(examJson);
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
    const id = setInterval(() => load(false, ac.signal), BOARD_POLL_MS);
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
          `Locked paper target ${Number(target).toFixed(2)} / stop ${Number(stop).toFixed(2)}. System levels replaced. Stays until this ticket hits those or 15:16. No live broker order.`,
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
          {board?.as_of_ist ? board.as_of_ist.replace("T", " ").slice(0, 19) : "—"} · 2s light poll · #{tick}
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
                  <div className="current-signal__title">
                    <span className={`side-mini side-mini--${String(current.side).toLowerCase()}`}>{current.side}</span>
                    <h3 className="current-signal__name">
                      {current.underlying} {current.atm_strike}
                    </h3>
                    {current.human_managed ? <span className="human-lock-pill">HUMAN LOCK</span> : null}
                  </div>
                  <dl className="level-strip level-strip--compact">
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
                      <dt>Stop</dt>
                      <dd>{px(path.stop)}</dd>
                    </div>
                    <div>
                      <dt>Target</dt>
                      <dd>{px(path.target)}</dd>
                    </div>
                    <div>
                      <dt>P/L</dt>
                      <dd className={moneyClass(path.vsEntry)}>
                        {path.vsEntry == null ? "—" : `${path.vsEntry.toFixed(1)}`}
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

          <SpillLedger exam={exam} />
        </>
      )}
      <Disclaimer />
    </div>
  );
}

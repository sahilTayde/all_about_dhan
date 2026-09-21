import { useEffect, useMemo, useState } from "react";
import { AppNav } from "./components/AppNav.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { Header } from "./components/Header.jsx";
import { SodFillGraph, WatcherStrip } from "./components/SodFillGraph.jsx";
import { TradeHistory } from "./components/TradeHistory.jsx";
import {
  derivePaperBoard,
  deskLifeStatus,
  fetchFounderLab,
  fetchMlPaperBoard,
  moneyClass,
  pathInfo,
  pct,
  px,
  shortWhy,
  skipPlain,
} from "./lib/paperBoard.js";

function StatusPill({ status }) {
  return <span className={`life-pill life-pill--${String(status || "dead").toLowerCase()}`}>{status}</span>;
}

function TicketPath({ t }) {
  const p = pathInfo(t);
  const width = p.pct == null ? 0 : Math.max(4, Math.min(96, p.pct * 100));
  return (
    <div className="fx-path">
      <div className="fx-path__bar" aria-hidden="true">
        <i style={{ width: `${width}%` }} />
      </div>
      <div className="fx-path__ticks">
        <span>
          {p.trailing ? "Trail SL" : "SL"} {px(p.stop)}
        </span>
        <span>now {px(p.last)}</span>
        <span>tgt {px(p.target)}</span>
      </div>
    </div>
  );
}

export function InternalDesk() {
  const [board, setBoard] = useState(null);
  const [lab, setLab] = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [roomId, setRoomId] = useState(null);

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
                <div className="path-confidence">
                  <div>
                    <span>Path to target</span>
                    <strong>{path.hitTargetPct == null ? "—" : pct(path.hitTargetPct)}</strong>
                  </div>
                  <div>
                    <span>Path to stop</span>
                    <strong>{path.hitStopPct == null ? "—" : pct(path.hitStopPct)}</strong>
                  </div>
                  <p>Distance score only. Not a win rate.</p>
                </div>
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
              Index book is the founder pick on /pm. BANKNIFTY / SENSEX off that book are not discards.
            </p>
            {d.skipGroups.length === 0 ? (
              <p className="muted">Nothing discarded on this snapshot.</p>
            ) : (
              <ul className="discard-list">
                {d.skipGroups.slice(0, 16).map((g) => (
                  <li key={`${g.reason}-${g.underlying}-${g.side}`}>
                    <div>
                      <strong>
                        {g.underlying} {g.side || ""}
                      </strong>
                      <span className="discard-who">{g.who}</span>
                      <span className="fx-skips__n">×{g.n}</span>
                    </div>
                    <p>
                      {skipPlain(g.reason)}
                      {g.why ? ` — ${String(g.why).slice(0, 140)}` : ""}
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

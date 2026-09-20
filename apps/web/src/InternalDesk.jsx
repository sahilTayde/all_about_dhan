import { useEffect, useMemo, useState } from "react";
import { AppNav } from "./components/AppNav.jsx";
import { Header } from "./components/Header.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import {
  clock,
  derivePaperBoard,
  deskLifeStatus,
  fetchMlPaperBoard,
  inr,
  moneyClass,
  outcomeLabel,
  outcomeSlug,
  pathInfo,
  pct,
  px,
  shortWhy,
  skipPlain,
} from "./lib/paperBoard.js";

function StatusPill({ status }) {
  const slug = String(status || "DEAD").toLowerCase();
  return <span className={`life-pill life-pill--${slug}`}>{status}</span>;
}

function OutcomePill({ label }) {
  return <span className={`out-pill out-pill--${outcomeSlug(label)}`}>{label}</span>;
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
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    try {
      const json = await fetchMlPaperBoard();
      setBoard(json);
      setError(null);
      setTick((n) => n + 1);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 8000);
    return () => clearInterval(id);
  }, []);

  const d = useMemo(() => derivePaperBoard(board), [board]);
  const current = d?.current;
  const life = deskLifeStatus(current);
  const path = current ? pathInfo(current) : null;
  const spot =
    current && d?.regimes?.[current.underlying]
      ? d.regimes[current.underlying].itm_bin?.index ?? d.regimes[current.underlying].vwap
      : null;

  return (
    <div className="shell shell--internal">
      <AppNav current="/desk" />
      <Header
        title="Desk"
        kicker="Live paper ticket"
        sub="Current signal, path to target or stop, full book, why it fired, what the boss discarded."
        sourceLabel={board?.live_session ? "PAPER" : "MOCK"}
      />

      <div className="desk-refresh">
        <p className="desk-sub">
          Latest {board?.as_of_ist ? board.as_of_ist.replace("T", " ").slice(0, 19) : "—"} · auto every 8s · tick #{tick}
        </p>
        <button type="button" className="refresh-btn" onClick={load} disabled={busy}>
          {busy ? "Refreshing…" : "Refresh now"}
        </button>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}
      {!d ? (
        <p className="muted">Loading desk…</p>
      ) : (
        <>
          <section className="panel current-signal" aria-labelledby="current-signal">
            <div className="panel__head">
              <div>
                <h2 id="current-signal">Current trade signal</h2>
                <p className="fx-kicker">PAPER · not a broker fill</p>
              </div>
              <StatusPill status={current ? life : "DEAD"} />
            </div>

            {!current ? (
              <p className="muted">No open ticket. Waiting for the next MIX-DEFAULT-BUY fill.</p>
            ) : (
              <>
                <div className="current-signal__hero">
                  <div>
                    <span className={`side-mini side-mini--${String(current.side).toLowerCase()}`}>
                      {current.side}
                    </span>
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
                  <p>
                    Distance score only — closer to target than stop reads higher. Not a win rate. Not a fill promise.
                  </p>
                </div>
              </>
            )}
          </section>

          <section className="panel">
            <h2>Why this signal</h2>
            {current ? (
              <ul className="logic-list">
                <li>
                  <strong>Ticket</strong> {current.underlying} {current.side} {current.atm_strike} because{" "}
                  {shortWhy(current.justification)}
                </li>
                <li>
                  <strong>Regime</strong> {current.index_regime || "—"} · {current.regime_reason || "—"}
                </li>
                <li>
                  <strong>Books that generated it</strong> {(current.books || [current.book_id]).join(", ")}
                </li>
                {(d.modelSignals.latest || []).slice(0, 4).map((r) => (
                  <li key={`${r.source}-${r.ts || r.side}`}>
                    <strong>{r.source}</strong> said {r.side || "SILENT"} · vs picker {r.vs_picker || "—"} · observer{" "}
                    {r.observer_action || "—"}
                    {r.ignored_by_boss ? " · ignored by boss" : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">{d.seen.note || "No live justification until a ticket opens."}</p>
            )}
          </section>

          <section className="panel">
            <h2>Trade history</h2>
            <p className="muted">
              Index · CE/PE · spot / SL / target · P/L · ACHIEVED / CANCELLED / STOP LOSS HIT / TARGET HIT / TRAIL /
              TARGET 2.
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
                  {d.uniqueClosed.slice(0, 40).map((t) => {
                    const label = outcomeLabel(t);
                    const spotPx = d.regimes?.[t.underlying]?.itm_bin?.index;
                    return (
                      <tr key={t.trade_id}>
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
          </section>

          <section className="panel">
            <h2>Discarded by boss or dealer</h2>
            <p className="muted">
              Signals seen but not taken, cancelled, vetoed, or ignored. Last section so the live ticket stays first.
            </p>
            {d.skipGroups.length === 0 ? (
              <p className="muted">Nothing discarded on this snapshot.</p>
            ) : (
              <ul className="discard-list">
                {d.skipGroups.slice(0, 24).map((g) => (
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
                      {g.why ? ` — ${String(g.why).slice(0, 180)}` : ""}
                    </p>
                    {g.books.length ? <p className="desk-sub">{g.books.join(" · ")}</p> : null}
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

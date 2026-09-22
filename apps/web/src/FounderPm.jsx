import { useEffect, useMemo, useState } from "react";
import { AppNav } from "./components/AppNav.jsx";
import { FounderHonestyExam } from "./components/FounderHonestyExam.jsx";
import { FounderRoster } from "./components/FounderRoster.jsx";
import { Header } from "./components/Header.jsx";
import { SodFillGraph, WatcherStrip } from "./components/SodFillGraph.jsx";
import { FounderBookPicker } from "./components/FounderBookPicker.jsx";
import { TradeHistory } from "./components/TradeHistory.jsx";
import {
  derivePaperBoard,
  fetchFounderLab,
  fetchMlPaperBoard,
  fetchSodExam,
  inr,
  moneyClass,
  pct,
} from "./lib/paperBoard.js";

function fetchFounderStatus(signal) {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  const url = base ? `${base}/founder/status` : "/founder/status";
  return fetch(`${url}?t=${Date.now()}`, { signal }).then((res) => {
    if (!res.ok) throw new Error(`status ${res.status}`);
    return res.json();
  });
}

function Stat({ label, value, hint, tone }) {
  return (
    <div className={`fx-stat ${tone ? `fx-stat--${tone}` : ""}`}>
      <span className="fx-stat__label">{label}</span>
      <strong className={`fx-stat__value ${tone === "up" ? "is-up" : ""} ${tone === "down" ? "is-down" : ""}`}>
        {value}
      </strong>
      {hint ? <span className="fx-stat__hint">{hint}</span> : null}
    </div>
  );
}

export function FounderPm() {
  const [status, setStatus] = useState(null);
  const [board, setBoard] = useState(null);
  const [lab, setLab] = useState(null);
  const [exam, setExam] = useState(null);
  const [error, setError] = useState(null);
  const [roomId, setRoomId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();
    async function pull(force) {
      const results = await Promise.allSettled([
        fetchFounderStatus(ac.signal),
        fetchMlPaperBoard({ force, signal: ac.signal }),
        fetchFounderLab({ signal: ac.signal }),
        fetchSodExam({ signal: ac.signal }),
      ]);
      if (cancelled) return;
      const nextErr = [];
      if (results[0].status === "fulfilled") setStatus(results[0].value);
      else nextErr.push("ops health offline");
      if (results[1].status === "fulfilled") setBoard(results[1].value);
      else nextErr.push("paper book missing");
      if (results[2].status === "fulfilled") setLab(results[2].value);
      if (results[3].status === "fulfilled") setExam(results[3].value);
      setError(nextErr.length ? nextErr.join(" · ") : null);
    }
    pull(true);
    const id = setInterval(() => pull(false), 15000);
    return () => {
      cancelled = true;
      ac.abort();
      clearInterval(id);
    };
  }, []);

  const d = useMemo(() => derivePaperBoard(board, lab), [board, lab]);
  const paper = (status?.agents || []).find((a) => a.id === "paper-loop");
  const day = d?.todayDay;
  const room = roomId && d?.fillRooms?.[roomId] ? d.fillRooms[roomId] : d?.currentRoom;

  return (
    <div className="shell shell--founder">
      <AppNav current="/pm" />
      <Header
        title="Founder"
        kicker="Train · compare · do not promote"
        sub="Money, rooms, and how a paper fill was built. Click a node. PAPER only."
        sourceLabel={board?.live_session ? "PAPER" : "MOCK"}
      />
      <p className="desk-sub">
        {board?.as_of_ist ? board.as_of_ist.replace("T", " ").slice(0, 16) : "…"} IST · light refresh 15s · orders
        refused · NO_PROMOTE
      </p>
      {error ? <p className="desk-error">{error}. Mock book still loads.</p> : null}

      <div className="fx-health">
        <span className={`cleanup-pill ${paper?.alive ? "done" : "pending"}`}>
          paper {paper?.alive ? "ON" : "OFF / mock"}
        </span>
        <span className="cleanup-pill pending">NO_PROMOTE</span>
        <span className="cleanup-pill pending">orders refused</span>
      </div>

      {!d ? (
        <p className="muted">Loading founder book…</p>
      ) : (
        <>
          <div className="fx-stats founder-kpis">
            <Stat
              label="Total trades"
              value={String(d.uniqueClosed.length)}
              hint={d.liveMoney ? "Live closed only" : "Paper book (no lab trainer)"}
            />
            <Stat label="Win rate" value={pct(d.uniqueWr ?? d.moneyWr)} hint="Net ₹ > 0 after charges · live book" />
            <Stat
              label="Account"
              value={inr(d.equity, { signed: false })}
              hint={`Start ${inr(d.startCap, { signed: false })}`}
              tone={Number(d.equity) >= Number(d.startCap) ? "up" : "down"}
            />
            <Stat
              label="Profit today"
              value={inr(day?.profit)}
              hint={day?.n ? `${day.day} · ${day.n} live` : `${day?.day || "—"} · no live fills`}
              tone="up"
            />
            <Stat
              label="Loss today"
              value={inr(day?.loss)}
              hint={day?.n ? `${day.n} live fills` : "no live fills"}
              tone="down"
            />
            <Stat
              label="Net today"
              value={inr(day?.net)}
              hint={d.liveMoney ? "This IST session only" : day?.day}
              tone={Number(day?.net) >= 0 ? "up" : "down"}
            />
          </div>

          <FounderBookPicker />

          <section className="panel">
            <h2>Train the models</h2>
            <p className="muted">
              {d.training?.label_note || "Label analysts from MATCH / DISSENT vs TARGET. Not a customer win rate."}
            </p>
            <div className="founder-pl">
              <div>
                <span>Target wr</span>
                <strong>{pct(d.targetWr)}</strong>
              </div>
              <div>
                <span>Money wr</span>
                <strong>{pct(d.moneyWr)}</strong>
              </div>
              <div>
                <span>MATCH</span>
                <strong>{d.nMatch}</strong>
              </div>
              <div>
                <span>DISSENT</span>
                <strong>{d.nDissent}</strong>
              </div>
              <div>
                <span>Charges</span>
                <strong>{inr(d.charges, { signed: false })}</strong>
              </div>
              <div>
                <span>Clone drag</span>
                <strong>{inr(d.cloneDrag)}</strong>
              </div>
            </div>
            <div className="mini-split">
              <ul className="founder-watch">
                {(d.byIndex || []).map((g) => (
                  <li key={g.key}>
                    {g.key} · {g.n} · {pct(g.wr)} · <span className={moneyClass(g.net)}>{inr(g.net)}</span>
                  </li>
                ))}
              </ul>
              <ul className="founder-watch">
                {(d.byRegime || []).map((g) => (
                  <li key={g.key}>
                    {g.key} · {g.n} · {pct(g.wr)} · <span className={moneyClass(g.net)}>{inr(g.net)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="panel">
            <h2>How this paper fill was placed</h2>
            <p className="muted">Click a node. Watchers and signal types sit under the graph.</p>
            <SodFillGraph room={room} />
            <WatcherStrip watchers={room?.watchers} />
            {room?.steps?.length ? (
              <ol className="step-list">
                {room.steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            ) : null}
          </section>

          <FounderRoster catalog={d.catalog} confirmKill={d.confirmKill} />

          <section className="panel">
            <h2>Models — win % today</h2>
            <div className="table-scroll">
              <table className="book-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Kind</th>
                    <th>Fills</th>
                    <th>Win % today</th>
                    <th>Win % book</th>
                    <th>Charges</th>
                    <th>Net ₹</th>
                  </tr>
                </thead>
                <tbody>
                  {d.books.map((r) => (
                    <tr key={r.book_id}>
                      <td>{r.book_id}</td>
                      <td>{r.kind || "—"}</td>
                      <td className="num">{r.day_n ?? r.n_filled ?? 0}</td>
                      <td className="num">{r.day_wr == null ? "—" : pct(r.day_wr)}</td>
                      <td className="num">{r.win_rate_net_pct == null ? "—" : pct(r.win_rate_net_pct)}</td>
                      <td className="num">{inr(r.sum_charges_inr, { signed: false })}</td>
                      <td className={`num ${moneyClass(r.sum_pnl_inr)}`}>{inr(r.sum_pnl_inr)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <h2>Each day</h2>
            <div className="table-scroll">
              <table className="book-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Trades</th>
                    <th>Win %</th>
                    <th>Profit</th>
                    <th>Loss</th>
                    <th>Charges</th>
                    <th>Net</th>
                  </tr>
                </thead>
                <tbody>
                  {d.days.map((row) => (
                    <tr key={row.day}>
                      <td>{row.day}</td>
                      <td className="num">{row.n}</td>
                      <td className="num">{pct(row.wr)}</td>
                      <td className={`num ${moneyClass(row.profit)}`}>{inr(row.profit)}</td>
                      <td className={`num ${moneyClass(row.loss)}`}>{inr(row.loss)}</td>
                      <td className="num">{inr(row.charges, { signed: false })}</td>
                      <td className={`num ${moneyClass(row.net)}`}>{inr(row.net)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <h2>Compare fills</h2>
            <p className="muted">Filter, then click a highlighted row that has a fill room.</p>
            <TradeHistory
              rows={d.uniqueClosed}
              regimes={d.regimes}
              fillRooms={d.fillRooms}
              onOpen={(t) => setRoomId(t.trade_id)}
            />
          </section>

          <details className="desk-context">
            <summary>Ops health</summary>
            <div className="cleanup-grid">
              {(status?.agents || []).map((a) => (
                <article key={a.id} className={`cleanup-card founder-${a.tone || "grey"}`}>
                  <div className="cleanup-status">{a.alive ? "RUNNING" : "DOWN"}</div>
                  <strong>{a.name}</strong>
                  <p>{a.detail}</p>
                </article>
              ))}
              {(status?.services || []).map((s) => (
                <article key={s.id} className={`cleanup-card founder-${s.tone || "grey"}`}>
                  <div className="cleanup-status">{s.tone}</div>
                  <strong>{s.name}</strong>
                  <p>{s.detail}</p>
                </article>
              ))}
            </div>
          </details>

          <FounderHonestyExam exam={exam} />
        </>
      )}
    </div>
  );
}

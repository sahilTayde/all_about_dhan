import { useEffect, useMemo, useState } from "react";
import { AppNav } from "./components/AppNav.jsx";
import { Header } from "./components/Header.jsx";
import {
  derivePaperBoard,
  fetchMlPaperBoard,
  inr,
  moneyClass,
  pct,
} from "./lib/paperBoard.js";

function fetchFounderStatus() {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  const url = base ? `${base}/founder/status` : "/founder/status";
  return fetch(`${url}?t=${Date.now()}`).then((res) => {
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
  const [error, setError] = useState(null);
  const [asOf, setAsOf] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function pull() {
      const results = await Promise.allSettled([fetchFounderStatus(), fetchMlPaperBoard()]);
      if (cancelled) return;
      const nextErr = [];
      if (results[0].status === "fulfilled") setStatus(results[0].value);
      else nextErr.push(`health ${results[0].reason?.message || results[0].reason}`);
      if (results[1].status === "fulfilled") {
        setBoard(results[1].value);
        setAsOf(results[1].value.as_of_ist || null);
      } else nextErr.push(`book ${results[1].reason?.message || results[1].reason}`);
      setError(nextErr.length ? nextErr.join(" · ") : null);
    }
    pull();
    const id = setInterval(pull, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const d = useMemo(() => derivePaperBoard(board), [board]);
  const paper = (status?.agents || []).find((a) => a.id === "paper-loop");
  const day = d?.todayDay;

  return (
    <div className="shell shell--founder">
      <AppNav current="/pm" />
      <Header
        title="Founder"
        kicker="Paper money · one desk"
        sub="What happened today, what it cost, which model paid. PAPER — not a live book."
        sourceLabel={board?.live_session ? "PAPER" : "MOCK"}
      />
      <p className="desk-sub">
        Updated {asOf ? asOf.replace("T", " ").slice(0, 16) : "…"} IST · refreshes every 10s · orders refused ·
        NO_PROMOTE
      </p>

      {error ? <p className="desk-error">{error}. Numbers below may be mock if the API is down.</p> : null}

      <div className="fx-health" aria-label="Desk health">
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
            <Stat label="Total trades" value={String(d.uniqueClosed.length)} hint="Unique fills (clones collapsed)" />
            <Stat
              label="Win rate"
              value={pct(d.uniqueWr ?? d.moneyWr)}
              hint="Net ₹ > 0 after charges. Not a promote."
            />
            <Stat
              label="Account balance"
              value={inr(d.equity, { signed: false })}
              hint={`Start ${inr(d.startCap, { signed: false })}`}
              tone={Number(d.equity) >= Number(d.startCap) ? "up" : "down"}
            />
            <Stat
              label="Profit today"
              value={inr(day?.profit)}
              hint={day?.day || "—"}
              tone={Number(day?.profit) > 0 ? "up" : ""}
            />
            <Stat
              label="Loss today"
              value={inr(day?.loss)}
              hint={`${day?.n || 0} unique fills`}
              tone={Number(day?.loss) < 0 ? "down" : ""}
            />
            <Stat
              label="Net today"
              value={inr(day?.net ?? d.uniqueNet)}
              hint="Unique desk P/L"
              tone={Number(day?.net ?? d.uniqueNet) >= 0 ? "up" : "down"}
            />
          </div>

          <section className="panel">
            <div className="panel__head">
              <div>
                <h2>P/L with charges</h2>
                <p className="fx-kicker">Groww-style brokerage + GST + STT (VERIFY). Paper only.</p>
              </div>
            </div>
            <div className="founder-pl">
              <div>
                <span>Gross</span>
                <strong className={moneyClass(d.today.gross_pnl_inr ?? d.uniqueGross)}>
                  {inr(d.today.gross_pnl_inr ?? d.uniqueGross)}
                </strong>
              </div>
              <div>
                <span>Charges</span>
                <strong>{inr(d.charges, { signed: false })}</strong>
              </div>
              <div>
                <span>Net</span>
                <strong className={moneyClass(d.today.net_pnl_inr ?? d.uniqueNet)}>
                  {inr(d.today.net_pnl_inr ?? d.uniqueNet)}
                </strong>
              </div>
              <div>
                <span>Charge drag</span>
                <strong>
                  {d.today.gross_pnl_inr
                    ? pct(
                        (Math.abs(Number(d.charges) || 0) /
                          Math.max(1, Math.abs(Number(d.today.gross_pnl_inr)))) *
                          100
                      )
                    : "—"}
                </strong>
              </div>
            </div>
            <p className="muted">
              Improvement to watch: unique net {inr(d.uniqueNet)} vs all-book headline {inr(d.headlineNet)}.
              Clone drag {inr(d.cloneDrag)} is copies of the same fill — do not manage to it. Target hits{" "}
              {d.nTarget} / {d.uniqueClosed.length} ({pct(d.targetWr)}) vs money win rate {pct(d.moneyWr)}.
            </p>
          </section>

          <section className="panel">
            <h2>Models / strategies — win rate today</h2>
            <p className="muted">Day % is unique-fill win rate for this session. Observe books stay ₹0.</p>
            <div className="book-table-wrap">
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
            <div className="book-table-wrap">
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

          <details className="desk-context">
            <summary>Ops health (API, paper loop, site)</summary>
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

          <section className="panel">
            <h2>What else matters</h2>
            <ul className="founder-watch">
              <li>
                Best index {d.today.best_index || "—"} · worst {d.today.worst_index || "—"} · NIFTY{" "}
                {inr(d.today.net_by_index?.NIFTY)} · BANKNIFTY {inr(d.today.net_by_index?.BANKNIFTY)} · SENSEX{" "}
                {inr(d.today.net_by_index?.SENSEX)}
              </li>
              <li>
                Open now {d.uniqueOpen.length} · STOP hits {d.nStop} · TARGET hits {d.nTarget} · discarded signals{" "}
                {d.skipGroups.length}
              </li>
              <li>
                Gate: {board.gate || "not RESEARCH_READY_FOR_PROGRAMMING"}. Confidence and path scores are not win
                rates.
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

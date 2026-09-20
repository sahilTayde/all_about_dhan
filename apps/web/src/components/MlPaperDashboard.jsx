import { useEffect, useMemo, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;
const UNIQUE_BOOKS = ["MIX-DEFAULT-BUY", "MIX-ML-LOGIT", "MIX-ML-LOGIT-XR", "MIX-ML-GREEKS"];

function paperCloseView(t) {
  const reason = String(t?.exit_reason || "");
  const targetHit = t?.target_hit === true || reason === "TARGET";
  let result = t?.result;
  if (reason === "TIME" && result === "SUCCESS") result = "TIME";
  if ((reason === "FLATTEN_1515" || reason === "FLATTEN_1500") && result === "SUCCESS") {
    result = "FLATTEN";
  }
  return { result, targetHit, reason: reason || "—" };
}

function inr(n, { signed = true, digits = 0 } = {}) {
  if (n == null || n === "" || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const body = `₹${Math.abs(v).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })}`;
  if (!signed) return v < 0 ? `-${body}` : body;
  if (v > 0) return `+${body}`;
  if (v < 0) return `-${body}`;
  return body;
}

function px(n) {
  if (n == null || n === "" || Number.isNaN(Number(n))) return "—";
  return Number(n).toFixed(2);
}

function clock(ist) {
  if (!ist) return "—";
  const m = String(ist).match(/T(\d{2}:\d{2})/);
  return m ? m[1] : String(ist);
}

function moneyClass(n) {
  const v = Number(n);
  if (!Number.isFinite(v) || v === 0) return "";
  return v > 0 ? "is-up" : "is-down";
}

function shortWhy(text) {
  if (!text) return "—";
  const now = String(text).match(/why_now=([^;|]+)/);
  if (now) return now[1].trim();
  const close = String(text).split("| CLOSE:")[0];
  const bit = close.replace(/^NIFTY buy /i, "").trim();
  return bit.length > 160 ? `${bit.slice(0, 157)}…` : bit;
}

function fillKey(t) {
  return [
    t.opened_ts || t.opened_ist || "",
    t.underlying,
    t.side,
    t.atm_strike,
    t.entry ?? t.limit_price,
    t.exit ?? "",
    t.exit_reason || "OPEN",
  ].join("|");
}

function uniqueFills(rows) {
  const map = new Map();
  for (const t of rows) {
    const k = fillKey(t);
    if (!map.has(k)) {
      map.set(k, { ...t, books: [t.book_id] });
    } else {
      const row = map.get(k);
      if (!row.books.includes(t.book_id)) row.books.push(t.book_id);
    }
  }
  return [...map.values()];
}

function overlayLine(o) {
  if (!o) return "NIFTY overlay not on this snapshot.";
  const sides = (o.allow_sides || []).join(" + ") || "—";
  return `NIFTY ${sides} only. Opens need last-3 / pause-continue / short-cover. Cap ${o.max_filled_per_book ?? "—"} fills/book. BANKNIFTY and SENSEX skipped. PAPER — not a live order.`;
}

function pathInfo(t) {
  const last = Number(t.last_ltp ?? t.exit);
  const stop = Number(t.stop);
  const target = Number(t.target);
  const entry = Number(t.entry ?? t.limit_price);
  const span = target - stop;
  const pct = Number.isFinite(span) && span !== 0 && Number.isFinite(last) ? (last - stop) / span : null;
  const toTarget = Number.isFinite(last) && Number.isFinite(target) ? target - last : null;
  const slRoom = Number.isFinite(last) && Number.isFinite(stop) ? last - stop : null;
  const vsEntry = Number.isFinite(last) && Number.isFinite(entry) ? last - entry : null;
  return { last, stop, target, entry, pct, toTarget, slRoom, vsEntry };
}

function groupSkips(rows) {
  const map = new Map();
  for (const t of rows) {
    const k = `${t.reason || "SKIP"}|${t.underlying || "?"}|${t.seen_side || t.side || "—"}`;
    if (!map.has(k)) {
      map.set(k, {
        reason: t.reason,
        underlying: t.underlying,
        side: t.seen_side || t.side,
        why: t.why,
        books: [],
        n: 0,
      });
    }
    const g = map.get(k);
    g.n += 1;
    if (t.book_id && !g.books.includes(t.book_id)) g.books.push(t.book_id);
  }
  return [...map.values()].sort((a, b) => b.n - a.n);
}

function skipPlain(reason) {
  const r = String(reason || "");
  if (r === "FOCUS_NIFTY_ONLY") return "SENSEX parked — this ship is NIFTY only";
  if (r === "FOCUS_NIFTY_SENSEX") return "BANKNIFTY parked";
  if (r === "NIFTY_WAIT_STRENGTH") return "Waiting for last-3 / pause-continue / short-cover";
  if (r === "GREEKS_NO_CLONE") return "Greeks book does not copy the same fill";
  if (r.startsWith("XR")) return "XR filter skipped this side";
  if (r.includes("OBSERVE")) return "Observe book — ₹0, no fill";
  if (r.includes("ML-001") || r.includes("HOLD")) return "ML-001 holding";
  return r.replaceAll("_", " ");
}

function ResultPill({ view }) {
  const r = view.result;
  const cls =
    view.targetHit || r === "SUCCESS"
      ? "status-pill status-pill--targethit"
      : r === "LOSS" || view.reason === "STOP"
        ? "status-pill status-pill--stoplosshit"
        : r === "TIME"
          ? "status-pill status-pill--expired"
          : "status-pill status-pill--inprogress";
  const label = view.targetHit ? "TARGET" : r === "TIME" ? "TIME (not target)" : r || view.reason;
  return <span className={cls}>{label}</span>;
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

function TicketPath({ t }) {
  const p = pathInfo(t);
  const width = p.pct == null ? 0 : Math.max(4, Math.min(96, p.pct * 100));
  return (
    <div className="fx-path">
      <div className="fx-path__bar" aria-hidden="true">
        <i style={{ width: `${width}%` }} />
      </div>
      <div className="fx-path__ticks">
        <span>SL {px(p.stop)}</span>
        <span>now {px(p.last)}</span>
        <span>tgt {px(p.target)}</span>
      </div>
    </div>
  );
}

async function fetchMlPaperBoard() {
  const url = API_URL ? `${API_URL}/paper/ml-books` : "/mock/ml_paper_dashboard.json";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`ml paper board HTTP ${res.status}`);
  return res.json();
}

export function MlPaperDashboard({ compact = false }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("now");

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchMlPaperBoard()
        .then((j) => {
          if (!cancelled) {
            setData(j);
            setError(null);
          }
        })
        .catch((e) => {
          if (!cancelled) setError(e.message || String(e));
        });
    };
    load();
    const id = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const derived = useMemo(() => {
    if (!data) return null;
    const today = data.today || {};
    const byUpdated = (a, b) => {
      const ta = Number(a?.last_updated_ts || a?.closed_ts || a?.opened_ts || 0);
      const tb = Number(b?.last_updated_ts || b?.closed_ts || b?.opened_ts || 0);
      return tb - ta;
    };
    const closed = [...(data.closed_trades || [])].sort(byUpdated);
    const open = [...(data.open_trades || [])].sort(byUpdated);
    const uniqueClosed = uniqueFills(closed);
    const uniqueOpen = uniqueFills(open);
    const views = uniqueClosed.map((t) => ({ t, view: paperCloseView(t) }));
    const nTarget = views.filter((x) => x.view.targetHit).length;
    const nTime = views.filter((x) => x.view.reason === "TIME").length;
    const nStop = views.filter((x) => x.view.reason === "STOP" || x.t.sl_hit).length;
    const uniqueFillNet = uniqueClosed.reduce((s, t) => s + (Number(t.realized_pnl_inr) || 0), 0);
    const uniqueNet = uniqueFillNet;
    const bookUniqueNet = today.unique_net_pnl_inr;
    const cloneNet = data.overall_pnl_inr;
    const bins = data.itm_bins || today.itm_bins || {};
    const niftyBin = (bins.bins || []).find((b) => b.underlying === "NIFTY") || (bins.bins || [])[0];
    const uniqueRank = (data.book_rank || []).filter((r) =>
      (today.unique_books || UNIQUE_BOOKS).includes(r.book_id)
    );
    const seen = data.seen_not_taken || today.seen_not_taken || {};
    const modelSignals = data.model_signals || today.model_signals || {};
    const skipGroups = groupSkips([...(seen.skipped_latest || []), ...(seen.cancelled || [])]);
    const insights = [];
    insights.push(
      data.sod_one_ticket !== false
        ? `SOD one desk ticket. One-fill net ${inr(uniqueFillNet)}. Analyst CE/PE stays on the board even when picker HOLD / observer VETO / desk ignores.`
        : `One-fill money (clones collapsed) is ${inr(uniqueFillNet)}. Book-unique ${inr(bookUniqueNet)} still adds dealer+logit+XR copies. Headline ${inr(cloneNet)} is worse.`
    );
    if (nTarget === 0 && nTime > 0) {
      insights.push(
        `No TARGET hit today. ${nTime} unique TIME exit(s) are hold-clock green — premium never printed the booked target (the 148 PE case).`
      );
    } else if (nTarget > 0) {
      insights.push(`${nTarget} unique TARGET hit(s). That is the only SUCCESS that means the price path worked.`);
    }
    if (nStop) {
      insights.push(`${nStop} unique STOP. Path SL hit before target — that is the real miss, not a TIME green.`);
    }
    for (const t of uniqueOpen) {
      const p = pathInfo(t);
      if (p.toTarget != null) {
        insights.push(
          `Open ${t.side} ${t.atm_strike}: last ₹${px(p.last)} · ${p.toTarget.toFixed(1)} pts to target · ${
            p.slRoom == null ? "—" : p.slRoom.toFixed(1)
          } pts of SL room · vs entry ${p.vsEntry == null ? "—" : inr(p.vsEntry, { digits: 2 })}/pt.`
        );
      }
    }
    if (niftyBin) {
      insights.push(
        `Live NIFTY bin leans ${niftyBin.side || "wait"} — CE ${niftyBin.ce?.strike ?? "—"} ₹${px(
          niftyBin.ce?.px
        )} vs PE ${niftyBin.pe?.strike ?? "—"} ₹${px(niftyBin.pe?.px)}. Booked strike can differ from this bin.`
      );
    }
    const moneyWr = data.win_rate_net_pct ?? today.win_rate_net_pct;
    const targetWr =
      uniqueClosed.length > 0 ? Math.round((nTarget / uniqueClosed.length) * 1000) / 10 : null;
    return {
      today,
      closed,
      open,
      uniqueClosed,
      uniqueOpen,
      views,
      nTarget,
      nTime,
      nStop,
      uniqueNet,
      bookUniqueNet,
      cloneNet,
      bins,
      niftyBin,
      uniqueRank,
      skipGroups,
      insights,
      moneyWr,
      targetWr,
      seen,
      modelSignals,
    };
  }, [data]);

  if (error) {
    return (
      <section className="panel fx-board" aria-labelledby="ml-paper-title">
        <h2 id="ml-paper-title">Live paper book</h2>
        <p className="muted">Board missing ({error}). PAPER only. No npm restart.</p>
      </section>
    );
  }
  if (!data || !derived) {
    return (
      <section className="panel fx-board">
        <h2>Live paper book</h2>
        <p className="muted">Loading live paper…</p>
      </section>
    );
  }

  const {
    today,
    uniqueClosed,
    uniqueOpen,
    views,
    nTarget,
    nTime,
    nStop,
    uniqueNet,
    bookUniqueNet,
    cloneNet,
    bins,
    niftyBin,
    uniqueRank,
    skipGroups,
    insights,
    moneyWr,
    targetWr,
    seen,
    open,
    modelSignals,
  } = derived;

  const ranks = uniqueRank.length ? uniqueRank : data.book_rank || [];
  const showLab = !compact;

  return (
    <section className={`panel fx-board ${compact ? "fx-board--compact" : ""}`} aria-labelledby="ml-paper-title">
      <div className="panel__head">
        <div>
          <h2 id="ml-paper-title">Live paper book</h2>
          <p className="fx-kicker">
            {data.session_ist_date || "—"} · updated {clock(data.as_of_ist)} IST · PAPER · NO_PROMOTE ·
            {data.sod_one_ticket !== false
              ? " SOD one MIX-DEFAULT-BUY ticket · analyst room observe"
              : " A/B parallel books (--sod-off)"}{" "}
            · orders refused
          </p>
        </div>
        <span className="source-pill">unique P/L</span>
      </div>

      <div className="fx-stats">
        <Stat
          label="One-fill net"
          value={inr(uniqueNet)}
          hint="Each NIFTY fill counted once"
          tone={Number(uniqueNet) > 0 ? "up" : Number(uniqueNet) < 0 ? "down" : ""}
        />
        <Stat
          label="Book copies"
          value={inr(bookUniqueNet)}
          hint={data.sod_one_ticket !== false ? "Lab votes, no extra capital" : "Dealer+logit+XR still copy"}
        />
        <Stat label="All-books headline" value={inr(cloneNet)} hint="Do not manage to this" />
        <Stat label="TARGET hits" value={String(nTarget)} hint="Only this is SUCCESS" tone={nTarget ? "up" : ""} />
        <Stat label="TIME green" value={String(nTime)} hint="Hold clock, not target" />
        <Stat label="STOP" value={String(nStop)} hint="SL before target" tone={nStop ? "down" : ""} />
        <Stat
          label="Open now"
          value={String(uniqueOpen.length)}
          hint={`${open.length} book rows`}
        />
      </div>

      <p className="fx-overlay">{overlayLine(data.nifty_overlay)}</p>

      <div className="fx-wr">
        <span>
          Money wr <strong>{moneyWr ?? "—"}%</strong>
          <em> net&gt;0 after Groww+STT</em>
        </span>
        <span>
          Target wr <strong>{targetWr == null ? "—" : `${targetWr}%`}</strong>
          <em> unique TARGET / unique fills</em>
        </span>
        <span>
          Charges <strong>{inr(today.charges_inr ?? data.overall_charges_inr, { signed: false })}</strong>
        </span>
      </div>

      <div className="fx-insights">
        <h3>What this means</h3>
        <ul>
          {insights.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </div>

      <nav className="fx-tabs" aria-label="Paper board sections">
        {[
          ["now", "Now"],
          ["closed", "Closed"],
          ["money", "Books"],
          ["tape", "Tape"],
          ["signals", "Analysts"],
          ["skips", "Skipped"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`chip ${tab === id ? "chip--active" : ""}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "now" && (
        <div className="fx-section">
          <h3>Open tickets</h3>
          {uniqueOpen.length === 0 ? (
            <p className="muted">Nothing open. Waiting for next NIFTY strength print.</p>
          ) : (
            <div className="fx-tickets">
              {uniqueOpen.map((t) => {
                const p = pathInfo(t);
                return (
                  <article key={t.trade_id} className={`fx-ticket fx-ticket--${String(t.side).toLowerCase()}`}>
                    <header>
                      <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
                      <strong>
                        {t.underlying} {t.atm_strike}
                      </strong>
                      <span className="status-pill status-pill--inprogress">{t.status || "OPEN"}</span>
                    </header>
                    <dl className="level-strip fx-ticket__levels">
                      <div>
                        <dt>Entry</dt>
                        <dd>{px(p.entry)}</dd>
                      </div>
                      <div>
                        <dt>Last</dt>
                        <dd>{px(p.last)}</dd>
                      </div>
                      <div>
                        <dt>Stop</dt>
                        <dd>{px(p.stop)}</dd>
                      </div>
                      <div>
                        <dt>Target</dt>
                        <dd>{px(p.target)}</dd>
                      </div>
                    </dl>
                    <TicketPath t={t} />
                    <p className="fx-ticket__call">
                      {p.toTarget == null
                        ? "Waiting on LTP."
                        : p.toTarget <= 0
                          ? "Last is at/through target — should be TARGET if the loop is live."
                          : `${p.toTarget.toFixed(1)} pts still needed for TARGET · SL room ${
                              p.slRoom == null ? "—" : `${p.slRoom.toFixed(1)} pts`
                            }.`}
                    </p>
                    <p className="desk-sub fx-ticket__why">{shortWhy(t.justification)}</p>
                    <p className="fx-books">on {t.books.join(" · ")}</p>
                  </article>
                );
              })}
            </div>
          )}

          {niftyBin ? (
            <div className="fx-bin">
              <h3>NIFTY wing right now</h3>
              <p className="muted">
                Live ITM bin — not automatically the strike you are in. Lean{" "}
                <strong>{niftyBin.side || "wait"}</strong>.
              </p>
              <div className="fx-bin__grid">
                <article>
                  <span className="side-mini side-mini--ce">CE</span>
                  <strong>{niftyBin.ce?.strike ?? "—"}</strong>
                  <span>₹{px(niftyBin.ce?.px)}</span>
                </article>
                <article>
                  <span className="fx-bin__spot">INDEX</span>
                  <strong>{px(niftyBin.index)}</strong>
                  <span>{niftyBin.reason || ""}</span>
                </article>
                <article>
                  <span className="side-mini side-mini--pe">PE</span>
                  <strong>{niftyBin.pe?.strike ?? "—"}</strong>
                  <span>₹{px(niftyBin.pe?.px)}</span>
                </article>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {tab === "closed" && (
        <div className="fx-section">
          <h3>Unique fills (clones collapsed)</h3>
          <p className="muted">
            SUCCESS means the booked strike printed target. TIME green is still rupees, not a target.
          </p>
          {views.length === 0 ? (
            <p className="muted">No closed fills yet.</p>
          ) : (
            <div className="book-table-wrap">
              <table className="book-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Side</th>
                    <th>Strike</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Target</th>
                    <th>How it ended</th>
                    <th>Net ₹</th>
                    <th>Books</th>
                  </tr>
                </thead>
                <tbody>
                  {views.map(({ t, view }) => (
                    <tr key={t.trade_id}>
                      <td>{clock(t.last_updated_ist || t.closed_ist)}</td>
                      <td>
                        <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
                      </td>
                      <td className="num">{t.atm_strike}</td>
                      <td className="num">{px(t.entry ?? t.limit_price)}</td>
                      <td className="num">{px(t.exit)}</td>
                      <td className="num">{px(t.target)}</td>
                      <td>
                        <ResultPill view={view} />
                      </td>
                      <td className={`num ${moneyClass(t.realized_pnl_inr)}`}>{inr(t.realized_pnl_inr)}</td>
                      <td>{t.books.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!compact && views.length > 0 ? (
            <details className="desk-context">
              <summary>Why each unique fill closed</summary>
              <ul className="fx-why-list">
                {views.map(({ t, view }) => (
                  <li key={`why-${t.trade_id}`}>
                    <ResultPill view={view} /> {t.side} {t.atm_strike} exit {px(t.exit)} vs tgt {px(t.target)}
                    <div className="desk-sub">{shortWhy(t.justification)}</div>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      )}

      {tab === "money" && (
        <div className="fx-section">
          <h3>Unique books</h3>
          <ul className="fx-rank">
            {ranks.map((r) => (
              <li key={r.book_id}>
                <span>
                  #{r.rank} {r.book_id}
                </span>
                <span>
                  {r.n_filled} fills · {r.n_wins} money-W / {r.n_losses} L
                </span>
                <strong className={moneyClass(r.sum_pnl_inr)}>{inr(r.sum_pnl_inr)}</strong>
              </li>
            ))}
          </ul>
          <p className="muted">
            Observe books (ML-001 / ML-002 / ML-1 / TV-EP) keep ₹0 so they cannot fake the desk.
          </p>
        </div>
      )}

      {tab === "tape" && (
        <div className="fx-section">
          <h3>ITM CE vs PE</h3>
          {(bins.bins || []).length === 0 ? (
            <p className="muted">No bin yet.</p>
          ) : (
            <div className="book-table-wrap">
              <table className="book-table">
                <thead>
                  <tr>
                    <th>Index</th>
                    <th>Spot</th>
                    <th>CE</th>
                    <th>PE</th>
                    <th>Lean</th>
                  </tr>
                </thead>
                <tbody>
                  {(bins.bins || []).map((b) => (
                    <tr key={b.underlying}>
                      <td>{b.underlying}</td>
                      <td className="num">{px(b.index)}</td>
                      <td>
                        {b.ce?.strike} · ₹{px(b.ce?.px)}
                      </td>
                      <td>
                        {b.pe?.strike} · ₹{px(b.pe?.px)}
                      </td>
                      <td>
                        <strong>{b.side || "wait"}</strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "signals" && (
        <div className="fx-section">
          <h3>Analyst room vs picker</h3>
          <p className="muted">
            {modelSignals.note ||
              "Spoken CE/PE stays MATCH / DISSENT / SPOKEN_PICKER_HOLD / SILENT even when the boss HOLDs or observer VETOes. Not extra capital."}
          </p>
          {(modelSignals.latest || []).length === 0 ? (
            <p className="muted">No analyst tape on this snapshot yet.</p>
          ) : (
            <div className="book-table-wrap">
              <table className="book-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Side</th>
                    <th>vs picker</th>
                    <th>Picker</th>
                    <th>Observer</th>
                    <th>Ignored</th>
                  </tr>
                </thead>
                <tbody>
                  {(modelSignals.latest || []).map((r) => (
                    <tr key={`${r.source}-${r.ts || r.detail || ""}`}>
                      <td>{r.source}</td>
                      <td>{r.side || "SILENT"}</td>
                      <td>{r.vs_picker || "—"}</td>
                      <td>
                        {r.picker_action}/{r.picker_side || "—"}
                      </td>
                      <td>{r.observer_action || "—"}</td>
                      <td>{r.ignored_by_boss ? "yes" : "no"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {(modelSignals.counts || []).length ? (
            <p className="muted">
              {(modelSignals.counts || [])
                .slice(0, 12)
                .map((c) => `${c.source} ${c.vs_picker}×${c.n}`)
                .join(" · ")}
            </p>
          ) : null}
        </div>
      )}

      {tab === "skips" && (
        <div className="fx-section">
          <h3>Saw it, did not take it</h3>
          <p className="muted">{seen.note || "Grouped by reason so eight clone SKIPs are one line."}</p>
          {skipGroups.length === 0 ? (
            <p className="muted">No skips this snapshot.</p>
          ) : (
            <ul className="fx-skips">
              {skipGroups.slice(0, compact ? 8 : 16).map((g) => (
                <li key={`${g.reason}-${g.underlying}-${g.side}`}>
                  <strong>
                    {g.underlying} {g.side || ""}
                  </strong>{" "}
                  {skipPlain(g.reason)}
                  <span className="fx-skips__n"> ×{g.n}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {showLab ? (
        <details className="desk-context">
          <summary>Lab notes / DATA_INSUFFICIENT</summary>
          {(data.index_notes || []).slice(0, 8).map((n) => (
            <p key={n} className="desk-sub">
              {n}
            </p>
          ))}
          {(data.mistakes || []).length ? (
            <ul className="fx-why-list">
              {(data.mistakes || []).slice(-8).map((t) => (
                <li key={t.trade_id}>
                  {t.book_id} {t.side} {t.atm_strike} {inr(t.money_lost_inr)} — {t.lesson}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No LOSS notes.</p>
          )}
        </details>
      ) : null}
    </section>
  );
}

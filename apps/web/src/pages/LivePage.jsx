import { useEffect, useMemo, useState } from "react";
import { BackgroundTestBox } from "../components/BackgroundTestBox.jsx";
import { PnlChart } from "../components/PnlChart.jsx";
import { PremiumChart } from "../components/PremiumChart.jsx";
import { CHARGES_LABEL, RULES, riskView, periodNets, signalWhy, agedAlerts, exitRule, feedAges, inr, minsUntil, num, pctOf, pctText, strikeOf, tone } from "../lib/deskModel.js";
import { useLtpTape } from "../lib/ltpTape.js";
import { AlertList, FeedAges, Levels, Reason, Side, Strat, TradeTable } from "./parts.jsx";

function useTick(ms = 1000) {
  const [, set] = useState(0);
  useEffect(() => {
    const id = setInterval(() => set((n) => n + 1), ms);
    return () => clearInterval(id);
  }, [ms]);
}

function Countdown({ t }) {
  const rule = exitRule(t);
  if (rule.kind !== "time") return <span className="muted">{rule.text}</span>;
  const left = minsUntil(rule.at);
  if (left == null) return <span className="muted">{rule.text}</span>;
  if (left < 0) return <span className="late" data-testid="late-exit">LATE EXIT · was due {rule.at} IST ({Math.round(-left)} min ago)</span>;
  const mm = Math.floor(left), ss = Math.floor((left - mm) * 60);
  return <span className="cd">Exits at {rule.at} IST · <b className="num">{String(mm).padStart(2, "0")}:{String(ss).padStart(2, "0")}</b> left</span>;
}

function Position({ t, onPick, picked }) {
  const ltp = num(t.last_ltp);
  const qty = num(t.qty) || RULES.qty[t.underlying];
  const pnl = num(t.unrealized_pnl_inr) ?? (ltp != null && num(t.entry) != null && qty ? (ltp - t.entry) * qty : null);
  const late = exitRule(t).kind === "time" && (minsUntil(exitRule(t).at) ?? 1) < 0;
  return (
    <button type="button" className={`pos ${late ? "pos--late" : ""} ${picked ? "is-picked" : ""}`} onClick={() => onPick(t.trade_id)}>
      <div className="pos__head">
        <span className="pos__sym"><b className="num">{strikeOf(t) ?? "—"}</b> <Side side={t.side} /></span>
        <span className="muted">{num(t.lots) ?? RULES.lots} lots · {qty ?? "—"} qty</span>
      </div>
      <div className="pos__grid">
        <div><span>Bought</span><b className="num">{num(t.entry) ?? "—"}</b></div>
        <div><span>LTP</span><b className="num">{ltp ?? "—"}</b></div>
        <div><span>P&amp;L</span><b className={`num big ${tone(pnl)}`}>{inr(pnl)}</b></div>
        <div><span>%</span><b className={`num ${tone(pnl)}`}>{pctText(pctOf(t.entry, ltp))}</b></div>
      </div>
      <div className="pos__levels"><Levels t={t} /><span>Rule <b>{exitRule(t).kind === "time" ? `time exit ${RULES.holdMin} min` : exitRule(t).text}</b></span></div>
      <div className="pos__foot"><Countdown t={t} /><Strat id={t.book_id} /></div>
      <p className="pos__why"><b>Why:</b> {signalWhy(t)}</p>
    </button>
  );
}

function IndexCard({ und, dd, onPick, picked }) {
  const open = dd.open.filter((t) => t.underlying === und);
  const last = dd.closed.filter((t) => t.underlying === und).sort((a, b) => (b.closed_ts || 0) - (a.closed_ts || 0))[0];
  const blocked = dd.lists.blocked.filter((t) => t.underlying === und);
  const late = open.some((t) => exitRule(t).kind === "time" && (minsUntil(exitRule(t).at) ?? 1) < 0);
  return (
    <section className={`panel idx ${late ? "idx--late" : ""}`} data-testid={`side-${und}`}>
      <header className="panel__head"><h2>{und}</h2><span className="muted">{open.length ? `${open.length} open` : "flat"}</span></header>
      {open.length ? open.map((t) => <Position key={t.trade_id} t={t} onPick={onPick} picked={picked === t.trade_id} />) : <div className="flat">No open position</div>}
      {blocked.length ? <p className="note"><span className="tag tag--warn">blocked: opposite side</span> {blocked.length} signal{blocked.length > 1 ? "s" : ""} skipped today</p> : null}
      {last ? (
        <button type="button" className="lastline" onClick={() => onPick(last.trade_id)}>
          <span className="muted">Last</span> <b className="num">{strikeOf(last)}</b> <Side side={last.side} /> <span className="num muted">{String(last.closed_ist || "").slice(11, 16)}</span> <Reason code={last.exit_reason} /> <b className={`num ${tone(last.realized_pnl_inr)}`}>{inr(last.realized_pnl_inr)}</b>
        </button>
      ) : null}
    </section>
  );
}

function RiskKpi({ dd }) {
  const rv = riskView(dd.risk);
  if (!rv) return <div><span>Open now</span><b className="num">{dd.open.length}</b><em>{dd.total.n ?? "—"} trades today · limit not enforced yet today</em></div>;
  return (
    <div className={rv.halted ? "kpi--halt" : ""} data-testid="risk-kpi">
      <span>Open now · risk</span>
      <b className="num">{rv.open ?? "—"} / {rv.maxOpen ?? "—"}</b>
      <em>trades {rv.trades ?? "—"}{rv.maxTrades == null ? " (no cap)" : ` / ${rv.maxTrades}`} · losers {rv.losers ?? "—"} · R01 group {inr(rv.groupNet)}{rv.groupStop ? " (stopped)" : ""}{rv.halted ? ` · ${rv.haltedText}` : ""}</em>
    </div>
  );
}

function Kpis({ snap, dd }) {
  const p = periodNets(snap);
  return (
    <div className="kpis" data-testid="kpis">
      <div><span>Capital now</span><b className="num">{inr(p.capital, { signed: false })}</b><em>start {inr(p.start, { signed: false })} + net P&amp;L</em></div>
      <div><span>Today</span><b className={`num ${tone(dd.total.net)}`}>{inr(dd.total.net)}</b><em>{dd.total.n ?? "—"} trades · after charges</em></div>
      <div><span>Last 5 days</span><b className={`num ${tone(p.week)}`}>{inr(p.week)}</b><em>{p.weekTrades} trades</em></div>
      <div><span>All time</span><b className={`num ${tone(p.total)}`}>{inr(p.total)}</b><em>{p.totalTrades} trades · {CHARGES_LABEL}</em></div>
      <RiskKpi dd={dd} />
    </div>
  );
}

export function LivePage({ snap, dd, conn }) {
  useTick(1000);
  const all = useMemo(() => [...dd.open, ...dd.closed], [dd]);
  const tape = useLtpTape(all);
  const [picked, setPicked] = useState(null);
  const sorted = [...dd.closed].sort((a, b) => (b.closed_ts || 0) - (a.closed_ts || 0));
  const trade = all.find((t) => t.trade_id === picked) || dd.open[0] || sorted[0] || null;
  const L = dd.lists;
  return (
    <div className="page live" data-testid="live-page">
      <Kpis snap={snap} dd={dd} />
      <div className="grid-2">
        <IndexCard und="NIFTY" dd={dd} onPick={setPicked} picked={trade?.trade_id} />
        <IndexCard und="SENSEX" dd={dd} onPick={setPicked} picked={trade?.trade_id} />
      </div>
      <section className="panel">
        <header className="panel__head"><h2>Chart</h2>
          <div className="seg">{[...dd.open, ...sorted.slice(0, 6)].map((t) => (
            <button key={t.trade_id} type="button" className={trade?.trade_id === t.trade_id ? "is-on" : ""} onClick={() => setPicked(t.trade_id)}>{t.underlying} {strikeOf(t)} {t.side}{t.closed_ts == null ? " ●" : ""}</button>
          ))}</div>
        </header>
        <PremiumChart trade={trade} prints={trade ? tape[trade.trade_id] : []} />
      </section>
      <div className="grid-2-1">
        <PnlChart trades={dd.closed} height={220} />
        <section className="panel books">
          <header className="panel__head"><h2>Books today</h2><span className="muted">after charges · {CHARGES_LABEL}</span></header>
          <div className="book"><span>Research book</span><b className={`num ${tone(dd.research.net)}`}>{inr(dd.research.net)}</b><em>{dd.research.trades} trades · charges {inr(dd.research.charges, { signed: false })}</em></div>
          <div className="book"><span>Old MIX book</span><b className={`num ${tone(dd.mix.net)}`}>{inr(dd.mix.net)}</b><em>{dd.mix.trades} trades · charges {inr(dd.mix.charges, { signed: false })}</em></div>
          <div className="book book--total"><span>Desk today</span><b className={`num ${tone(dd.total.net)}`}>{inr(dd.total.net)}</b><em>charges {inr(dd.total.charges, { signed: false })} ({CHARGES_LABEL})</em></div>
          <p className="fine">Rules: max {RULES.maxOpen} open, no daily trade cap on paper, day stops after {RULES.maxLosersPerDay} losers or {inr(RULES.dayLossInr)} ({inr(RULES.dayLossInrR01)} for R01 / B3a), once the engine enforces it. Never opposite sides across NIFTY and SENSEX.</p>
        </section>
      </div>
      <section className="panel">
        <header className="panel__head"><h2>Desk trades today</h2><span className="muted">real paper money · click a row to chart it</span></header>
        <TradeTable rows={sorted} kind="desk" onPick={setPicked} picked={trade?.trade_id} />
      </section>
      <details className="panel details" data-testid="details">
        <summary>Details: shadow, blocked, risk-blocked, duplicates, warnings, data age</summary>
        <h3>Shadow only (not counted){L.parkedNote ? <em className="muted"> · {L.parkedNote}</em> : null}</h3>
        <TradeTable rows={L.parked} kind="shadow" fallback="SHADOW_PARKED" />
        <h3>Blocked signals</h3>
        <TradeTable rows={L.blocked} kind="blocked" fallback="BLOCKED_OPPOSITE_SIDE" />
        <h3>Blocked by risk limit (not traded)</h3>
        <TradeTable rows={L.riskBlocked} kind="blocked" fallback="RISK_BLOCKED" />
        <h3>Duplicates (same contract, not counted)</h3>
        <TradeTable rows={L.dups} kind="blocked" fallback="DUP_SAME_CONTRACT" />
        <h3>Warnings and engine alerts</h3>
        <AlertList alerts={agedAlerts(snap?.alerts)} />
        <h3>Data age</h3>
        <FeedAges rows={feedAges(snap)} />
        <p className="fine">Feed: {conn}</p>
      </details>
      <BackgroundTestBox />
    </div>
  );
}

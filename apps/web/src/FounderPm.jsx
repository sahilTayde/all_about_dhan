import { useEffect, useMemo, useState } from "react";
import { AccountPanel } from "./components/AccountPanel.jsx";
import { AlertBar } from "./components/AlertBar.jsx";
import { AppNav } from "./components/AppNav.jsx";
import { CurrentTrade } from "./components/CurrentTrade.jsx";
import { DecisionTrace } from "./components/DecisionTrace.jsx";
import { DiscardedBook } from "./components/DiscardedBook.jsx";
import { CumulativeChart, LossByStage, ModelScores, PeriodChart, TradesPerDay } from "./components/FounderCharts.jsx";
import { FounderBookPicker } from "./components/FounderBookPicker.jsx";
import { FounderControls } from "./components/FounderControls.jsx";
import { FounderHonestyExam } from "./components/FounderHonestyExam.jsx";
import { FounderRoster } from "./components/FounderRoster.jsx";
import { Header, OfflineBanner } from "./components/Header.jsx";
import { HealthPanel } from "./components/HealthPanel.jsx";
import { MarketPanel } from "./components/MarketPanel.jsx";
import { TradeHistory } from "./components/TradeHistory.jsx";
import { useDeskFeed } from "./lib/v2Feed.js";
import { boardClock, boardSource, derivePaperBoard, fetchFounderLab, holdReason, inr, pct } from "./lib/paperBoard.js";

function Stat({ label, value, hint, tone, className = "" }) {
  return (
    <div className={`fx-stat ${tone ? `fx-stat--${tone}` : ""} ${className}`}>
      <span className="fx-stat__label">{label}</span>
      <strong className={`fx-stat__value ${tone === "up" ? "is-up" : ""} ${tone === "down" ? "is-down" : ""}`}>{value}</strong>
      {hint ? <span className="fx-stat__hint">{hint}</span> : null}
    </div>
  );
}

export function FounderPm() {
  const { snap, conn, latencyMs } = useDeskFeed();
  const [lab, setLab] = useState(null);
  const [picked, setPicked] = useState(null);

  useEffect(() => {
    const ac = new AbortController();
    fetchFounderLab({ signal: ac.signal }).then(setLab).catch(() => {});
    return () => ac.abort();
  }, []);

  const board = snap?.board || null;
  const d = useMemo(() => derivePaperBoard(board, null), [board]);
  const clock = boardClock(board);
  const offline = Boolean(snap?.offline);
  const indexing = snap?.history_complete === false;
  const source = boardSource(board, clock, offline);
  const days = snap?.days || [];
  const liveDay = board?.session_ist_date || clock.ist?.slice(0, 10);
  const day = days.find((x) => x.day === liveDay) || d?.todayDay;
  const paper = (snap?.founder?.agents || []).find((a) => a.id === "paper-loop");
  const current = d?.current;
  const fresh = picked && [...(d?.uniqueOpen || []), ...(d?.uniqueClosed || [])].find((t) => t.trade_id === picked.trade_id);
  const traceRow = fresh || picked || current || d?.uniqueClosed?.[0];

  return (
    <div className="shell shell--founder">
      <AppNav current="/pm" />
      <Header
        title="Founder"
        kicker="Train · compare · do not promote"
        sub="Money, health, models and how each paper fill was decided. PAPER only."
        sourceLabel={source}
      />
      <div className="desk-refresh">
        <p className="desk-sub" title={clock.writtenIst ? `Board written ${clock.writtenIst}` : undefined}>
          Tape as of {clock.label}
          {offline ? " · static mock (API offline)" : clock.replay ? " · replay of a past session" : ""} · {conn === "live" ? "live push" : conn}
          {latencyMs != null ? ` · update ${latencyMs} ms` : ""} · orders refused · NO_PROMOTE
        </p>
        <div className="fx-health">
          <span className={`cleanup-pill ${paper?.alive ? "done" : "pending"}`} title="Paper market-hours loop (PID)">
            paper loop {paper ? (paper.alive ? "ON" : "OFF") : "unknown"}
          </span>
          <span className="cleanup-pill pending">book: {source}</span>
        </div>
      </div>
      {offline ? <OfflineBanner /> : null}
      <AlertBar alerts={snap?.alerts} conn={conn} />

      {!d ? (
        <p className="muted">Loading founder book…</p>
      ) : (
        <div className="grid">
          <div className="fx-stats founder-kpis span-12">
            <Stat label="Trades today" value={String(day?.n ?? d.uniqueClosed.length)} hint={liveDay || "—"} />
            <Stat label="Win rate today" value={pct(day?.n ? (day.wins / day.n) * 100 : d.uniqueWr)} hint="net ₹ > 0 after charges" />
            <Stat label="Profit today" value={inr(d.todayDay?.profit)} hint="winning fills" tone="up" />
            <Stat label="Loss today" value={inr(d.todayDay?.loss)} hint="losing fills" tone="down" />
            <Stat label="Net today" value={inr(day?.net)} hint={day ? `charges ${inr(day.charges, { signed: false })}` : "no fills"} tone={Number(day?.net) >= 0 ? "up" : "down"} />
            <Stat
              label="Net all days"
              value={indexing ? "Indexing history…" : inr(snap?.account?.net_inr)}
              hint={indexing ? "model log still loading" : snap?.account?.n_days ? `${snap.account.n_days} recorded days` : "API offline"}
              tone={indexing ? "" : Number(snap?.account?.net_inr) >= 0 ? "up" : "down"}
              className={indexing ? "needs-history" : ""}
            />
          </div>

          <div className="span-4">
            <HealthPanel rows={snap?.health} founder={snap?.founder} conn={conn} />
          </div>
          <div className="span-4">
            <AccountPanel account={snap?.account} today={day} founderBook={snap?.founder_book} indexing={indexing} />
          </div>
          <div className="span-4 stack">
            <FounderBookPicker />
          </div>
          <div className="span-12">
            <FounderControls />
          </div>

          <div className="span-6">
            <CumulativeChart days={days} todayTrades={d.uniqueClosed} indexing={indexing} />
          </div>
          <div className="span-6">
            <PeriodChart days={days} indexing={indexing} />
          </div>
          <div className="span-4">
            <TradesPerDay days={days} indexing={indexing} />
          </div>
          <div className="span-8">
            <ModelScores days={days} indexing={indexing} />
          </div>

          <div className="span-4">
            <LossByStage days={days} exam={snap?.exam} indexing={indexing} />
          </div>
          <div className="span-5">
            <CurrentTrade t={current} last={d.uniqueClosed[0]} clock={clock} hold={current ? null : holdReason(board, snap?.founder_book, snap?.risk_halt, offline)} title="Now open" />
          </div>
          <div className="span-3">
            <MarketPanel regimes={d.regimes} />
          </div>

          <div className="span-12">
            <DecisionTrace
              refreshKey={traceRow?.last_updated_ts}
              tradeId={traceRow?.trade_id}
              label={traceRow ? `${traceRow.underlying} ${traceRow.side} ${traceRow.atm_strike ?? ""} · ${String(traceRow.opened_ist || "").slice(11, 19)}` : null}
            />
          </div>

          <section className="panel span-12">
            <h2>Compare fills</h2>
            <TradeHistory
              indexing={indexing}
              rows={[...(d.uniqueOpen || []), ...d.uniqueClosed]}
              days={days}
              liveDay={board?.session_ist_date}
              clock={clock}
              onSelect={setPicked}
              selectedId={traceRow?.trade_id}
            />
          </section>

          <div className="span-12">
            <FounderHonestyExam exam={snap?.exam} />
          </div>
          <div className="span-12">
            <DiscardedBook rows={d.discardedRows} actorCounts={d.actorCounts} />
          </div>
          <div className="span-12">
            <FounderRoster catalog={lab?.catalog} confirmKill={lab?.confirm_kill} />
          </div>
        </div>
      )}
      <footer className="page-foot muted small">
        <span>Last update applied in {latencyMs ?? "—"} ms · one push stream, no per-panel polling.</span>
        <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">
          Charts by TradingView Lightweight Charts
        </a>
      </footer>
    </div>
  );
}

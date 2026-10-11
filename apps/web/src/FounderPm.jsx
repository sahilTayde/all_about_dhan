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
import { LlmShadowPanel } from "./components/LlmShadowPanel.jsx";
import { TradeHistory } from "./components/TradeHistory.jsx";
import { ActionBar } from "./desk/components/ActionBar.jsx";
import { HealthStrip } from "./desk/components/HealthStrip.jsx";
import { Heatmap } from "./desk/components/Heatmap.jsx";
import { OpenPositions } from "./desk/components/OpenPositions.jsx";
import { Skeleton } from "./desk/components/Skeleton.jsx";
import { TradePipeline } from "./desk/components/TradePipeline.jsx";
import "./desk/desk.css";
import { useDeskFeed } from "./lib/v2Feed.js";
import { boardClock, boardSource, derivePaperBoard, fetchFounderLab, holdReason, inr, pct } from "./lib/paperBoard.js";
import { replayAlerts } from "./lib/plainWords.js";
import { buildStrategyCards } from "./lib/strategyBoard.js";

function Stat({ label, value, hint, tone, className = "" }) {
  return (
    <div className={`fx-stat ${tone ? `fx-stat--${tone}` : ""} ${className}`}>
      <span className="fx-stat__label">{label}</span>
      <strong className={`fx-stat__value ${tone === "up" ? "is-up" : ""} ${tone === "down" ? "is-down" : ""}`}>{value}</strong>
      {hint ? <span className="fx-stat__hint">{hint}</span> : null}
    </div>
  );
}

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "books", label: "Books" },
  { id: "research", label: "Research" },
  { id: "ops", label: "Ops" },
  { id: "advanced", label: "Advanced" },
];

export function FounderPm() {
  const { snap, conn, latencyMs } = useDeskFeed();
  const [lab, setLab] = useState(null);
  const [picked, setPicked] = useState(null);
  const [tab, setTab] = useState("overview");

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
  const cards = useMemo(
    () => buildStrategyCards(board, { uniqueClosed: d?.uniqueClosed, uniqueOpen: d?.uniqueOpen }),
    [board, d],
  );
  const paperCards = cards.filter((c) => !c.shadow);
  const best = [...paperCards].sort((a, b) => (b.net || 0) - (a.net || 0))[0];
  const worst = [...paperCards].sort((a, b) => (a.net || 0) - (b.net || 0))[0];
  const week = days.slice(0, 5).reduce((s, x) => s + (x.net || 0), 0);
  const month = days.reduce((s, x) => s + (x.net || 0), 0);
  const vs = best?.vsRandom;
  const alerts = replayAlerts(snap?.alerts, clock.replay);

  return (
    <div className="shell shell--founder founder-shell" data-testid="founder-shell">
      <div className="desk-sticky">
        <AppNav current="/pm" />
        <Header
          title="Founder"
          kicker="Train · compare"
          sub="Money, health, and books. Paper only."
          sourceLabel={source}
        />
        <HealthStrip rows={snap?.health} conn={conn} replay={clock.replay} />
        <div className="desk-refresh">
          <p className="desk-sub">
            Tape as of {clock.label}
            {offline ? " · waiting for the live desk" : clock.replay ? " · replay of a past session" : ""} · {conn === "live" ? "live push" : conn}
            {latencyMs != null ? ` · update ${latencyMs} ms` : ""}
          </p>
        </div>
        <div className="desk-tabs" role="tablist" aria-label="Founder pages">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              className={tab === t.id ? "is-on" : ""}
              data-testid={t.id === "advanced" ? "advanced-toggle" : `founder-tab-${t.id}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <ActionBar
          onRefresh={() => window.location.reload()}
          onCsv={() => {}}
          onToggleAlerts={() => document.querySelector(".alert-bar .chip-btn")?.click()}
          onPause={() => {}}
          onExit={() => {}}
          onReview={() => {}}
        />
      </div>
      {offline ? <OfflineBanner /> : null}
      <AlertBar alerts={alerts} conn={conn} />

      {!d ? (
        <Skeleton lines={6} />
      ) : tab === "overview" ? (
        <div className="founder-overview">
          <TradePipeline board={board} open={d.uniqueOpen} closed={d.uniqueClosed} />
          <OpenPositions
            rows={d.uniqueOpen}
            clock={clock}
            last={d.uniqueClosed?.[0]}
            onSelect={setPicked}
            selectedId={traceRow?.trade_id}
            regimes={d.regimes}
          />
          <div className="fx-stats founder-kpis">
            <Stat label="Net today" value={inr(day?.net)} hint="after costs" tone={Number(day?.net) >= 0 ? "up" : "down"} />
            <Stat label="Net week" value={inr(week)} hint="last sessions" />
            <Stat
              label="Net month"
              value={indexing ? "Indexing history…" : inr(month)}
              hint={indexing ? "model log still loading" : `${days.length} days`}
              className={indexing ? "needs-history" : ""}
            />
            <Stat label="Win vs random" value={vs == null ? "pending" : `${vs > 0 ? "+" : ""}${Number(vs).toFixed(1)} pt`} hint="shadow scoreboard" />
            <Stat label="Best / worst" value={`${best?.name || "—"} / ${worst?.name || "—"}`} hint={inr(best?.net)} />
            <Stat label="Max DD" value={best?.maxDd == null ? "—" : inr(-Math.max(...paperCards.map((c) => c.maxDd || 0)))} tone="down" />
          </div>
          <Heatmap cards={cards} trades={d.uniqueClosed} />
          <section className="widget">
            <header className="widget__head">
              <h2>Promote / demote</h2>
              <span className="muted small">Read-only from badge rules</span>
            </header>
            <ul className="suggest-list">
              {paperCards.map((c) => (
                <li key={c.id}>
                  <strong>{c.name}</strong>
                  <span className={`slot-badge slot-badge--${String(c.badge).toLowerCase()}`}>
                    {c.badge} n={c.nFilled || 0}
                  </span>
                  <span className="muted small">{c.badge === "TRADE" ? "Keep watching the thick book." : c.badge === "DROP" ? "Losing at n≥30." : "Thin or close — watch."}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : tab === "books" ? (
        <section className="widget panel-scroll" data-testid="founder-books">
          <header className="widget__head">
            <h2>Open now</h2>
          </header>
          <CurrentTrade t={current} last={d.uniqueClosed[0]} clock={clock} hold={current ? null : holdReason(board, snap?.founder_book, snap?.risk_halt, offline)} title="Now open" />
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
      ) : tab === "research" ? (
        <section className="widget panel-scroll" data-testid="research-feed">
          <header className="widget__head">
            <h2>Research feed</h2>
          </header>
          <LlmShadowPanel compare={snap?.llm_shadow_compare} />
          <ul className="suggest-list">
            {paperCards.map((c) => (
              <li key={c.id}>
                <strong>{c.name}</strong>
                <span className={`slot-badge slot-badge--${String(c.badge).toLowerCase()}`}>{c.badge}</span>
                <span className="muted small">n={c.nFilled || 0} · {c.vsRandom == null ? "vs random pending" : `${c.vsRandom > 0 ? "+" : ""}${Number(c.vsRandom).toFixed(1)} pt`}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : tab === "ops" ? (
        <div className="founder-ops">
          <HealthPanel rows={snap?.health} founder={snap?.founder} conn={conn} />
          <AccountPanel account={snap?.account} today={day} founderBook={snap?.founder_book} indexing={indexing} />
          <p className="muted small">
            Paper loop {paper ? (paper.alive ? "ON" : "OFF") : "unknown"} · token and tape sit in the health list.
          </p>
        </div>
      ) : (
        <div className="grid founder-advanced" data-testid="advanced-panel">
          <div className="span-12">
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
          <div className="span-3">
            <MarketPanel regimes={d.regimes} />
          </div>
          <div className="span-12">
            <DecisionTrace
              refreshKey={traceRow?.last_updated_ts}
              tradeId={traceRow?.trade_id}
              label={traceRow ? `${traceRow.underlying} ${traceRow.side} ${traceRow.atm_strike ?? ""}` : null}
            />
          </div>
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
    </div>
  );
}

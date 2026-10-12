import { useEffect, useMemo, useState } from "react";
import { AccountPanel } from "./components/AccountPanel.jsx";
import { TopBar } from "./components/TopBar.jsx";
import { CumulativeChart, ModelScores, PeriodChart, TradesPerDay } from "./components/FounderCharts.jsx";
import { FounderHonestyExam } from "./components/FounderHonestyExam.jsx";
import { FounderRoster } from "./components/FounderRoster.jsx";
import { OfflineBanner } from "./components/Header.jsx";
import { LlmShadowPanel } from "./components/LlmShadowPanel.jsx";
import "./desk/desk.css";
import "./desk/pro.css";
import { deskDay, inr, statusLight, strategyName, tone } from "./lib/deskModel.js";
import { fetchFounderLab } from "./lib/paperBoard.js";
import { useDeskFeed } from "./lib/v2Feed.js";

const TABS = [
  { id: "money", label: "Money" },
  { id: "research", label: "Research" },
];

/** /pm: money and research only. Live trades live on /desk, controls on /ops. */
export function FounderPm() {
  const { snap, conn } = useDeskFeed();
  const [lab, setLab] = useState(null);
  const [tab, setTab] = useState("money");
  useEffect(() => {
    const ac = new AbortController();
    fetchFounderLab({ signal: ac.signal }).then(setLab).catch(() => {});
    return () => ac.abort();
  }, []);
  const dd = useMemo(() => deskDay(snap), [snap]);
  const days = snap?.days || [];
  const indexing = snap?.history_complete === false;
  const week = days.slice(0, 5).reduce((s, x) => s + (x.net || 0), 0);
  const today = days.find((x) => x.day === dd.day);
  const light = snap ? statusLight(dd, conn, Boolean(snap?.offline)) : { tone: "amber", text: "Connecting…" };

  return (
    <div className="term" data-testid="founder-shell">
      <TopBar path="/pm" light={light} dd={snap ? dd : null} snap={snap} conn={conn} />
      <main className="term__main page">
      <header className="pg-head">
        <div>
          <h1>Money &amp; research</h1>
          <p className="muted">Where the money went, and what the research says. Paper only.</p>
        </div>
        <div className="desk-tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} className={tab === t.id ? "is-on" : ""} data-testid={`founder-tab-${t.id}`} onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </div>
      </header>
      {snap?.offline ? <OfflineBanner /> : null}
      {!snap ? <p className="muted">Loading…</p> : tab === "money" ? (
        <div className="money">
          <section className="panel">
            <p className="money__line">Capital now <strong className="num">{inr(snap?.account?.equity_inr, { signed: false })}</strong> (start {inr(snap?.account?.starting_capital_inr, { signed: false })} + net) · Today <strong className={tone(dd.total.net)}>{inr(dd.total.net)}</strong> · last 5 days <strong className={tone(week)}>{inr(week)}</strong> · all time <strong className={tone(snap?.account?.net_inr)}>{inr(snap?.account?.net_inr)}</strong>{indexing ? " (still reading the log)" : ""}</p>
            <ul className="day-list">
              {Object.entries(today?.by_book || {}).map(([id, b]) => (
                <li key={id}><span title={id}>{strategyName(id)}</span><span className="muted">{b.n} trades · {b.wins} won</span><strong className={tone(b.net)}>{inr(b.net)}</strong></li>
              ))}
            </ul>
          </section>
          <AccountPanel account={snap?.account} today={today} founderBook={snap?.founder_book} indexing={indexing} />
          <div className="grid2">
            <CumulativeChart days={days} todayTrades={dd.closed} indexing={indexing} />
            <PeriodChart days={days} indexing={indexing} />
          </div>
          <TradesPerDay days={days} indexing={indexing} />
        </div>
      ) : (
        <div className="research">
          <ModelScores days={days} indexing={indexing} />
          <LlmShadowPanel compare={snap?.llm_shadow_compare} />
          <FounderHonestyExam exam={snap?.exam} />
          <FounderRoster catalog={lab?.catalog} confirmKill={lab?.confirm_kill} />
        </div>
      )}
      </main>
    </div>
  );
}

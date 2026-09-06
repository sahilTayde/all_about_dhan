import { useEffect, useState } from "react";
import { apiMode, fetchPaperDesk } from "./lib/signalApi.js";
import { subscribePaperSignals } from "./lib/liveSignals.js";
import { Header } from "./components/Header.jsx";
import { UnderlyingPicker } from "./components/UnderlyingPicker.jsx";
import { MarketSentiment } from "./components/MarketSentiment.jsx";
import { CasPanel } from "./components/CasPanel.jsx";
import { SignalCard } from "./components/SignalCard.jsx";
import { TookTrade } from "./components/TookTrade.jsx";
import { SystemOutcome } from "./components/SystemOutcome.jsx";
import { TodaysBook } from "./components/TodaysBook.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { LegendDialog } from "./components/LegendDialog.jsx";

const EMPTY_FILL = { lots: "", spot: "", pnl: "" };

export default function App() {
  const [desk, setDesk] = useState(null);
  const [error, setError] = useState(null);
  const [underlying, setUnderlying] = useState("NIFTY");
  const [tookTrade, setTookTrade] = useState(null);
  const [userFill, setUserFill] = useState(EMPTY_FILL);
  const [legendOpen, setLegendOpen] = useState(false);
  const [livePaper, setLivePaper] = useState(null);

  useEffect(() => {
    return subscribePaperSignals(setLivePaper);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchPaperDesk()
      .then((data) => {
        if (cancelled) return;
        setDesk(data);
        const first = data.underlyings?.[0] || "NIFTY";
        setUnderlying(first);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleUnderlying(next) {
    setUnderlying(next);
    setTookTrade(null);
    setUserFill(EMPTY_FILL);
  }

  function handleFill(key, value) {
    setUserFill((prev) => ({ ...prev, [key]: value }));
  }

  const mockSignal = desk?.signals?.[underlying];
  const live = livePaper?.underlyings?.[underlying];
  const signal = live && mockSignal
    ? {
        ...mockSignal,
        side: live.side,
        strike: live.strike ?? "",
        entry: live.entry ?? "",
        stop: live.stop ?? "",
        target: live.target ?? "",
        staged: {
          state: live.state,
          headline: live.headline,
          note: live.note,
        },
        customer: { headline: live.headline, note: live.note },
        lifecycle: {},
        ticket: live.ticket,
        confidence: live.confidence,
      }
    : mockSignal;
  const sourceLabel = live
    ? "LIVE PAPER"
    : apiMode() === "remote"
      ? "API"
      : "MOCK";
  const confidence =
    signal?.confidence ||
    live?.confidence || {
      score_pct: 0,
      band: "none",
      label: "No active lean",
      eligible: [],
      why: "Connect live paper or wait for a lean.",
      fairness:
        "Agreement score only. Not a win rate. Not a fill promise. You decide.",
    };
  const ticket = signal?.ticket || live?.ticket || null;

  if (error) {
    return (
      <div className="shell">
        <Header sourceLabel="ERROR" />
        <p className="error-banner">{error}</p>
        <Disclaimer />
      </div>
    );
  }

  if (!desk || !signal) {
    return (
      <div className="shell">
        <Header sourceLabel={sourceLabel} />
        <p className="muted">Loading desk…</p>
      </div>
    );
  }

  const sentiment = desk.sentiment?.byUnderlying?.[underlying] || {};

  return (
    <div className="shell">
      <Header sourceLabel={sourceLabel} onInfo={() => setLegendOpen(true)} />

      <UnderlyingPicker
        underlyings={desk.underlyings}
        value={underlying}
        onChange={handleUnderlying}
      />

      <MarketSentiment
        windows={desk.sentiment?.windows}
        values={sentiment}
        source={desk.sentiment?.source || desk.meta?.source}
      />

      <CasPanel cas={desk.cas} underlying={underlying} />

      <SignalCard
        signal={signal}
        confidence={confidence}
        ticket={ticket}
      />

      <div className="desk-split">
        <TookTrade
          value={tookTrade}
          onChange={setTookTrade}
          fill={userFill}
          onFillChange={handleFill}
        />
        <SystemOutcome
          tookTrade={tookTrade}
          outcome={signal.systemOutcome}
          lifecycle={signal.lifecycle}
          userFill={userFill}
        />
      </div>

      <TodaysBook book={desk.todaysBook} />

      <p className="as-of muted">
        As of {desk.meta?.asOf ?? "—"} · {desk.meta?.note}
      </p>

      <Disclaimer />
      <LegendDialog open={legendOpen} onClose={() => setLegendOpen(false)} />

      {/* TODO(charts): optional premium / spot panel beside levels — later. */}
      {/* TODO(signals): stack more than one active signal on this desk. */}
      {/* TODO(api): GET /paper/signal should include sentiment + todaysBook + customer copy. */}
      {/* TODO(jobs): recon job stamps lifecycle.outcome — not live Dhan from this UI. */}
    </div>
  );
}

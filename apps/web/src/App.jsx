import { useEffect, useState } from "react";
import { apiMode, fetchPaperDesk } from "./lib/signalApi.js";
import { subscribePaperSignals } from "./lib/liveSignals.js";
import { customerStatus, isWaitingStatus } from "./lib/status.js";
import { Header } from "./components/Header.jsx";
import { UnderlyingPicker } from "./components/UnderlyingPicker.jsx";
import { MarketSentiment } from "./components/MarketSentiment.jsx";
import { CasPanel } from "./components/CasPanel.jsx";
import { SignalCard } from "./components/SignalCard.jsx";
import { IndexChart } from "./components/IndexChart.jsx";
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
  // LIVE PAPER levels win when present. Index proxy never fills premium slots.
  const signal = live && mockSignal
    ? {
        ...mockSignal,
        side: live.side,
        strike: live.strike != null && live.strike !== "" ? live.strike : "",
        entry: live.entry != null && live.entry !== "" ? live.entry : "",
        stop: live.stop != null && live.stop !== "" ? live.stop : "",
        target: live.target != null && live.target !== "" ? live.target : "",
        underlying_spot:
          live.underlying_spot ?? live.spot ?? live.ticket?.underlying_spot ?? "",
        spot: live.underlying_spot ?? live.spot ?? live.ticket?.underlying_spot ?? "",
        staged: {
          state: live.state,
          headline: live.headline,
          note: live.note,
        },
        customer: { headline: live.headline, note: live.note },
        lifecycle: mockSignal.lifecycle || {},
        ticket: live.ticket || {
          unit: "OPTION_PREMIUM",
          levels_ready: false,
          levels_note:
            "LIVE PAPER lean without bound option premium — DATA_INSUFFICIENT. Refusing index-as-premium.",
        },
        confidence: live.confidence,
        chart: mockSignal.chart,
        confidenceDetail: mockSignal.confidenceDetail,
        top_veto_reasons:
          live.top_veto_reasons ||
          mockSignal.top_veto_reasons ||
          live.vetoes ||
          mockSignal.vetoes,
        vetoes: live.vetoes || mockSignal.vetoes,
      }
    : mockSignal;
  const sourceLabel = live
    ? "LIVE PAPER"
    : apiMode() === "remote"
      ? "API"
      : desk?.meta?.source === "fixture" || desk?.meta?.placeholder
        ? "FIXTURE"
        : "MOCK";
  const status = customerStatus(signal);
  const waiting = isWaitingStatus(status);
  const confidence =
    waiting
      ? {
          score_pct: null,
          band: "none",
          label: "Waiting for next signal",
          eligible: [],
          why_bullets: [],
          fairness:
            "Agreement score only when a lean is active. Not a win rate.",
        }
      : signal?.confidence ||
        live?.confidence || {
          score_pct: 0,
          band: "none",
          label: "No active lean",
          eligible: [],
          why: "Connect live paper or wait for a lean.",
          fairness:
            "Agreement score only. Not a win rate. Not a fill promise. You decide.",
        };
  const ticket = waiting ? null : signal?.ticket || live?.ticket || null;

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
  const chart = signal.chart || desk.charts?.[underlying] || null;

  return (
    <div className="shell shell--customer">
      <Header
        sourceLabel={sourceLabel}
        onInfo={() => setLegendOpen(true)}
        title="Paper desk"
        sub="One suggested ticket · MOCK / PAPER · not advice · orders refused"
      />

      <UnderlyingPicker
        underlyings={desk.underlyings}
        value={underlying}
        onChange={handleUnderlying}
      />

      <SignalCard
        signal={signal}
        confidence={confidence}
        ticket={ticket}
        deskMeta={desk?.meta}
      />

      <IndexChart chart={chart} signal={signal} status={status} />

      {!waiting && (
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
      )}

      <TodaysBook book={desk.todaysBook} fixtureBook={desk.fixtureBook} />

      <details className="desk-context">
        <summary>Desk context (sentiment · close auction) — not the ticket</summary>
        <MarketSentiment
          windows={desk.sentiment?.windows}
          values={sentiment}
          source={desk.sentiment?.source || desk.meta?.source}
        />
        <CasPanel cas={desk.cas} underlying={underlying} />
      </details>

      <p className="as-of muted">
        As of {desk.meta?.asOf ?? "—"} · {desk.meta?.note}
      </p>

      <Disclaimer />
      <LegendDialog open={legendOpen} onClose={() => setLegendOpen(false)} />
    </div>
  );
}

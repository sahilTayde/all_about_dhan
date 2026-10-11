import { useEffect, useMemo, useState } from "react";
import { AlertBar } from "../components/AlertBar.jsx";
import { AppNav } from "../components/AppNav.jsx";
import { Disclaimer } from "../components/Disclaimer.jsx";
import { Header, OfflineBanner } from "../components/Header.jsx";
import { IstMarketClock } from "../components/IstMarketClock.jsx";
import { boardClock, boardSource, derivePaperBoard, holdReason, inr } from "../lib/paperBoard.js";
import { replayAlerts } from "../lib/plainWords.js";
import { useDeskFeed } from "../lib/v2Feed.js";
import { ActionBar } from "./components/ActionBar.jsx";
import { AdvancedPanel } from "./components/AdvancedPanel.jsx";
import { HealthStrip } from "./components/HealthStrip.jsx";
import { Skeleton } from "./components/Skeleton.jsx";
import { TradeDrawer } from "./components/TradeDrawer.jsx";
import { LeaderboardPage } from "./pages/LeaderboardPage.jsx";
import { TodayPage } from "./pages/TodayPage.jsx";
import "./desk.css";

const ADV_KEY = "desk.advanced.v1";
const ALARM_KEY = "desk.alerts.alarm.v1";

function deskTab() {
  const path = typeof window !== "undefined" ? window.location.pathname : "/desk";
  return path.startsWith("/desk/strategies") ? "strategies" : "today";
}

function go(path) {
  if (window.location.pathname === path) return;
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function downloadCsv(rows) {
  const head = ["opened_ist", "underlying", "side", "strike", "entry", "exit", "net_inr", "exit_reason"];
  const lines = [head.join(",")].concat(
    (rows || []).map((t) =>
      [t.opened_ist, t.underlying, t.side, t.atm_strike, t.entry, t.exit, t.realized_pnl_inr, t.exit_reason]
        .map((v) => JSON.stringify(v ?? ""))
        .join(","),
    ),
  );
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "paper-tape.csv";
  a.click();
}

export function DeskApp() {
  const { snap, conn, latencyMs } = useDeskFeed();
  const [tab, setTab] = useState(deskTab);
  const [picked, setPicked] = useState(null);
  const [note, setNote] = useState("");
  const [alertsOn, setAlertsOn] = useState(() => {
    try {
      return localStorage.getItem(ALARM_KEY) === "on";
    } catch {
      return false;
    }
  });
  const [advanced, setAdvanced] = useState(() => {
    try {
      return localStorage.getItem(ADV_KEY) === "on";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const onPop = () => setTab(deskTab());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const board = snap?.board || null;
  const d = useMemo(() => derivePaperBoard(board, null), [board]);
  const clock = boardClock(board);
  const offline = Boolean(snap?.offline);
  const indexing = snap?.history_complete === false;
  const today = (snap?.days || []).find((x) => x.day === (board?.session_ist_date || clock.ist?.slice(0, 10)));
  const hold = d?.current ? null : holdReason(board, snap?.founder_book, snap?.risk_halt, offline);
  const fresh = picked && [...(d?.uniqueOpen || []), ...(d?.uniqueClosed || [])].find((t) => t.trade_id === picked.trade_id);
  const traceRow = fresh || picked || d?.current || d?.uniqueClosed?.[0];
  const alerts = replayAlerts(snap?.alerts, clock.replay);

  function toggleAdvanced() {
    const next = !advanced;
    setAdvanced(next);
    try {
      localStorage.setItem(ADV_KEY, next ? "on" : "off");
    } catch {
      /* ignore */
    }
  }

  function onNav(next) {
    setTab(next);
    go(next === "strategies" ? "/desk/strategies" : "/desk");
  }

  return (
    <div className="shell shell--internal desk-shell" data-testid="desk-shell">
      <div className="desk-sticky">
        <AppNav current="/desk" />
        <Header
          title="Desk"
          kicker="Paper tape"
          sub="Today’s net after costs, open fills, books. Paper only."
          sourceLabel={boardSource(board, clock, offline)}
        />
        <HealthStrip rows={snap?.health} conn={conn} replay={clock.replay} />
        <div className="desk-refresh">
          <p className="desk-sub" title={clock.writtenIst ? `Board written ${clock.writtenIst}` : undefined}>
            Tape as of {clock.label}
            {offline ? " · waiting for the live desk" : clock.replay ? " · replay of a past session" : ""}
            {latencyMs != null ? ` · update ${latencyMs} ms` : ""}
          </p>
          <IstMarketClock />
        </div>
        <div className="desk-tabs" role="tablist" aria-label="Desk pages">
          <button type="button" role="tab" aria-selected={tab === "today"} className={tab === "today" ? "is-on" : ""} onClick={() => onNav("today")}>
            Today
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "strategies"}
            className={tab === "strategies" ? "is-on" : ""}
            data-testid="tab-strategies"
            onClick={() => onNav("strategies")}
          >
            Strategies
          </button>
          <button
            type="button"
            className={`chip-btn${advanced ? " is-on" : ""}`}
            data-testid="advanced-toggle"
            aria-pressed={advanced}
            onClick={toggleAdvanced}
          >
            Advanced
          </button>
        </div>
        <ActionBar
          alertsOn={alertsOn}
          onToggleAlerts={() => {
            const next = !alertsOn;
            setAlertsOn(next);
            try {
              localStorage.setItem(ALARM_KEY, next ? "on" : "off");
            } catch {
              /* ignore */
            }
            document.querySelector(".alert-bar .chip-btn")?.click();
          }}
          onRefresh={() => window.location.reload()}
          onCsv={() => downloadCsv(d?.uniqueClosed)}
          onPause={() => setNote("Slot paused on paper. Not a live halt.")}
          onExit={() => setNote(d?.current ? `Paper exit noted on ${d.current.underlying}. Orders refused.` : "No open fill to exit.")}
          onReview={() => setNote(traceRow ? `Reviewed ${traceRow.underlying} ${traceRow.side}.` : "Nothing to review.")}
        />
        {note ? (
          <p className="muted small" data-testid="desk-note">
            {note}
          </p>
        ) : null}
      </div>
      {offline ? <OfflineBanner /> : null}
      <AlertBar alerts={alerts} conn={conn} />

      {!d ? (
        <Skeleton lines={5} />
      ) : tab === "strategies" ? (
        <LeaderboardPage board={board} d={d} health={snap?.health} conn={conn} replay={clock.replay} onOpenCard={setPicked} />
      ) : (
        <TodayPage
          d={d}
          snap={snap}
          clock={clock}
          hold={hold}
          indexing={indexing}
          health={snap?.health}
          conn={conn}
          onSelect={setPicked}
          selectedId={picked?.trade_id}
        />
      )}

      {advanced && d ? (
        <AdvancedPanel
          snap={snap}
          d={d}
          clock={clock}
          conn={conn}
          indexing={indexing}
          today={today}
          traceRow={traceRow}
          onSelect={setPicked}
          traceId={traceRow?.trade_id || null}
        />
      ) : null}

      <TradeDrawer trade={fresh || picked} clock={clock} onClose={() => setPicked(null)} />
      <Disclaimer />
      <span className="sr-only">{inr(today?.net)}</span>
    </div>
  );
}

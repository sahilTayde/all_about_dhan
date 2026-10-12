import { useEffect, useMemo, useState } from "react";
import { AppNav } from "../components/AppNav.jsx";
import { Disclaimer } from "../components/Disclaimer.jsx";
import { OfflineBanner } from "../components/Header.jsx";
import { IstMarketClock } from "../components/IstMarketClock.jsx";
import { deskDay, statusLight } from "../lib/deskModel.js";
import { useDeskFeed } from "../lib/v2Feed.js";
import { HistoryPage } from "../pages/HistoryPage.jsx";
import { LivePage } from "../pages/LivePage.jsx";
import { OpsPage } from "../pages/OpsPage.jsx";
import { StrategiesPage } from "../pages/StrategiesPage.jsx";
import { Skeleton } from "./components/Skeleton.jsx";
import "./desk.css";
import "./redesign.css";

const TITLES = {
  live: ["Live trade", "What is open now and today's result."],
  history: ["History", "Past trades and the account over time."],
  strategies: ["Strategies", "How each strategy is doing today."],
  ops: ["Ops", "Alerts, health, trade trace and paper controls."],
};

function pageOf(path) {
  if (path.startsWith("/ops")) return "ops";
  if (path.startsWith("/desk/history")) return "history";
  if (path.startsWith("/desk/strategies")) return "strategies";
  return "live";
}

/** One feed, four pages: /desk, /desk/history, /desk/strategies, /ops. */
export function DeskApp() {
  const { snap, conn } = useDeskFeed();
  const [path, setPath] = useState(() => window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const page = pageOf(path);
  const offline = Boolean(snap?.offline);
  const dd = useMemo(() => deskDay(snap), [snap]);
  const light = snap ? statusLight(dd, conn, offline) : { tone: "amber", text: "Connecting…" };
  const [title, sub] = TITLES[page];
  const asOf = String(snap?.board?.as_of_ist || "").slice(11, 19);

  return (
    <div className="shell rd-shell" data-testid="desk-shell">
      <AppNav current={path} light={light} />
      <header className="rd-head">
        <div>
          <h1>{title}</h1>
          <p className="muted">{sub}{asOf ? ` Data as of ${asOf} IST.` : ""}</p>
        </div>
        <IstMarketClock />
      </header>
      {offline ? <OfflineBanner /> : null}
      {!snap ? <Skeleton lines={5} /> : page === "live" ? <LivePage snap={snap} dd={dd} conn={conn} /> : page === "history" ? <HistoryPage snap={snap} dd={dd} /> : page === "strategies" ? <StrategiesPage snap={snap} dd={dd} /> : <OpsPage snap={snap} dd={dd} conn={conn} />}
      <Disclaimer />
    </div>
  );
}

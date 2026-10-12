import { useEffect, useMemo, useState } from "react";
import { Disclaimer } from "../components/Disclaimer.jsx";
import { OfflineBanner } from "../components/Header.jsx";
import { TopBar } from "../components/TopBar.jsx";
import { deskDay, statusLight } from "../lib/deskModel.js";
import { useDeskFeed } from "../lib/v2Feed.js";
import { HistoryPage } from "../pages/HistoryPage.jsx";
import { LivePage } from "../pages/LivePage.jsx";
import { OpsPage } from "../pages/OpsPage.jsx";
import { SignalsPage } from "../pages/SignalsPage.jsx";
import { StrategiesPage } from "../pages/StrategiesPage.jsx";
import { Skeleton } from "./components/Skeleton.jsx";
import "./desk.css";
import "./pro.css";

const PAGES = {
  "/desk": LivePage,
  "/desk/signals": SignalsPage,
  "/desk/history": HistoryPage,
  "/desk/strategies": StrategiesPage,
  "/ops": OpsPage,
};

/** One feed for the desk pages; each page has one job. */
export function DeskApp() {
  const { snap, conn } = useDeskFeed();
  const [path, setPath] = useState(() => window.location.pathname.replace(/\/+$/, "") || "/desk");
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname.replace(/\/+$/, ""));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const Page = PAGES[path] || LivePage;
  const dd = useMemo(() => deskDay(snap), [snap]);
  const light = snap ? statusLight(dd, conn, Boolean(snap?.offline)) : { tone: "amber", text: "Connecting…" };
  return (
    <div className="term" data-testid="desk-shell">
      <TopBar path={path} light={light} dd={snap ? dd : null} snap={snap} conn={conn} />
      <main className="term__main">
        {snap?.offline ? <OfflineBanner /> : null}
        {!snap ? <Skeleton lines={5} /> : <Page snap={snap} dd={dd} conn={conn} />}
        <Disclaimer />
      </main>
    </div>
  );
}

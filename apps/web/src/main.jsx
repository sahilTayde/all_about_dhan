import React, { Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

// One chunk per page: Desk never downloads the chart library the Founder and Customer pages use.
const InternalDesk = lazy(() => import("./InternalDesk.jsx").then((m) => ({ default: m.InternalDesk })));
const FounderPm = lazy(() => import("./FounderPm.jsx").then((m) => ({ default: m.FounderPm })));
const CustomerApp = lazy(() => import("./App.jsx"));
const CleanupCanvas = lazy(() => import("./CleanupCanvas.jsx").then((m) => ({ default: m.CleanupCanvas })));

function usePathname() {
  const [path, setPath] = useState(() => window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  return path;
}

function Page() {
  const path = usePathname();
  if (path === "/pm" || path.startsWith("/pm/")) return <FounderPm />;
  if (path === "/cleanup" || path.startsWith("/cleanup/")) return <CleanupCanvas />;
  if (path === "/desk" || path.startsWith("/desk/")) return <InternalDesk />;
  // `/` is the paper customer portal (C5-03). `/customer` stays as an alias.
  if (path === "/customer" || path.startsWith("/customer/") || path === "/" || path === "") {
    return <CustomerApp />;
  }
  return <InternalDesk />;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Suspense fallback={<p className="muted boot">Loading…</p>}>
      <Page />
    </Suspense>
  </React.StrictMode>
);

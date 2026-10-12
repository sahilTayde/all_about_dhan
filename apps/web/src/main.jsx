import React, { Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

const InternalDesk = lazy(() => import("./InternalDesk.jsx").then((m) => ({ default: m.InternalDesk })));
const FounderPm = lazy(() => import("./FounderPm.jsx").then((m) => ({ default: m.FounderPm })));
const CustomerApp = lazy(() => import("./App.jsx"));
const NotFound = lazy(() => import("./pages/NotFound.jsx").then((m) => ({ default: m.NotFound })));

function usePathname() {
  const [path, setPath] = useState(() => window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  return path;
}

const under = (path, base) => path === base || path.startsWith(`${base}/`);

function Page() {
  const path = usePathname().replace(/\/+$/, "") || "/";
  if (path === "/cleanup") {
    window.history.replaceState({}, "", "/ops");
    return <InternalDesk />;
  }
  if (under(path, "/pm")) return <FounderPm />;
  if (["/desk", "/desk/history", "/desk/strategies", "/ops"].includes(path)) return <InternalDesk />;
  if (path === "/" || under(path, "/customer")) return <CustomerApp />;
  return <NotFound />;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Suspense fallback={<p className="muted boot">Loading…</p>}>
      <Page />
    </Suspense>
  </React.StrictMode>
);

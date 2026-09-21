import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { CleanupCanvas } from "./CleanupCanvas.jsx";
import { FounderPm } from "./FounderPm.jsx";
import { InternalDesk } from "./InternalDesk.jsx";
import "./index.css";

function usePathname() {
  const [path, setPath] = useState(() => window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  return path;
}

function Root() {
  const path = usePathname();
  if (path === "/pm" || path.startsWith("/pm/")) {
    return <FounderPm />;
  }
  if (path === "/cleanup" || path.startsWith("/cleanup/")) {
    return <CleanupCanvas />;
  }
  if (path === "/" || path === "") {
    if (typeof window !== "undefined" && window.location.pathname === "/") {
      window.history.replaceState({}, "", "/desk");
    }
    return <InternalDesk />;
  }
  return <InternalDesk />;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

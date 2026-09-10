import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
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
  if (path === "/desk" || path.startsWith("/desk/")) {
    return <InternalDesk />;
  }
  if (path === "/cleanup" || path.startsWith("/cleanup/")) {
    return <CleanupCanvas />;
  }
  return <App />;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

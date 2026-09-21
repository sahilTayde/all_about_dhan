import { useEffect, useState } from "react";

const KNOWN = ["NIFTY", "BANKNIFTY", "SENSEX"];

function sessionUrl() {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return base ? `${base}/paper/founder-book` : "/paper/founder-book";
}

export function FounderBookPicker() {
  const [picked, setPicked] = useState([...KNOWN]);
  const [status, setStatus] = useState({
    NIFTY: "START",
    BANKNIFTY: "START",
    SENSEX: "START",
  });
  const [chosen, setChosen] = useState("NIFTY");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  function applyBook(j) {
    const names = Array.isArray(j?.trade_underlyings) ? j.trade_underlyings : [...KNOWN];
    setPicked(names);
    if (j?.index_status && typeof j.index_status === "object") {
      setStatus({
        NIFTY: j.index_status.NIFTY || (names.includes("NIFTY") ? "START" : "STOP"),
        BANKNIFTY: j.index_status.BANKNIFTY || (names.includes("BANKNIFTY") ? "START" : "STOP"),
        SENSEX: j.index_status.SENSEX || (names.includes("SENSEX") ? "START" : "STOP"),
      });
    } else {
      setStatus({
        NIFTY: names.includes("NIFTY") ? "START" : "STOP",
        BANKNIFTY: names.includes("BANKNIFTY") ? "START" : "STOP",
        SENSEX: names.includes("SENSEX") ? "START" : "STOP",
      });
    }
  }

  useEffect(() => {
    const ac = new AbortController();
    fetch(`${sessionUrl()}?t=${Date.now()}`, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (j) applyBook(j);
      })
      .catch(() => {});
    return () => ac.abort();
  }, []);

  async function postAction(action) {
    setBusy(true);
    setMsg("");
    try {
      const res = await fetch(sessionUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ underlying: chosen, action }),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j.detail || j.error || "save failed");
      applyBook(j);
      setMsg(
        action === "START"
          ? `START TRADE on ${chosen}. NEW paper fills allowed. Tape still records all three.`
          : `STOP TRADE on ${chosen}. NEW paper fills denied until you hit START TRADE. Open tickets stay.`,
      );
    } catch (err) {
      setMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  const chosenOn = (status[chosen] || "START") === "START" || picked.includes(chosen);

  return (
    <section className="panel founder-desk">
      <h2>Founder trade desk</h2>
      <p className="muted">
        Dual-tape keeps recording NIFTY + BANKNIFTY + SENSEX. You pick the index, then START TRADE or
        STOP TRADE. Default is START TRADE. There is no fill-count auto-stop — only this desk stops NEW fills.
      </p>

      <div className="founder-desk__grid">
        <div className="founder-desk__section">
          <h3>1. Which index</h3>
          <label className="filter-field">
            <span>Index</span>
            <select value={chosen} onChange={(e) => setChosen(e.target.value)}>
              {KNOWN.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </label>
          <p className="founder-desk__state">
            {chosen}:{" "}
            <strong className={chosenOn ? "is-up" : "is-down"}>
              {chosenOn ? "START TRADE" : "STOP TRADE"}
            </strong>
          </p>
        </div>

        <div className="founder-desk__section">
          <h3>2. Control</h3>
          <div className="founder-desk__btns">
            <button
              type="button"
              className={`founder-desk__btn founder-desk__btn--start${chosenOn ? " is-active" : ""}`}
              onClick={() => postAction("START")}
              disabled={busy}
            >
              {busy ? "Saving…" : "START TRADE"}
            </button>
            <button
              type="button"
              className={`founder-desk__btn founder-desk__btn--stop${!chosenOn ? " is-active" : ""}`}
              onClick={() => postAction("STOP")}
              disabled={busy}
            >
              {busy ? "Saving…" : "STOP TRADE"}
            </button>
          </div>
        </div>
      </div>

      <div className="founder-book">
        {KNOWN.map((name) => {
          const on = (status[name] || "START") === "START" || picked.includes(name);
          return (
            <span key={name} className="founder-book__opt">
              {name}: {on ? "START TRADE" : "STOP TRADE"}
            </span>
          );
        })}
      </div>
      {msg ? <p className="muted">{msg}</p> : null}
    </section>
  );
}

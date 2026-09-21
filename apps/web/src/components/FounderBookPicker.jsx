import { useEffect, useState } from "react";

const KNOWN = ["NIFTY", "BANKNIFTY", "SENSEX"];
const HELP =
  "Dual-tape keeps recording NIFTY + BANKNIFTY + SENSEX. You pick the index, then START TRADE or STOP TRADE. Default is STOP TRADE. There is no fill-count auto-stop — only this desk stops NEW fills.";

function sessionUrl() {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return base ? `${base}/paper/founder-book` : "/paper/founder-book";
}

function isStarted(status, picked, name) {
  if (status[name] === "START") return true;
  if (status[name] === "STOP") return false;
  return Array.isArray(picked) && picked.includes(name);
}

export function FounderBookPicker() {
  const [indexes, setIndexes] = useState([...KNOWN]);
  const [picked, setPicked] = useState([]);
  const [status, setStatus] = useState({
    NIFTY: "STOP",
    BANKNIFTY: "STOP",
    SENSEX: "STOP",
  });
  const [chosen, setChosen] = useState("NIFTY");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);

  function applyBook(j) {
    const known =
      Array.isArray(j?.known_underlyings) && j.known_underlyings.length
        ? j.known_underlyings.map((n) => String(n).toUpperCase())
        : [...KNOWN];
    setIndexes(known);
    const names = Array.isArray(j?.trade_underlyings) ? j.trade_underlyings : [];
    setPicked(names);
    const next = {};
    for (const name of known) {
      const raw = j?.index_status?.[name];
      if (raw === "START" || raw === "STOP") next[name] = raw;
      else next[name] = names.includes(name) ? "START" : "STOP";
    }
    setStatus(next);
    setChosen((cur) => (known.includes(cur) ? cur : known[0] || "NIFTY"));
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
          ? `START TRADE on ${chosen}. NEW paper fills allowed. Tape still records all indexes.`
          : `STOP TRADE on ${chosen}. NEW paper fills denied until you hit START TRADE. Open tickets stay.`,
      );
    } catch (err) {
      setMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  const chosenOn = isStarted(status, picked, chosen);

  return (
    <section className="panel founder-desk">
      <div className="founder-desk__head">
        <h2>Founder trade desk</h2>
        <button
          type="button"
          className="info-btn"
          aria-label="Founder trade desk extra information"
          aria-expanded={infoOpen}
          onClick={() => setInfoOpen((v) => !v)}
        >
          i
        </button>
      </div>
      {infoOpen ? (
        <div className="confidence-detail" role="region" aria-label="Founder trade desk extra information">
          <p>{HELP}</p>
        </div>
      ) : null}

      <div className="founder-desk__grid">
        <div className="founder-desk__section">
          <h3>1. Which index</h3>
          <label className="filter-field">
            <span>Index</span>
            <select value={chosen} onChange={(e) => setChosen(e.target.value)}>
              {indexes.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="founder-desk__section">
          <h3>2. Control</h3>
          <div className="founder-desk__btns">
            <button
              type="button"
              className={`founder-desk__btn founder-desk__btn--start${chosenOn ? " is-active" : ""}`}
              onClick={() => postAction("START")}
              disabled={busy || chosenOn}
              aria-pressed={chosenOn}
            >
              {busy ? "Saving…" : "START TRADE"}
            </button>
            <button
              type="button"
              className={`founder-desk__btn founder-desk__btn--stop${!chosenOn ? " is-active" : ""}`}
              onClick={() => postAction("STOP")}
              disabled={busy || !chosenOn}
              aria-pressed={!chosenOn}
            >
              {busy ? "Saving…" : "STOP TRADE"}
            </button>
          </div>
        </div>
      </div>

      {msg ? <p className="muted">{msg}</p> : null}
    </section>
  );
}

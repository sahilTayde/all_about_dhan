import { useEffect, useState } from "react";

const KNOWN = ["NIFTY", "BANKNIFTY", "SENSEX"];

function sessionUrl() {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return base ? `${base}/paper/founder-book` : "/paper/founder-book";
}

export function FounderBookPicker() {
  const [picked, setPicked] = useState(["NIFTY"]);
  const [chosen, setChosen] = useState("NIFTY");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    fetch(`${sessionUrl()}?t=${Date.now()}`, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (j?.trade_underlyings?.length) setPicked(j.trade_underlyings);
      })
      .catch(() => {});
    return () => ac.abort();
  }, []);

  async function save(nextPicked, actionText = "Saved") {
    setBusy(true);
    setMsg("");
    try {
      const res = await fetch(sessionUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_underlyings: nextPicked }),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j.detail || "save failed");
      setPicked(j.trade_underlyings || []);
      setMsg(`${actionText}. NEW fills obey this immediately after restart/next tick. Tape still records all three.`);
    } catch (err) {
      setMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  function stopChosen() {
    const next = picked.filter((x) => x !== chosen);
    save(next, `FOUNDER STOP TRADING ON ${chosen}`);
  }

  function restartChosen() {
    const next = picked.includes(chosen) ? picked : [...picked, chosen];
    save(next, `Restarted NEW fills on ${chosen}`);
  }

  return (
    <section className="panel">
      <h2>Founder book today</h2>
      <p className="muted">
        Dual-tape keeps recording NIFTY + BANKNIFTY + SENSEX. This control only tells the boss
        which index may get NEW paper fills. Stopped index denials show as FOUNDER STOP TRADING ON INDEX.
      </p>
      <div className="founder-book">
        <label className="filter-field">
          <span>Index</span>
          <select value={chosen} onChange={(e) => setChosen(e.target.value)}>
            {KNOWN.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </label>
        <button type="button" className="refresh-btn" onClick={stopChosen} disabled={busy || !picked.includes(chosen)}>
          {busy ? "Saving…" : `Stop ${chosen}`}
        </button>
        <button type="button" className="refresh-btn" onClick={restartChosen} disabled={busy || picked.includes(chosen)}>
          {busy ? "Saving…" : `Restart ${chosen}`}
        </button>
        {KNOWN.map((name) => (
          <span key={name} className="founder-book__opt">
            {name}: {picked.includes(name) ? "NEW fills ON" : "FOUNDER STOP TRADING"}
          </span>
        ))}
      </div>
      {msg ? <p className="muted">{msg}</p> : null}
    </section>
  );
}

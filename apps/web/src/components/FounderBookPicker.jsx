import { useEffect, useState } from "react";

const KNOWN = ["NIFTY", "BANKNIFTY", "SENSEX"];

function sessionUrl() {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return base ? `${base}/paper/founder-book` : "/paper/founder-book";
}

export function FounderBookPicker() {
  const [picked, setPicked] = useState(["NIFTY"]);
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

  function toggle(name) {
    setPicked((prev) => (prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]));
  }

  async function save() {
    setBusy(true);
    setMsg("");
    try {
      const res = await fetch(sessionUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_underlyings: picked }),
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j.detail || "save failed");
      setPicked(j.trade_underlyings || picked);
      setMsg("Saved. NEW fills only after the open ticket closes. Tape still records all three.");
    } catch (err) {
      setMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Founder book today</h2>
      <p className="muted">
        You pick which indices may get a NEW paper fill. Boss / dealer / analysts do not. Dual-tape
        still writes NIFTY + BANKNIFTY + SENSEX for replay. An open ticket is not flattened.
      </p>
      <div className="founder-book">
        {KNOWN.map((name) => (
          <label key={name} className="founder-book__opt">
            <input type="checkbox" checked={picked.includes(name)} onChange={() => toggle(name)} />
            {name}
          </label>
        ))}
        <button type="button" className="refresh-btn" onClick={save} disabled={busy || picked.length === 0}>
          {busy ? "Saving…" : "Save book"}
        </button>
      </div>
      {msg ? <p className="muted">{msg}</p> : null}
    </section>
  );
}

import { useState } from "react";
import { sendControl } from "../lib/founderControls.js";
import { inr, moneyClass } from "../lib/paperBoard.js";

const INDICES = ["NIFTY", "BANKNIFTY", "SENSEX"];

/** Account across every recorded day (server `account`), not the engine's daily reset. */
// While the API is still reading the model log, every all-days figure is partial: show none of them.
export function AccountPanel({ account, today, founderBook, indexing = false }) {
  const a = account || {};
  const status = founderBook?.index_status || {};
  const [funds, setFunds] = useState("");
  const [minCap, setMinCap] = useState("");
  const [why, setWhy] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function saveFunds(e) {
    e.preventDefault();
    if (!why.trim()) {
      setMsg("Type a reason first. It is logged with the command.");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      const done = [];
      if (funds) done.push((await sendControl("add-funds", { reason: why.trim(), amount_inr: Number(funds) })).kind);
      if (minCap !== "") done.push((await sendControl("min-capital", { reason: why.trim(), amount_inr: Number(minCap) })).kind);
      setMsg(done.length ? `Recorded ${done.join(" + ")} · pending until the engine's next cycle.` : "Enter an amount.");
      if (done.length) {
        setFunds("");
        setMinCap("");
        setWhy("");
      }
    } catch (err) {
      setMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }
  const allDays = (value, tone) => (indexing ? [<span className="indexing">Indexing history…</span>, "needs-history"] : [value, tone]);
  const rows = [
    ["Starting capital", inr(a.starting_capital_inr, { signed: false }), ""],
    ["Funds added", inr(a.funds_added_inr, { signed: false }), ""],
    ["Min capital to trade", a.min_capital_inr == null ? "—" : inr(a.min_capital_inr, { signed: false }), ""],
    ["Running gross", ...allDays(inr(a.gross_inr), moneyClass(a.gross_inr))],
    ["Charges", ...allDays(inr(a.charges_inr == null ? null : -a.charges_inr), a.charges_inr ? "is-down" : "")],
    ["Net (all days)", ...allDays(inr(a.net_inr), moneyClass(a.net_inr))],
    ["Equity", ...allDays(inr(a.equity_inr, { signed: false }), moneyClass((a.equity_inr ?? 0) - (a.starting_capital_inr ?? 0)))],
    ["Net today", inr(today?.net), moneyClass(today?.net)],
  ];
  return (
    <section className="panel account-panel">
      <div className="panel__head">
        <h2>Account</h2>
        <span className="muted small">
          {indexing
            ? "indexing history…"
            : a.n_days
              ? `${a.n_days} day${a.n_days > 1 ? "s" : ""} · ${a.first_day} → ${a.last_day}`
              : "no recorded days"}
        </span>
      </div>
      <dl className="kv-grid kv-grid--2">
        {rows.map(([k, v, tone]) => (
          <div key={k} className="kv">
            <dt>{k}</dt>
            <dd className={tone}>{v}</dd>
          </div>
        ))}
      </dl>
      <div className="index-chips" aria-label="Index trading state">
        {INDICES.map((n) => (
          <span key={n} className={`index-chip ${status[n] === "START" ? "is-on" : ""}`} title="Change on Founder → trade desk">
            {n} {status[n] === "START" ? "ON" : status[n] === "STOP" ? "OFF" : "—"}
          </span>
        ))}
      </div>
      <form className="account-funds" onSubmit={saveFunds}>
        <fieldset disabled={busy}>
          <legend>Funds (founder command)</legend>
          <label>
            Add funds ₹
            <input type="number" min="1" value={funds} onChange={(e) => setFunds(e.target.value)} placeholder="—" />
          </label>
          <label>
            Min capital to trade ₹
            <input type="number" min="0" value={minCap} onChange={(e) => setMinCap(e.target.value)} placeholder="—" />
          </label>
          <label>
            Reason
            <input value={why} onChange={(e) => setWhy(e.target.value)} maxLength={500} placeholder="logged" />
          </label>
          <button type="submit" className="refresh-btn">
            {busy ? "Saving…" : "Save"}
          </button>
        </fieldset>
      </form>
      <p className="muted small">{msg || a.funds_note || "Funds and minimum capital are founder commands (PAPER)."}</p>
    </section>
  );
}

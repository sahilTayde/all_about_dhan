import { inr, moneyClass } from "../lib/paperBoard.js";

const INDICES = ["NIFTY", "BANKNIFTY", "SENSEX"];

/** Account across every recorded day (server `account`), not the engine's daily reset. */
// While the API is still reading the model log, every all-days figure is partial: show none of them.
export function AccountPanel({ account, today, founderBook, indexing = false }) {
  const a = account || {};
  const status = founderBook?.index_status || {};
  const allDays = (value, tone) => (indexing ? [<span className="indexing">Indexing history…</span>, "needs-history"] : [value, tone]);
  const rows = [
    ["Starting capital", inr(a.starting_capital_inr, { signed: false }), ""],
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
      <fieldset className="account-funds" disabled>
        <legend>Funds · coming in controls PR</legend>
        <label>
          Add funds ₹
          <input type="number" placeholder="—" />
        </label>
        <label>
          Min capital to trade ₹
          <input type="number" placeholder="—" />
        </label>
        <button type="button" className="refresh-btn">
          Save
        </button>
      </fieldset>
      <p className="muted small">{a.funds_note || "Add funds / minimum capital need an engine-side setting. Coming in the controls PR."}</p>
    </section>
  );
}

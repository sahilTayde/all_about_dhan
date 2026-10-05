import { useEffect, useState } from "react";
import { fetchCustomerDesk } from "./lib/customerFeed.js";
import { formatSlot, formatWhen, selectCustomerView } from "./lib/customerPortal.js";
import { UnderlyingPicker } from "./components/UnderlyingPicker.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { LegendDialog } from "./components/LegendDialog.jsx";

function ModeBadge({ mode, feed }) {
  return (
    <span
      className={`mode-badge mode-badge--${String(mode || "mock").toLowerCase()}`}
      data-mode-badge={mode}
      data-feed={feed}
      title="Book mode. Never LIVE. Paper / shadow / mock only."
    >
      {mode}
    </span>
  );
}

function Chrome({ mode, feed, onInfo }) {
  return (
    <header className="cp-chrome">
      <div>
        <p className="cp-chrome__brand">all_about_dhan</p>
        <p className="cp-chrome__sub">Five paper seats · you decide · orders refused</p>
      </div>
      <div className="cp-chrome__tools">
        <ModeBadge mode={mode} feed={feed} />
        {onInfo ? (
          <button
            type="button"
            className="info-btn"
            aria-label="Open status legend"
            aria-haspopup="dialog"
            onClick={onInfo}
          >
            i
          </button>
        ) : null}
      </div>
    </header>
  );
}

function CustomerHero({ view }) {
  return (
    <section
      className={`customer-hero customer-hero--${view.tone} customer-hero--${view.market.toLowerCase()}`}
      data-testid="customer-hero"
      aria-labelledby="customer-hero-heading"
    >
      <div className="customer-hero__meta">
        <p className="customer-hero__kicker">{view.underlying}</p>
        <span className={`status-pill status-pill--${view.status.toLowerCase().replace(/[^a-z0-9]+/g, "")}`}>
          {view.status}
        </span>
      </div>
      <h1 id="customer-hero-heading" className="customer-hero__market">
        {view.market}
      </h1>
      <p className="customer-hero__why">{view.why}</p>
    </section>
  );
}

function TicketCard({ view }) {
  if (view.waiting || !view.ticket) {
    return (
      <section className="customer-ticket customer-ticket--empty" data-testid="customer-ticket">
        <p className="customer-ticket__kicker">Ticket</p>
        <p className="customer-ticket__empty-title">No suggested ticket</p>
        <p className="muted">HOLD until the desk issues a paper lean. Not a fill.</p>
      </section>
    );
  }
  const t = view.ticket;
  const slots = [
    ["Strike", t.strike],
    ["Entry", t.entry],
    ["Stop", t.stop],
    ["Target", t.target],
  ];
  return (
    <section className="customer-ticket" data-testid="customer-ticket">
      <p className="customer-ticket__kicker">One ticket · {view.underlying}</p>
      <dl className="customer-ticket__grid">
        {slots.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{formatSlot(value)}</dd>
          </div>
        ))}
      </dl>
      <p className="customer-ticket__qty">
        {t.lots === "" || t.lots == null ? "—" : t.lots} lot
        {Number(t.lots) === 1 ? "" : "s"} · {t.expiry} · {formatWhen(t.time)}
      </p>
    </section>
  );
}

function RiskStrip({ view }) {
  return (
    <section className="risk-strip" data-testid="risk-strip" aria-label="Risk">
      <p className="risk-strip__line">
        <span>Invalid if</span> {view.invalidIf}
      </p>
      <p className={`risk-strip__stale ${view.stale ? "is-stale" : ""}`} data-stale={view.staleText}>
        {view.staleText}
        {view.asOf ? ` · ${formatWhen(view.asOf)}` : ""}
      </p>
    </section>
  );
}

function CustomerBook({ view }) {
  const rows = view.bookRows;
  return (
    <section className="customer-book" data-testid="customer-book" aria-labelledby="customer-book-heading">
      <div className="customer-book__head">
        <h2 id="customer-book-heading">Today</h2>
        <ModeBadge mode={view.bookMode} feed={view.feed} />
      </div>
      {rows.length === 0 ? (
        <p className="customer-book__empty" data-testid="book-empty">
          No paper tickets today.
        </p>
      ) : (
        <ul className="customer-book__list">
          {rows.map((row) => (
            <li key={row.id || `${row.underlying}-${row.timeIst}`}>
              <div>
                <strong>
                  {row.underlying} {row.side ? String(row.side).replace("BUY_", "") : ""}
                </strong>
                <span className="muted">
                  {row.timeIst || row.time || "—"} · {formatSlot(row.strike)}
                </span>
              </div>
              <span>{row.displayed_status || row.status || "—"}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function App() {
  const [desk, setDesk] = useState(null);
  const [error, setError] = useState(null);
  const [underlying, setUnderlying] = useState("NIFTY");
  const [legendOpen, setLegendOpen] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    fetchCustomerDesk(ac.signal)
      .then((data) => {
        setDesk(data);
        setUnderlying(data.underlyings?.[0] || "NIFTY");
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setError(err.message || String(err));
      });
    return () => ac.abort();
  }, []);

  if (error) {
    return (
      <div className="shell shell--customer customer-portal">
        <Chrome mode="MOCK" feed="mock" />
        <p className="error-banner">{error}</p>
        <Disclaimer />
      </div>
    );
  }

  if (!desk) {
    return (
      <div className="shell shell--customer customer-portal" data-testid="customer-portal">
        <Chrome mode="…" feed="loading" />
        <p className="cp-loading muted">Loading ticket…</p>
      </div>
    );
  }

  const view = selectCustomerView(desk, underlying);
  const mockTape = view.feed !== "signals:public";

  return (
    <div className="shell shell--customer customer-portal" data-testid="customer-portal">
      <Chrome mode={view.mode} feed={view.feed} onInfo={() => setLegendOpen(true)} />

      {view.stale ? (
        <p className="stale-banner" role="status">
          Payload is stale. Do not treat this as a fresh ticket.
        </p>
      ) : null}
      {mockTape ? (
        <p className="mock-banner" data-testid="mock-banner">
          MOCK tape — no live signal stream. Not a fill.
        </p>
      ) : null}

      <UnderlyingPicker underlyings={view.underlyings} value={underlying} onChange={setUnderlying} />
      <CustomerHero view={view} />
      <TicketCard view={view} />
      <RiskStrip view={view} />
      <CustomerBook view={view} />

      <Disclaimer />
      <LegendDialog open={legendOpen} onClose={() => setLegendOpen(false)} />
    </div>
  );
}

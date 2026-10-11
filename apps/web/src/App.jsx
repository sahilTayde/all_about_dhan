import { useEffect, useMemo, useState } from "react";
import { fetchCustomerDesk, fetchCustomerJournal } from "./lib/customerFeed.js";
import { formatWhen, marketView, selectCustomerView, ticketStatus } from "./lib/customerPortal.js";
import { indexTabs, plainText } from "./lib/plainWords.js";
import { OpenPositions } from "./desk/components/OpenPositions.jsx";
import { SizeForm } from "./desk/components/SizeForm.jsx";
import { TradeJourney } from "./components/TradeJourney.jsx";
import { UnderlyingPicker } from "./components/UnderlyingPicker.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { LegendDialog } from "./components/LegendDialog.jsx";
import "./desk/desk.css";

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
        <p className="cp-chrome__sub">Paper seats · you decide · orders refused</p>
      </div>
      <div className="cp-chrome__tools">
        <ModeBadge mode={mode} feed={feed} />
        {onInfo ? (
          <button type="button" className="info-btn" aria-label="Open status legend" aria-haspopup="dialog" onClick={onInfo}>
            i
          </button>
        ) : null}
      </div>
    </header>
  );
}

function CustomerHero({ view, openCount }) {
  return (
    <section
      className={`customer-hero customer-hero--${view.tone} customer-hero--${view.market.toLowerCase()} customer-hero--alive`}
      data-testid="customer-hero"
      aria-labelledby="customer-hero-heading"
    >
      <div className="customer-hero__meta">
        <p className="customer-hero__kicker">{openCount > 1 ? "NIFTY + SENSEX" : view.underlying}</p>
        <span className={`status-pill status-pill--${view.status.toLowerCase().replace(/[^a-z0-9]+/g, "")}`}>{view.status}</span>
      </div>
      <h1 id="customer-hero-heading" className="customer-hero__market">
        {openCount > 1 ? "TWO OPEN" : view.market}
      </h1>
      <p className="customer-hero__why">{plainText(view.why, "Waiting for the next paper lean.")}</p>
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
            <dd title={String(value).includes("DATA") ? String(value) : undefined}>{plainText(value)}</dd>
          </div>
        ))}
      </dl>
      <SizeForm lots={Number(t.lots) || 10} entry={Number(t.entry)} />
      <p className="customer-ticket__qty">
        {t.expiry} · {formatWhen(t.time)}
      </p>
    </section>
  );
}

function RiskStrip({ view }) {
  return (
    <section className="risk-strip" data-testid="risk-strip" aria-label="Risk">
      <p className="risk-strip__line">
        <span>Invalid if</span> {plainText(view.invalidIf, "No ticket to invalidate.")}
      </p>
      <p className={`risk-strip__stale ${view.stale ? "is-stale" : ""}`} data-stale={view.staleText}>
        {plainText(view.staleText, "Waiting for live price")}
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
        <h2 id="customer-book-heading">Today’s book</h2>
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
                  {row.timeIst || row.time || "—"} · {plainText(row.strike)}
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

function signalToOpen(und, signal) {
  if (!signal) return null;
  const market = marketView(signal.side);
  const status = ticketStatus(signal);
  if (market === "HOLD" || status === "HOLD" || status === "DEALER_KILLED") return null;
  const entry = Number(signal.entry);
  const stop = Number(signal.stop);
  const target = Number(signal.target);
  if (![entry, stop, target].every(Number.isFinite)) return null;
  const openedTs = Date.parse(signal.timeIst || signal.opened_ist || "") / 1000;
  const opened = Number.isFinite(openedTs) ? openedTs : undefined;
  const ltp = Number(signal.last_ltp ?? signal.mark ?? entry);
  return {
    trade_id: signal.id || `open-${und}`,
    underlying: und,
    side: market === "CALL" ? "CE" : "PE",
    atm_strike: signal.strike,
    entry,
    limit_price: entry,
    last_ltp: ltp,
    stop,
    target,
    lots: signal.lots ?? 10,
    lot_size: signal.lot_size ?? (und === "SENSEX" ? 20 : 65),
    qty: (signal.lots || 10) * (signal.lot_size || (und === "SENSEX" ? 20 : 65)),
    status: "OPEN",
    opened_ts: opened,
    opened_ist: signal.timeIst || signal.opened_ist,
    premium_path:
      opened && Number.isFinite(ltp)
        ? [
            { t: opened, v: entry, label: "entry" },
            { t: opened + 180, v: ltp, label: "ltp" },
          ]
        : undefined,
    expiry: signal.expiry || signal.ticket?.expiry,
    justification: signal.customer?.note || signal.customer?.headline,
    strategy_id: signal.strategy_id,
    spot_at_entry: Number(signal.spot || signal.underlying_spot || signal.ticket?.underlying_spot) || null,
    last_index_spot: Number(signal.spot || signal.underlying_spot) || null,
    seen_high: Number(signal.seen_high) || null,
  };
}

export default function App() {
  const [desk, setDesk] = useState(null);
  const [journal, setJournal] = useState(null);
  const [error, setError] = useState(null);
  const [underlying, setUnderlying] = useState("NIFTY");
  const [legendOpen, setLegendOpen] = useState(false);
  const [picked, setPicked] = useState(null);

  useEffect(() => {
    const ac = new AbortController();
    fetchCustomerDesk(ac.signal)
      .then((data) => {
        setDesk(data);
        const tabs = indexTabs(data.underlyings);
        setUnderlying(tabs.includes(data.underlyings?.[0]) ? data.underlyings[0] : tabs[0]);
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setError(err.message || String(err));
      });
    return () => ac.abort();
  }, []);

  useEffect(() => {
    if (!desk) return undefined;
    const ac = new AbortController();
    fetchCustomerJournal(ac.signal).then((body) => {
      if (body) setJournal(body);
    });
    return () => ac.abort();
  }, [desk]);

  const tabs = useMemo(() => indexTabs(desk?.underlyings), [desk]);
  const opens = useMemo(() => {
    if (!desk?.signals) return [];
    return tabs.map((und) => signalToOpen(und, desk.signals[und])).filter(Boolean);
  }, [desk, tabs]);

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
          Paper tape — no live order stream.
        </p>
      ) : null}

      {tabs.length > 1 ? <UnderlyingPicker underlyings={tabs} value={underlying} onChange={setUnderlying} /> : null}
      <CustomerHero view={view} openCount={opens.length} />
      {opens.length >= 2 ? (
        <OpenPositions
          rows={opens}
          clock={
            Number.isFinite(Date.parse(desk.asOf || ""))
              ? { replay: true, ms: Date.parse(desk.asOf), ist: desk.asOf }
              : undefined
          }
          regimes={Object.fromEntries(
            opens.map((t) => [t.underlying, { itm_bin: { index: t.last_index_spot || t.spot_at_entry } }]),
          )}
          onSelect={setPicked}
          selectedId={picked?.trade_id}
        />
      ) : (
        <TradeJourney view={view} journal={journal} />
      )}
      <TicketCard view={view} />
      <RiskStrip view={view} />
      <CustomerBook view={view} />

      <Disclaimer />
      <LegendDialog open={legendOpen} onClose={() => setLegendOpen(false)} />
    </div>
  );
}

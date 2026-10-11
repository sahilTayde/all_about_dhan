import { clock as clockOf, fmtElapsed, inr, moneyClass, outcomeLabel, pct, px, regimeSpot, runningTradeView, ticketState } from "../../lib/paperBoard.js";
import { formatIst } from "../../lib/plainWords.js";
import { strategyName } from "../../lib/tradePipeline.js";
import { premiumMarks } from "../../lib/tradeMarks.js";
import { PremiumSpark } from "./EquitySpark.jsx";

function Cell({ label, value, tone, title }) {
  return (
    <div className="kv" title={title}>
      <dt>{label}</dt>
      <dd className={tone || ""}>{value}</dd>
    </div>
  );
}

function signedPct(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

function PathBar({ path, stop, entry, ltp, target }) {
  if (!path || path.sl == null || path.target == null) {
    return (
      <div className="run-path run-path--empty" data-testid="run-path">
        Waiting for SL / target
      </div>
    );
  }
  const left = (v) => `${Math.max(0, Math.min(100, (v ?? 0) * 100))}%`;
  return (
    <div className="run-path" data-testid="run-path">
      <div className="run-path__track" aria-hidden="true">
        <i className="run-path__fill" style={{ width: left(path.now) }} />
        <b className="run-path__mark run-path__mark--entry" style={{ left: left(path.entry) }} title="Entry" />
        <em className="run-path__mark run-path__mark--now" style={{ left: left(path.now) }} title="Now" />
      </div>
      <div className="run-path__ticks">
        <span>SL {px(stop)}</span>
        <span>Entry {px(entry)}</span>
        <span>Now {px(ltp)}</span>
        <span>Target {px(target)}</span>
      </div>
    </div>
  );
}

function PositionCard({ t, clock, nowMs, spotNow, selected, onSelect }) {
  const v = runningTradeView(t, { nowMs, spotNow });
  const s = ticketState(t, { clock });
  const name = strategyName(t);
  const inAt = formatIst(t.opened_ist);
  const marks = premiumMarks(t);
  const lines = marks.lines.filter((l) => l.id === "entry" || l.id === "stop" || l.id === "target");
  const what = [
    v.expiry ? `Expiry ${v.expiry}` : null,
    v.lots != null ? `${v.lots} lots` : null,
    v.qty != null ? `${v.qty} qty` : null,
    name || null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <li>
      <button
        type="button"
        className={`pos-card run-card current-trade${selected ? " is-selected" : ""}`}
        data-testid="pos-card"
        data-und={t.underlying}
        onClick={() => onSelect?.(t)}
      >
        <header>
          <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
          <strong>
            {t.underlying} {t.atm_strike ?? "—"}
          </strong>
          <span className={`state-pill state-pill--${s.key}`}>{s.label}</span>
        </header>
        <p className="run-card__what">{what || "Paper fill"}</p>
        <p className="run-card__when">
          In {inAt.text}
          {v.elapsedMs != null ? ` · ${fmtElapsed(v.elapsedMs)} in trade` : ""}
        </p>
        <div className="pos-card__body">
          <dl className="kv-grid">
            <Cell label="Entry" value={px(v.entry)} />
            <Cell label="Premium" value={px(v.ltp)} tone={moneyClass(v.pts)} />
            <Cell label="Spot in" value={px(v.spotIn)} />
            <Cell label="Spot now" value={px(v.spotNow)} />
            <Cell
              label="Stop"
              value={`${px(v.stop)}${v.slPct != null ? ` · ${signedPct(v.slPct)}` : ""}`}
              title={v.riskInr != null ? `${inr(v.riskInr, { signed: false })} risk` : undefined}
            />
            <Cell label="SL risk" value={inr(v.riskInr, { signed: false })} title="(entry − stop) × qty" />
            <Cell label="Target" value={`${px(v.target)}${v.tgtPct != null ? ` · ${signedPct(v.tgtPct)}` : ""}`} />
            <Cell label="Unrealised" value={inr(v.inr)} tone={moneyClass(v.inr)} title="(LTP − entry) × qty" />
            <Cell label="P&L %" value={v.pnlPct == null ? "—" : signedPct(v.pnlPct)} tone={moneyClass(v.pnlPct)} />
            <Cell label="Peak" value={inr(v.peakInr)} tone={moneyClass(v.peakInr)} title="Best premium since entry × qty" />
          </dl>
          <div className="run-card__path">
            <PathBar path={v.path} stop={v.stop} entry={v.entry} ltp={v.ltp} target={v.target} />
            <p className="run-card__cover">
              <span>{v.coveredPct == null ? "—" : `${signedPct(v.coveredPct)} of target covered`}</span>
              <span>{v.toStopPct == null ? "—" : `${pct(v.toStopPct)} to stop`}</span>
            </p>
          </div>
          <PremiumSpark points={marks.points} lines={lines} label={`${t.underlying} premium`} width={280} height={72} />
        </div>
        <p className="run-card__why">Why: {v.why}</p>
      </button>
    </li>
  );
}

/** Open paper fills. NIFTY and SENSEX sit side by side when both are live. */
export function OpenPositions({ rows, clock, hold, last, onSelect, selectedId, regimes }) {
  const list = rows || [];
  if (!list.length) {
    return (
      <section className="widget current-trade" data-testid="open-positions">
        <header className="widget__head">
          <h2>Running trade</h2>
          <span className={`state-pill state-pill--${hold ? "hold" : "waiting"}`}>{hold ? "ON HOLD" : "FLAT"}</span>
        </header>
        <div className="current-trade__empty">
          <p className="current-trade__big">{hold ? "On hold" : "No open paper fill"}</p>
          <p className="muted">{hold || "Empty book. The next CE/PE lands here when the board writes it."}</p>
          {last ? (
            <dl className="kv-grid kv-grid--3 last-ticket">
              <div className="kv">
                <dt>Last ticket</dt>
                <dd>{`${last.underlying} ${last.side} ${last.atm_strike ?? ""}`}</dd>
              </div>
              <div className="kv">
                <dt>Net ₹</dt>
                <dd className={moneyClass(last.realized_pnl_inr)}>{inr(last.realized_pnl_inr)}</dd>
              </div>
              <div className="kv">
                <dt>Out</dt>
                <dd>{clockOf(last.closed_ist) === "—" ? outcomeLabel(last) : clockOf(last.closed_ist)}</dd>
              </div>
            </dl>
          ) : null}
        </div>
      </section>
    );
  }
  const nowMs = clock?.replay && clock.ms != null ? clock.ms : Date.now();
  const totals = list.reduce(
    (acc, t) => {
      const n = runningTradeView(t, { nowMs, spotNow: regimeSpot(regimes, t.underlying) });
      if (n.inr != null) acc.inr += n.inr;
      acc.n += 1;
      return acc;
    },
    { inr: 0, n: 0 },
  );
  return (
    <section className="widget open-positions" data-testid="open-positions">
      <header className="widget__head">
        <h2>Running trade</h2>
        <span className="muted small">{list.length} paper fill{list.length === 1 ? "" : "s"}</span>
      </header>
      <ul className={`pos-list${list.length > 1 ? " pos-list--dual" : ""}`}>
        {list.map((t) => (
          <PositionCard
            key={t.trade_id}
            t={t}
            clock={clock}
            nowMs={nowMs}
            spotNow={regimeSpot(regimes, t.underlying) ?? t.last_index_spot}
            selected={selectedId === t.trade_id}
            onSelect={onSelect}
          />
        ))}
      </ul>
      {list.length > 1 ? (
        <div className="pos-total" data-testid="pos-total">
          <span>Combined</span>
          <strong className={moneyClass(totals.inr)}>{inr(totals.inr)}</strong>
          <span className="muted small">{totals.n} opens · before charges</span>
        </div>
      ) : null}
    </section>
  );
}

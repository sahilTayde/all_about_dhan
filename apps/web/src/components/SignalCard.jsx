import {
  customerStatus,
  formatLevel,
  sideCopy,
  slugState,
} from "../lib/status.js";
import { ConfidenceBox } from "./ConfidenceBox.jsx";

const LEVELS = [
  { key: "strike", label: "Strike" },
  { key: "entry", label: "Entry (index ref)" },
  { key: "stop", label: "Stop-loss" },
  { key: "target", label: "Target" },
];

export function SignalCard({ signal, fields, confidence, ticket }) {
  const status = customerStatus(signal);
  const side = sideCopy(signal.side);
  const closed = Boolean(signal.lifecycle?.outcome);
  const waiting = Boolean(signal.staged?.waiting) && !closed;
  const headline =
    signal.customer?.headline ||
    (closed ? signal.lifecycle?.headline : signal.staged?.headline) ||
    "Ticket";
  const note = signal.customer?.note || (closed ? signal.lifecycle?.note : "") || "";
  const levels = fields || {
    strike: signal.strike,
    entry: signal.entry,
    stop: signal.stop,
    target: signal.target,
  };
  const unitNote =
    ticket?.levels_note ||
    (ticket?.unit === "INDEX_POINTS_PROXY"
      ? "Paper index levels — not option premium fills."
      : "");

  return (
    <div className="signal-layout">
      <section
        className={`signal-card signal-card--${slugState(status)} signal-card--${side.kind}`}
        aria-labelledby="signal-card-heading"
      >
        <div className="signal-card__top">
          <p className="signal-card__kicker">
            {closed ? "Closed ticket" : "Suggested ticket"}
          </p>
          <span className={`status-pill status-pill--${slugState(status)}`}>
            {status}
          </span>
        </div>

        <div className="signal-card__hero">
          <h2 id="signal-card-heading" className="visually-hidden">
            {side.action} {side.option} {signal.underlying}
          </h2>
          <p className={`signal-card__side signal-card__side--${side.kind}`}>
            <span className="signal-card__action">{side.action}</span>
            <span className="signal-card__option">{side.option}</span>
          </p>
          <p className="signal-card__name">
            {signal.underlying}
            <span className="signal-card__strike-inline">
              {formatLevel(levels.strike)}
            </span>
          </p>
        </div>

        <dl className="level-strip">
          {LEVELS.map(({ key, label }) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>{formatLevel(levels[key])}</dd>
            </div>
          ))}
        </dl>

        {unitNote && <p className="signal-card__unit muted">{unitNote}</p>}

        <p className="signal-card__headline">{headline}</p>
        {waiting && signal.staged?.waitLabel && (
          <p className="signal-card__wait">{signal.staged.waitLabel}</p>
        )}
        {note && <p className="signal-card__note">{note}</p>}
        <p className="signal-card__decide">
          You choose whether to take this trade. The desk does not place orders
          for you.
        </p>
      </section>

      <ConfidenceBox confidence={confidence} ticket={ticket} />
    </div>
  );
}

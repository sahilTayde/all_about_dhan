import {
  customerStatus,
  formatLevel,
  isWaitingStatus,
  sideCopy,
  slugState,
} from "../lib/status.js";
import { ConfidenceBox } from "./ConfidenceBox.jsx";

const LEVELS = [
  { key: "strike", label: "Strike" },
  { key: "entry", label: "Entry (premium)" },
  { key: "stop", label: "Stop-loss" },
  { key: "target", label: "Target" },
];

export function SignalCard({ signal, fields, confidence, ticket }) {
  const status = customerStatus(signal);
  const waiting = isWaitingStatus(status);
  const side = waiting ? { action: "—", option: "—", kind: "unk" } : sideCopy(signal.side);
  const closed = Boolean(signal.lifecycle?.outcome);
  const headline = waiting
    ? "Waiting for next signal"
    : signal.customer?.headline ||
      (closed ? signal.lifecycle?.headline : signal.staged?.headline) ||
      "Ticket";
  const note = waiting
    ? "Signal window is blank until the desk issues a new paper lean. Not advice."
    : signal.customer?.note || (closed ? signal.lifecycle?.note : "") || "";
  const levels = waiting
    ? { strike: "", entry: "", stop: "", target: "" }
    : fields || {
        strike: signal.strike,
        entry: signal.entry,
        stop: signal.stop,
        target: signal.target,
      };
  const unitNote = waiting
    ? ""
    : ticket?.levels_note ||
      (ticket?.unit === "INDEX_POINTS_PROXY"
        ? "Paper levels — premium on ticket; index path on the chart."
        : "");

  return (
    <div className="signal-layout">
      <section
        className={`signal-card signal-card--${slugState(status)} signal-card--${side.kind}${
          waiting ? " signal-card--waiting" : ""
        }`}
        aria-labelledby="signal-card-heading"
      >
        <div className="signal-card__top">
          <p className="signal-card__kicker">
            {waiting ? "Signal window" : closed ? "Closed ticket" : "Suggested ticket"}
          </p>
          <span className={`status-pill status-pill--${slugState(status)}`}>
            {status}
          </span>
        </div>

        {waiting ? (
          <div className="signal-card__empty">
            <h2 id="signal-card-heading" className="signal-card__wait-title">
              WAITING FOR NEXT SIGNAL
            </h2>
            <p className="muted">{note}</p>
          </div>
        ) : (
          <>
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
            <p className="signal-card__lot muted">Size · 1 lot PAPER</p>

            <p className="signal-card__headline">{headline}</p>
            {note && <p className="signal-card__note">{note}</p>}
            <p className="signal-card__decide">
              You choose whether to take this trade. The desk does not place orders
              for you.
            </p>
          </>
        )}
      </section>

      <ConfidenceBox
        confidence={confidence}
        ticket={ticket}
        status={status}
        detail={signal?.confidenceDetail}
      />
    </div>
  );
}

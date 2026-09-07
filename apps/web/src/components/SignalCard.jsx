import {
  customerStatus,
  formatLevel,
  formatPremiumSlot,
  isWaitingStatus,
  levelFieldDefs,
  sideCopy,
  slugState,
  topVetoReasons,
} from "../lib/status.js";
import { ConfidenceBox } from "./ConfidenceBox.jsx";

/**
 * Customer ticket for BUY_CE / BUY_PE: Entry/SL/Target are option premium only.
 * INDEX_POINTS_PROXY numbers never occupy those slots — show DI / UNKNOWN instead.
 * Underlying index spot is labeled separately when present.
 */
export function SignalCard({ signal, fields, confidence, ticket, deskMeta }) {
  const status = customerStatus(signal);
  const waiting = isWaitingStatus(status);
  const vetoReasons = waiting ? topVetoReasons(signal, deskMeta) : [];
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
  const unit = ticket?.unit || signal?.ticket?.unit || "OPTION_PREMIUM";
  const unitUpper = String(unit).toUpperCase();
  const indexMasquerade =
    unitUpper === "INDEX_POINTS_PROXY" || unitUpper === "INDEX_POINTS";

  const rawLevels = waiting
    ? { strike: "", entry: "", stop: "", target: "" }
    : fields || {
        strike: signal.strike,
        entry: signal.entry,
        stop: signal.stop,
        target: signal.target,
      };

  // Never let index proxy numbers render in premium slots.
  const levels = waiting
    ? rawLevels
    : indexMasquerade
      ? {
          strike: rawLevels.strike,
          entry: "DATA_INSUFFICIENT",
          stop: "DATA_INSUFFICIENT",
          target: "DATA_INSUFFICIENT",
        }
      : rawLevels;

  const levelDefs = levelFieldDefs("OPTION_PREMIUM");
  const underlyingSpot = waiting
    ? null
    : signal?.underlying_spot ?? signal?.spot ?? ticket?.underlying_spot ?? null;
  const unitNote = waiting
    ? ""
    : ticket?.levels_note ||
      ticket?.levels_gap ||
      ticket?.stop_gap ||
      (indexMasquerade
        ? "DATA_INSUFFICIENT: option premium unbound. Index levels quarantined to the chart — not Entry/SL/Target."
        : !ticket?.levels_ready
          ? "DATA_INSUFFICIENT: OPTIDX premium not fetched / LTP unbound. Not a fill."
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
            {vetoReasons.length > 0 ? (
              <div className="veto-banner" role="status" aria-label="Hold reasons">
                <p className="veto-banner__title">Why the desk is holding</p>
                <ul className="veto-banner__list">
                  {vetoReasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                <p className="veto-banner__note muted">
                  Overlay hold only — not a deleted strategy. Not advice.
                </p>
              </div>
            ) : null}
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
              {levelDefs.map(({ key, label }) => (
                <div key={key}>
                  <dt>{label}</dt>
                  <dd>
                    {key === "strike"
                      ? formatLevel(levels[key])
                      : formatPremiumSlot(levels[key])}
                  </dd>
                </div>
              ))}
              {underlyingSpot != null && underlyingSpot !== "" && (
                <div>
                  <dt>Underlying spot</dt>
                  <dd>{formatLevel(underlyingSpot)}</dd>
                </div>
              )}
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

import { useEffect, useRef } from "react";
import { CAS_LEGEND, SENTIMENT_LEGEND, STATE_LEGEND } from "../lib/status.js";

export function LegendDialog({ open, onClose }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    function onKey(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="legend-overlay" onClick={onClose} role="presentation">
      <div
        className="legend-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="legend-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="legend-dialog__head">
          <h2 id="legend-title">Desk legend</h2>
          <button
            ref={closeRef}
            type="button"
            className="legend-dialog__close"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <p className="muted">
          Color is paired with a word. Status is not a fill and not advice.
          Confidence is agreement, not a win rate. MOCK / PAPER only.
        </p>

        <h3 className="legend-dialog__sub">Ticket status (customer honesty)</h3>
        <ul className="legend-list">
          {STATE_LEGEND.map((row) => (
            <li key={row.id}>
              <span
                className={`status-pill status-pill--${row.id.toLowerCase().replace(/[^a-z0-9]+/g, "")}`}
              >
                {row.label}
              </span>
              <span>{row.meaning}</span>
            </li>
          ))}
        </ul>

        <h3 className="legend-dialog__sub">Market sentiment</h3>
        <ul className="legend-list">
          {SENTIMENT_LEGEND.map((row) => (
            <li key={row.id}>
              <span className={`sent-chip sent-chip--${row.id.toLowerCase()}`}>
                {row.id}
              </span>
              <span>{row.meaning}</span>
            </li>
          ))}
        </ul>

        <h3 className="legend-dialog__sub">Close auction / cash bias</h3>
        <ul className="legend-list">
          {CAS_LEGEND.map((row) => (
            <li key={row.id}>
              <span className={`cas-bias cas-bias--${row.id.toLowerCase()}`} style={{ fontSize: "1rem" }}>
                {row.id}
              </span>
              <span>{row.meaning}</span>
            </li>
          ))}
        </ul>

        <h3 className="legend-dialog__sub">Side</h3>
        <ul className="legend-list">
          <li>
            <span className="signal-badge__option signal-badge--ce-text">CE</span>
            <span>Call buy. Green is direction, not “good.”</span>
          </li>
          <li>
            <span className="signal-badge__option signal-badge--pe-text">PE</span>
            <span>Put buy. Rose is direction, not “bad.”</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

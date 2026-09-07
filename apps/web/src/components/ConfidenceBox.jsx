import { useState } from "react";
import { isWaitingStatus } from "../lib/status.js";

/** Right-rail box: agreement score + plain why. Not a win rate. */

function bandClass(band) {
  return String(band || "none").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

export function ConfidenceBox({ confidence, ticket, status, detail }) {
  const [infoOpen, setInfoOpen] = useState(false);
  const conf = confidence || {};
  const waiting = isWaitingStatus(status);
  const score = typeof conf.score_pct === "number" ? conf.score_pct : null;
  const eligible = Array.isArray(conf.eligible) ? conf.eligible : [];
  const whyBullets = Array.isArray(conf.why_bullets)
    ? conf.why_bullets
    : conf.why
      ? [conf.why]
      : [];
  const ready = Boolean(ticket?.levels_ready) && !waiting;
  const tech = detail || conf.detail || {};

  if (waiting) {
    return (
      <aside className="confidence-box confidence-box--none" aria-labelledby="confidence-heading">
        <h2 id="confidence-heading">Desk confidence</h2>
        <p className="confidence-box__score">—</p>
        <p className="confidence-box__label">Waiting for next signal</p>
        <p className="confidence-box__fair muted">
          No active lean. Agreement score stays blank — not a win rate.
        </p>
      </aside>
    );
  }

  return (
    <aside
      className={`confidence-box confidence-box--${bandClass(conf.band)}`}
      aria-labelledby="confidence-heading"
    >
      <div className="confidence-box__head">
        <h2 id="confidence-heading">Desk confidence</h2>
        <button
          type="button"
          className="info-btn"
          aria-label="Open technical and liquidity detail"
          aria-expanded={infoOpen}
          onClick={() => setInfoOpen((v) => !v)}
        >
          i
        </button>
      </div>
      <p className="confidence-box__score" aria-live="polite">
        {score == null ? "—" : `${score}%`}
        <span className="confidence-box__paper"> PAPER</span>
      </p>
      <p className="confidence-box__label">{conf.label || "No active lean"}</p>
      <p className="confidence-box__fair muted">
        {conf.fairness ||
          "Agreement score only. Not a win rate. Not a fill promise. Model score, not a win probability."}
      </p>

      <h3 className="confidence-box__sub">Why (plain)</h3>
      {whyBullets.length === 0 && eligible.length === 0 ? (
        <p className="muted">No playbook is firing a side yet.</p>
      ) : whyBullets.length > 0 ? (
        <ul className="confidence-box__list">
          {whyBullets.slice(0, 3).map((line) => (
            <li key={line}>
              <span className="confidence-box__elig-why">{line}</span>
            </li>
          ))}
        </ul>
      ) : (
        <ul className="confidence-box__list">
          {eligible.slice(0, 3).map((row) => (
            <li key={`${row.mix_id}-${row.side}`}>
              <span className="confidence-box__elig-label">{row.label}</span>
              <span className="confidence-box__elig-side">
                {row.side === "BUY_CE" ? "CALL" : row.side === "BUY_PE" ? "PUT" : "—"}
              </span>
              {row.why && (
                <span className="confidence-box__elig-why muted">{row.why}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {ready ? (
        <p className="confidence-box__decide">
          Ticket levels are paper. <strong>You decide</strong> Yes / No below.
          Orders refused.
        </p>
      ) : (
        <p className="confidence-box__decide muted">
          Levels appear when a lean is confirmed. Still not a broker order.
        </p>
      )}

      {infoOpen && (
        <div className="confidence-detail" role="region" aria-label="Technical detail">
          <p className="confidence-detail__layer">
            HYPOTHESIS / PAPER — technical and liquidity detail
          </p>
          <p className="muted">
            Not advice. Not a claimed future win rate. Indicators and depth notes
            stay here, not on the ticket hero.
          </p>
          {Array.isArray(tech.hypothesis) && tech.hypothesis.length > 0 && (
            <ul>
              {tech.hypothesis.map((row) => (
                <li key={row}>{row}</li>
              ))}
            </ul>
          )}
          {Array.isArray(tech.liquidity) && tech.liquidity.length > 0 && (
            <>
              <h3 className="confidence-box__sub">Liquidity (paper)</h3>
              <ul>
                {tech.liquidity.map((row) => (
                  <li key={row}>{row}</li>
                ))}
              </ul>
            </>
          )}
          {!tech.hypothesis && !tech.liquidity && (
            <p className="muted">
              No extra tech notes in this MOCK payload. RSI / MACD / Supertrend /
              VWAP / order-book detail would appear here when present.
            </p>
          )}
        </div>
      )}
    </aside>
  );
}

/** Right-rail box: agreement score + which playbooks are eligible. Not a win rate. */

function bandClass(band) {
  return String(band || "none").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

export function ConfidenceBox({ confidence, ticket }) {
  const conf = confidence || {};
  const score = typeof conf.score_pct === "number" ? conf.score_pct : null;
  const eligible = Array.isArray(conf.eligible) ? conf.eligible : [];
  const ready = Boolean(ticket?.levels_ready);

  return (
    <aside
      className={`confidence-box confidence-box--${bandClass(conf.band)}`}
      aria-labelledby="confidence-heading"
    >
      <h2 id="confidence-heading">Desk confidence</h2>
      <p className="confidence-box__score" aria-live="polite">
        {score == null ? "—" : `${score}%`}
      </p>
      <p className="confidence-box__label">{conf.label || "No active lean"}</p>
      <p className="confidence-box__fair muted">
        {conf.fairness ||
          "Agreement score only. Not a win rate. Not a fill promise."}
      </p>

      <h3 className="confidence-box__sub">Eligible now</h3>
      {eligible.length === 0 ? (
        <p className="muted">No playbook is firing a side yet.</p>
      ) : (
        <ul className="confidence-box__list">
          {eligible.map((row) => (
            <li key={`${row.mix_id}-${row.side}`}>
              <span className="confidence-box__elig-label">{row.label}</span>
              <span className="confidence-box__elig-side">
                {row.side === "BUY_CE" ? "CALL" : row.side === "BUY_PE" ? "PUT" : "—"}
              </span>
              <span className="confidence-box__elig-why muted">{row.why}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="confidence-box__why">{conf.why}</p>

      {ready ? (
        <p className="confidence-box__decide">
          Ticket levels are paper. <strong>You decide</strong> whether to take
          it — Yes / No below. Orders refused.
        </p>
      ) : (
        <p className="confidence-box__decide muted">
          Levels appear when a lean is confirmed. Still not a broker order.
        </p>
      )}
    </aside>
  );
}

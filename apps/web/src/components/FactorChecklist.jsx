export function FactorChecklist({ factors = [] }) {
  return (
    <div className="factor-checklist">
      <h3 className="staged__subhead">Contributing factors</h3>
      <p className="muted">
        Mix-and-match checklist. EARLY can fire from news, chain OI, or PA
        before Supertrend or MACD flip.
      </p>
      <ul className="factor-list">
        {factors.map((factor) => (
          <li
            key={factor.id}
            className={factor.on ? "factor factor--on" : "factor factor--off"}
          >
            <span className="factor__mark" aria-hidden="true">
              {factor.on ? "✓" : "○"}
            </span>
            <span className="factor__body">
              <span className="factor__label">{factor.label}</span>
              <span className="factor__flag">{factor.on ? "in" : "out"}</span>
              {factor.detail && (
                <span className="factor__detail">{factor.detail}</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

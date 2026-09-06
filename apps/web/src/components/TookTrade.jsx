const FILL_FIELDS = [
  { key: "lots", label: "Lots", hint: "Lots you took (paper)" },
  { key: "spot", label: "Spot / fill", hint: "Your fill or spot" },
  { key: "pnl", label: "P-L", hint: "Your paper P-L" },
];

export function TookTrade({ value, onChange, fill, onFillChange }) {
  return (
    <section className="panel" aria-labelledby="took-heading">
      <h2 id="took-heading">Did you take this trade?</h2>
      <p className="muted">
        Your call. Local paper record only — not a broker order.
      </p>
      <div className="chip-row" role="group" aria-label="Did you take this trade?">
        <button
          type="button"
          className={value === true ? "chip chip--yes chip--active" : "chip"}
          aria-pressed={value === true}
          onClick={() => onChange(true)}
        >
          Yes
        </button>
        <button
          type="button"
          className={value === false ? "chip chip--no chip--active" : "chip"}
          aria-pressed={value === false}
          onClick={() => onChange(false)}
        >
          No
        </button>
      </div>

      {value === true && (
        <div className="took-fill">
          <p className="muted">Record paper lots, spot, and P-L. Mock only.</p>
          <div className="field-grid field-grid--3">
            {FILL_FIELDS.map(({ key, label, hint }) => (
              <label key={key} className="field" htmlFor={`fill-${key}`}>
                <span className="field__label">{label}</span>
                <input
                  id={`fill-${key}`}
                  name={key}
                  inputMode="decimal"
                  autoComplete="off"
                  value={fill?.[key] ?? ""}
                  onChange={(e) => onFillChange(key, e.target.value)}
                  aria-describedby={`hint-fill-${key}`}
                />
                <span id={`hint-fill-${key}`} className="field__hint">
                  {hint}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}
      {/* TODO(api): POST took-trade + lots/spot/pnl to apps/api for audit. */}
    </section>
  );
}

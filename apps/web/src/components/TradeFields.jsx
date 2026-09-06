const FIELDS = [
  { key: "strike", label: "Strike", hint: "Index option strike" },
  { key: "entry", label: "Entry", hint: "Premium (placeholder)" },
  { key: "stop", label: "Stop-loss", hint: "Premium stop-loss (placeholder)" },
  { key: "target", label: "Target", hint: "Premium target (placeholder)" },
];

export function TradeFields({ values, onChange }) {
  return (
    <section className="panel" aria-labelledby="levels-heading">
      <h2 id="levels-heading">Levels</h2>
      <p className="muted">Editable placeholders. Not live quotes.</p>
      <div className="field-grid">
        {FIELDS.map(({ key, label, hint }) => (
          <label key={key} className="field" htmlFor={`field-${key}`}>
            <span className="field__label">{label}</span>
            <input
              id={`field-${key}`}
              name={key}
              inputMode="decimal"
              autoComplete="off"
              value={values[key] ?? ""}
              onChange={(e) => onChange(key, e.target.value)}
              aria-describedby={`hint-${key}`}
            />
            <span id={`hint-${key}`} className="field__hint">
              {hint}
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}

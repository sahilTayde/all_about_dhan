const FIELDS = [
  { key: "strike", label: "Strike", hint: "Index option strike" },
  { key: "entry", label: "Entry (premium)", hint: "Option premium entry — never index spot" },
  { key: "stop", label: "Stop (premium)", hint: "Option premium stop — DATA_INSUFFICIENT if LTP unbound" },
  { key: "target", label: "Target (premium)", hint: "Option premium target — do not invent from index" },
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

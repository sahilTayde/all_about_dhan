const LABELS = {
  NIFTY: "NIFTY",
  BANKNIFTY: "BANKNIFTY",
  SENSEX: "SENSEX",
};

export function UnderlyingPicker({ underlyings, value, onChange }) {
  return (
    <nav className="index-tabs" aria-label="Index underlying">
      <div className="chip-row" role="tablist">
        {underlyings.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={value === key}
            className={value === key ? "chip chip--active" : "chip"}
            onClick={() => onChange(key)}
          >
            {LABELS[key] || key}
          </button>
        ))}
      </div>
      {/* TODO(markets): add expiry / lot display once contracts package exists. Never hardcode lot size. */}
    </nav>
  );
}

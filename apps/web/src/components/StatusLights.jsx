const LIGHT_COPY = {
  idle: { label: "Idle", className: "light--idle" },
  leaning: { label: "Leaning", className: "light--leaning" },
  lagging: { label: "Lagging", className: "light--lagging" },
  confirm: { label: "Confirm", className: "light--confirm" },
  against: { label: "Against", className: "light--against" },
};

export function StatusLights({ lights = [] }) {
  return (
    <div className="status-lights">
      <h3 className="staged__subhead">Indicator lights</h3>
      <p className="muted">
        Supertrend, RSI, EMA 9, MACD as status only — not live OHLC math.
      </p>
      <ul className="light-row" aria-label="Indicator status lights">
        {lights.map((light) => {
          const copy = LIGHT_COPY[light.state] || LIGHT_COPY.idle;
          return (
            <li key={light.id} className={`light ${copy.className}`}>
              <span className="light__dot" aria-hidden="true" />
              <span className="light__label">{light.label}</span>
              <span className="light__state">{copy.label}</span>
              {light.detail && <span className="light__detail">{light.detail}</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

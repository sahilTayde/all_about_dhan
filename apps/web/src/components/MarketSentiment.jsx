const WINDOWS = ["1h", "30m", "15m", "10m"];

export function MarketSentiment({ windows, values, source }) {
  const keys = windows?.length ? windows : WINDOWS;
  const label = source === "mock" ? "MOCK" : source || "MOCK";

  return (
    <section className="panel sentiment" aria-labelledby="sentiment-heading">
      <div className="panel__head">
        <h2 id="sentiment-heading">Market sentiment</h2>
        <span className="source-pill source-pill--quiet">{label}</span>
      </div>
      <p className="muted sentiment__hint">
        Last 1h / 30m / 15m / 10m. Fusion placeholder — not an indicator list.
      </p>
      <ul className="sentiment-grid">
        {keys.map((window) => {
          const bias = String(values?.[window] || "SIDEWAYS").toUpperCase();
          return (
            <li key={window} className="sentiment-cell">
              <span className="sentiment-cell__window">{window}</span>
              <span className={`sent-chip sent-chip--${bias.toLowerCase()}`}>
                {bias}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

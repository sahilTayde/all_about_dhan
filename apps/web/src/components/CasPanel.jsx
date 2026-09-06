const BIASES = ["BOUNCE", "SIDEWAYS", "FALL"];

function normalizeBias(raw) {
  const bias = String(raw || "SIDEWAYS").toUpperCase();
  return BIASES.includes(bias) ? bias : "SIDEWAYS";
}

function formatWhen(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "short",
    });
  } catch {
    return String(iso);
  }
}

function leanLabel(confidence) {
  const n = Number(confidence);
  if (!Number.isFinite(n)) return "lean unknown";
  if (n < 0.35) return "thin lean";
  if (n < 0.65) return "mixed lean";
  return "fuller lean";
}

/**
 * Customer CAS strip: close-auction / cash bias only.
 * No RSI / MACD / Supertrend. Not a fill. Not a win rate.
 */
export function CasPanel({ cas, underlying }) {
  const row = cas?.byUnderlying?.[underlying] || {};
  const bias = normalizeBias(row.bias || cas?.bias);
  const asOf = row.asOf || cas?.asOf;
  const source = cas?.source || "mock";
  const label = source === "mock" ? "MOCK" : source;
  const headline =
    row.headline ||
    cas?.note ||
    "Close auction bias. Official CAS is the cash closing auction — not a live fill.";
  const layer = row.layer || cas?.layer || "UNVALIDATED";

  return (
    <section className="panel cas-panel" aria-labelledby="cas-heading">
      <div className="panel__head">
        <h2 id="cas-heading">Close auction / cash bias</h2>
        <span className="source-pill source-pill--quiet">{label}</span>
      </div>
      <p className="muted cas-panel__hint">
        Official CAS = Closing Auction Session (cash F&amp;O names, 15:15–15:35 IST).
        Bias is vs the 15:15 print — not an indicator list.
      </p>
      <div className="cas-panel__body">
        <p className={`cas-bias cas-bias--${bias.toLowerCase()}`}>{bias}</p>
        <dl className="cas-meta">
          <div>
            <dt>Last update</dt>
            <dd>{formatWhen(asOf)}</dd>
          </div>
          <div>
            <dt>Lean</dt>
            <dd>{leanLabel(row.confidence)}</dd>
          </div>
          <div>
            <dt>Layer</dt>
            <dd>{layer}</dd>
          </div>
        </dl>
      </div>
      <p className="cas-panel__headline">{headline}</p>
    </section>
  );
}

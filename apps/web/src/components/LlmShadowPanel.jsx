import { moneyLine, shadowCompareView } from "../lib/llmShadowCompare.js";

/** Small founder panel: cumulative R3 take/skip net vs random skip. Shadow only. */
export function LlmShadowPanel({ compare }) {
  const v = shadowCompareView(compare);
  return (
    <section className="panel llm-shadow" data-testid="llm-shadow-panel">
      <div className="panel__head">
        <h2>Take / skip shadow</h2>
        <span className="muted small">Paper only · 1.5× Dhan costs · no veto</span>
      </div>
      {!v.ok ? (
        <p className="muted">No daily shadow compare yet. Nightly writes the first JSON after a paper session.</p>
      ) : (
        <>
          <dl className="kv-grid kv-grid--3">
            <div className="kv">
              <dt>R3 cumulative</dt>
              <dd className={v.r3Net == null ? "" : v.r3Net >= 0 ? "is-up" : "is-down"}>{moneyLine(v.r3Net)}</dd>
            </div>
            <div className="kv">
              <dt>Random skip mean</dt>
              <dd>{moneyLine(v.randomMean)}</dd>
            </div>
            <div className="kv">
              <dt>R3 vs random</dt>
              <dd className={v.delta == null ? "" : v.delta >= 0 ? "is-up" : "is-down"}>{moneyLine(v.delta)}</dd>
            </div>
          </dl>
          <p className="muted small">
            {v.nDays} scored day{v.nDays === 1 ? "" : "s"}. Logistic trains on earlier dates only. Not a promote.
          </p>
        </>
      )}
      <p className="muted small" data-testid="r4-status">
        {r4Line(v)}
      </p>
    </section>
  );
}

function r4Line(v) {
  if (v.r4Status === "ok") {
    return `R4 prompt loaded from ${v.r4Path}. Shadow only.`;
  }
  if (v.r4Status === "LOCK_MISMATCH") {
    return v.r4Note || `R4 prompt hash does not match prefix ${v.r4Prefix}. Replace the file at ${v.r4Path}.`;
  }
  return (
    v.r4Note ||
    `R4 prompt missing. Drop the frozen file (sha256 prefix ${v.r4Prefix}) at ${v.r4Path}.`
  );
}

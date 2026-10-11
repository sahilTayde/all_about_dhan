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
            {v.nDays} scored day{v.nDays === 1 ? "" : "s"}. Logistic trains on earlier dates only. R4 slot is empty
            until a new prompt is frozen. Not a promote.
          </p>
        </>
      )}
    </section>
  );
}

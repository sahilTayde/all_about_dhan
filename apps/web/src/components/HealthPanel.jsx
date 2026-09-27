const TONE_WORD = { green: "OK", amber: "SLOW", red: "DOWN", grey: "N/A" };

export function HealthPanel({ rows, founder, conn }) {
  const issues = founder?.issues || [];
  const list = rows?.length ? rows : [{ id: "api", name: "API", tone: "red", detail: "not reachable — static mock only" }];
  return (
    <section className="panel health-panel">
      <div className="panel__head">
        <h2>System health</h2>
        <span className={`conn conn--${conn}`}>{conn === "live" ? "live push" : conn}</span>
      </div>
      <ul className="rag-list">
        {list.map((r) => (
          <li key={r.id} className={`rag rag--${r.tone}`}>
            <i aria-hidden="true" />
            <strong>{r.name}</strong>
            <span className="rag__word">{TONE_WORD[r.tone] || r.tone}</span>
            <span className="rag__detail" title={r.detail}>
              {r.detail}
            </span>
          </li>
        ))}
      </ul>
      <p className="ops-issues__next">
        <strong>Next:</strong> {founder?.next_action || "Ops status not reachable — start the API (./scripts/desk.sh website)."}
      </p>
      {issues.length ? (
        <ul className="ops-issues__list">
          {issues.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

const CORE = [
  { id: "paper", label: "Recorder", aliases: ["paper", "heartbeat"] },
  { id: "broker", label: "Token", aliases: ["broker"] },
  { id: "data", label: "Feed", aliases: ["data"] },
];
const WORD = { green: "OK", amber: "SLOW", red: "DOWN", grey: "N/A" };

function pick(rows, aliases) {
  return (rows || []).find((r) => aliases.includes(r.id)) || null;
}

/** Compact recorder / token / feed bar. Replay hides live recorder/feed alarms. */
export function HealthStrip({ rows, conn, replay, onAdvanced }) {
  if (replay) {
    return (
      <div className="health-strip health-strip--ok" data-testid="health-strip" role="status">
        <span className="replay-pill" data-testid="replay-pill">
          REPLAY
        </span>
        <span className="muted small">Recorded tape · live recorder and feed alarms hidden</span>
        <span className={`conn conn--${conn}`}>{conn === "live" ? "live push" : conn || "—"}</span>
        {onAdvanced ? (
          <button type="button" className="link-btn" onClick={onAdvanced}>
            Advanced
          </button>
        ) : null}
      </div>
    );
  }
  const list = rows?.length ? rows : [{ id: "api", name: "API", tone: "red", detail: "not reachable" }];
  const worst = CORE.map((c) => pick(list, c.aliases)).some((r) => r?.tone === "red")
    ? "red"
    : CORE.map((c) => pick(list, c.aliases)).some((r) => r?.tone === "amber")
      ? "amber"
      : "ok";
  return (
    <div className={`health-strip health-strip--${worst}`} data-testid="health-strip" role="status">
      <ul className="health-strip__list">
        {CORE.map((c) => {
          const row = pick(list, c.aliases);
          const tone = row?.tone || "grey";
          return (
            <li key={c.id} className={`health-dot health-dot--${tone}`} title={row?.detail || undefined}>
              <i aria-hidden="true" />
              <span>{c.label}</span>
              <strong>{WORD[tone] || tone}</strong>
            </li>
          );
        })}
      </ul>
      <span className={`conn conn--${conn}`}>{conn === "live" ? "live push" : conn || "—"}</span>
      {onAdvanced ? (
        <button type="button" className="link-btn" onClick={onAdvanced}>
          Advanced
        </button>
      ) : null}
    </div>
  );
}

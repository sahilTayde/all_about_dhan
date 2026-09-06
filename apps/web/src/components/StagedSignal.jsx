const STAGES = [
  { id: "WATCH", label: "WATCH" },
  { id: "EARLY", label: "EARLY" },
  { id: "WAITING", label: "wait ~2 min" },
  { id: "CONFIRMED", label: "CONFIRMED" },
  { id: "VETOED", label: "VETOED" },
];

const OUTCOMES = [
  { id: "INVALIDATED", label: "INVALIDATED" },
  { id: "ACHIEVED", label: "ACHIEVED" },
  { id: "STOPPED", label: "STOPPED" },
  { id: "LOST", label: "LOST" },
  { id: "EXPIRED", label: "EXPIRED" },
];

const EMPTY = {
  state: "WATCH",
  waiting: false,
  waitLabel: "Not confirmed — wait ~2 min",
  lean: "",
  headline: "No staged payload",
  note: "Mock staged states only.",
  lights: [],
  factors: [],
};

function outcomeId(lifecycle) {
  const raw = String(lifecycle?.outcome || "").toUpperCase();
  return OUTCOMES.some((row) => row.id === raw) ? raw : "";
}

export function StagedSignal({ staged, lifecycle }) {
  const row = staged || EMPTY;
  const state = String(row.state || "WATCH").toUpperCase();
  const waiting = Boolean(row.waiting) && !outcomeId(lifecycle);
  const waitLabel = row.waitLabel || "Not confirmed — wait ~2 min";
  const outcome = outcomeId(lifecycle);
  const closed = Boolean(outcome);
  const bannerState = closed ? outcome : state;
  const kicker = closed ? outcome : state;
  const headline = closed ? lifecycle?.headline || row.headline : row.headline;
  const prior = closed ? String(lifecycle?.priorStage || state).toUpperCase() : "";

  return (
    <section className="panel staged" aria-labelledby="staged-heading">
      <h2 id="staged-heading">Staged signal</h2>
      <p className="muted">
        Engineering honesty stages. This block is not on the customer desk.
      </p>

      <p className="staged__subhead" id="stage-legend-label">
        Honesty stages
      </p>
      <ul className="stage-legend" aria-labelledby="stage-legend-label">
        {STAGES.map((stage) => {
          const isWait = stage.id === "WAITING";
          const active = closed ? false : isWait ? waiting : state === stage.id;
          return (
            <li
              key={stage.id}
              className={`stage-chip stage-chip--${stage.id.toLowerCase()}${
                active ? " stage-chip--active" : ""
              }`}
            >
              {stage.label}
            </li>
          );
        })}
      </ul>

      <p className="staged__subhead" id="outcome-legend-label">
        Lifecycle outcomes
      </p>
      <ul className="stage-legend" aria-labelledby="outcome-legend-label">
        {OUTCOMES.map((item) => {
          const active = outcome === item.id;
          return (
            <li
              key={item.id}
              className={`stage-chip stage-chip--${item.id.toLowerCase()}${
                active ? " stage-chip--active" : ""
              }`}
            >
              {item.label}
            </li>
          );
        })}
      </ul>

      <div
        className={`stage-banner stage-banner--${bannerState.toLowerCase()}${
          waiting ? " stage-banner--waiting" : ""
        }`}
      >
        <p className="stage-banner__kicker">{kicker}</p>
        <p className="stage-banner__headline">{headline}</p>
        {closed && prior && (
          <p className="stage-banner__prior">was {prior} · closed</p>
        )}
        {waiting && <p className="stage-banner__wait">{waitLabel}</p>}
      </div>

      {closed && lifecycle?.note && (
        <p className="staged__note">{lifecycle.note}</p>
      )}
      {!closed && row.note && <p className="staged__note">{row.note}</p>}

      {/* TODO(api): wire staged + lifecycle from GET /paper/signal (same JSON shape). */}
      {/* TODO(desk_intel): map MARKET_SIGNAL + factor flags from packages/desk-intel. */}
      {/* TODO(jobs): nightly recon should stamp INVALIDATED/ACHIEVED/STOPPED/LOST/EXPIRED. */}
    </section>
  );
}

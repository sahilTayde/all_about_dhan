import { useEffect, useMemo, useState } from "react";
import { fetchTrace } from "../../lib/feed.js";
import { inr, moneyClass } from "../../lib/paperBoard.js";
import { PIPE_STAGES, buildPipelines, stagesForRecord } from "../../lib/tradePipeline.js";

const ICONS = {
  analyst: "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-4 0-8 2-8 5v1h16v-1c0-3-4-5-8-5z",
  desk: "M3 10h18v2H3zm2 3h6v7H5zm8 0h6v7h-6zM4 4h16v4H4z",
  overlay: "M4 6h16v2H4zm2 5h12v2H6zm2 5h8v2H8z",
  boss: "M12 2l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z",
  imm: "M4 7h16v10H4zm2 2v6h12V9z",
  live: "M8 5v14l11-7z",
  exit: "M5 5h8v2H7v10h6v2H5zm9 4 5 3-5 3V9z",
};

const KIND_LABEL = { live: "On the move", skipped: "Stopped", closed: "Arrived", empty: "Waiting" };

function StageIcon({ id }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path fill="currentColor" d={ICONS[id] || ICONS.desk} />
    </svg>
  );
}

function stageLine(stage) {
  if (stage.state === "waiting") return "waiting";
  if (stage.state === "blocked") return stage.why;
  if (stage.at?.text) return stage.at.text;
  return stage.why;
}

function StageButton({ stage, on, onPick }) {
  return (
    <button
      type="button"
      className={`pipe-stage pipe-stage--${stage.state}${on ? " is-on" : ""}`}
      data-testid="pipe-stage"
      data-stage={stage.id}
      data-state={stage.state}
      aria-pressed={on}
      onClick={() => onPick(stage)}
    >
      <span className="pipe-stage__icon">
        <StageIcon id={stage.id} />
        {stage.state === "done" ? <i className="pipe-check">✓</i> : null}
      </span>
      <strong>{stage.label}</strong>
      <em>{stage.hint}</em>
      <span className="pipe-stage__why" title={stage.code || undefined}>
        {stageLine(stage)}
      </span>
    </button>
  );
}

function StageDetail({ pick, onClose }) {
  if (!pick) return <p className="muted small pipe-hint">Tap a station for the recorded inputs, rule, and reason.</p>;
  const inputs = Object.entries(pick.inputs || {}).filter(([, v]) => v != null && v !== "");
  return (
    <div className="pipe-detail" data-testid="pipe-detail">
      <header>
        <p>
          <strong>
            {pick.lane ? `${pick.lane} · ` : ""}
            {pick.label}
          </strong>
          {pick.at?.text ? ` · ${pick.at.text}` : ""}
        </p>
        <button type="button" className="link-btn" onClick={onClose}>
          Close
        </button>
      </header>
      <dl className="kv-grid kv-grid--3">
        {pick.why && pick.why !== "waiting" ? (
          <div className="kv">
            <dt>Reason</dt>
            <dd title={pick.code || undefined}>{pick.why}</dd>
          </div>
        ) : null}
        {pick.who ? (
          <div className="kv">
            <dt>Who</dt>
            <dd>{pick.who}</dd>
          </div>
        ) : null}
        {pick.rule && pick.rule !== "waiting" ? (
          <div className="kv">
            <dt>Rule</dt>
            <dd title={pick.code || undefined}>{pick.rule}</dd>
          </div>
        ) : null}
      </dl>
      {inputs.length ? (
        <dl className="kv-grid kv-grid--2">
          {inputs.map(([k, v]) => (
            <div key={k} className="kv">
              <dt>{k}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="muted small">No extra inputs on this stage.</p>
      )}
    </div>
  );
}

function HistoryFlow({ stages, onPick }) {
  return (
    <ol className="pipe-flow pipe-flow--mini" data-testid="pipe-review">
      {stages.map((stage) => (
        <li key={stage.id}>
          <StageButton stage={stage} on={false} onPick={onPick} />
        </li>
      ))}
    </ol>
  );
}

/** Station-board pipeline. NIFTY and SENSEX lanes. Recorded tape only. */
export function TradePipeline({ board, open, closed }) {
  const [traces, setTraces] = useState({});
  const [pick, setPick] = useState(null);
  const [review, setReview] = useState(null);

  const ids = useMemo(
    () => [...(open || []), ...(closed || [])].slice(0, 8).map((t) => t.trade_id).filter(Boolean),
    [open, closed],
  );

  useEffect(() => {
    let stop = false;
    ids.forEach((id) => {
      fetchTrace(id)
        .then((t) => {
          if (!stop && t) setTraces((prev) => ({ ...prev, [id]: t }));
        })
        .catch(() => {});
    });
    return () => {
      stop = true;
    };
  }, [ids.join("|")]);

  const model = useMemo(
    () => buildPipelines(board, { uniqueOpen: open, uniqueClosed: closed, traces }),
    [board, open, closed, traces],
  );

  function pickStage(stage, lane) {
    setPick({ ...stage, lane: lane.underlying, title: lane.title });
    setReview(null);
  }

  function pickHistory(row) {
    const stages = stagesForRecord(row.record, traces);
    setReview({ ...row, stages });
    const blocked = stages.find((s) => s.state === "blocked");
    setPick(blocked ? { ...blocked, lane: row.underlying, title: row.label } : { ...stages[0], lane: row.underlying, title: row.label });
  }

  return (
    <section className="pipeline" data-testid="trade-pipeline">
      <header className="widget__head pipeline__head">
        <div>
          <p className="desk-kicker">Live board</p>
          <h2>Trade pipeline</h2>
        </div>
        <ol className="pipe-legend" aria-label="Stage order">
          {PIPE_STAGES.map((s) => (
            <li key={s.id}>{s.label}</li>
          ))}
        </ol>
      </header>
      <div className="pipeline__lanes">
        {model.lanes.map((lane) => (
          <article key={lane.underlying} className={`pipe-lane pipe-lane--${lane.kind}`} data-testid="pipe-lane" data-und={lane.underlying}>
            <header className="pipe-lane__head">
              <strong>{lane.title}</strong>
              {lane.name ? <span className="muted small">{lane.name}</span> : null}
              <span className={`pipe-pill pipe-pill--${lane.kind}`}>{KIND_LABEL[lane.kind] || lane.kind}</span>
            </header>
            <ol className="pipe-flow">
              {lane.stages.map((stage) => (
                <li key={stage.id}>
                  <StageButton
                    stage={stage}
                    on={pick?.lane === lane.underlying && pick?.id === stage.id && !review}
                    onPick={(s) => pickStage(s, lane)}
                  />
                </li>
              ))}
            </ol>
          </article>
        ))}
      </div>
      <StageDetail pick={pick} onClose={() => setPick(null)} />
      {review ? (
        <div className="pipe-review">
          <p className="muted small">
            Earlier ticket · {review.label}
            {review.name ? ` · ${review.name}` : ""}
          </p>
          <HistoryFlow stages={review.stages} onPick={(s) => setPick({ ...s, lane: review.underlying, title: review.label })} />
        </div>
      ) : null}
      <div className="pipe-history" data-testid="pipe-history">
        <h3>Today’s earlier tickets</h3>
        {!model.history.length ? (
          <p className="empty-state">No earlier pipelines today.</p>
        ) : (
          <ol>
            {model.history.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  className={`pipe-hist pipe-hist--${row.state}${review?.id === row.id ? " is-on" : ""}`}
                  data-testid="pipe-hist"
                  onClick={() => pickHistory(row)}
                >
                  <strong>{row.label}</strong>
                  {row.name ? <span className="muted small">{row.name}</span> : null}
                  <span title={row.code || undefined}>{row.why}</span>
                  {row.pnl != null ? (
                    <span className={moneyClass(row.pnl)} data-testid="pipe-hist-pnl">
                      {inr(row.pnl)}
                    </span>
                  ) : (
                    <span className="muted small">—</span>
                  )}
                  <span className="muted small">{row.at?.text || "waiting"}</span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

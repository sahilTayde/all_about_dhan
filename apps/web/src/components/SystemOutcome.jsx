import { formatPts as formatPtsLib } from "../lib/status.js";

function formatPts(n) {
  return formatPtsLib(n);
}

function displayPts(value) {
  if (value === "" || value == null) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return formatPts(n);
}

export function SystemOutcome({ tookTrade, outcome, lifecycle, userFill }) {
  const shadow = lifecycle?.shadowPaper;
  const closed = Boolean(lifecycle?.outcome);
  let title = "Waiting on Yes / No";
  let body = "Answer Yes or No to see the paper mark-to-market.";
  let kind = "idle";
  let mtm = outcome?.mtmPts;
  let comment = outcome?.comment;

  if (tookTrade === true) {
    kind = "taken";
    title = "Your paper fill";
    body = closed
      ? `Ticket closed as ${lifecycle.outcome}. Your lots / spot / P-L stay on this screen.`
      : "System tracks this path as a taken paper trade.";
    comment = "Mock inputs only. Not a live fill and not investment advice.";
  } else if (tookTrade === false) {
    kind = "shadow";
    title = "Shadow paper (you skipped)";
    body = "Platform tracked anyway. Skip does not hide the mock path.";
    mtm = shadow?.mtmPts ?? outcome?.mtmPts;
    comment = shadow?.comment || outcome?.comment;
  }

  const userPnl = userFill?.pnl;
  const userPnlNum = Number(userPnl);
  const userDown = userPnl !== "" && !Number.isNaN(userPnlNum) && userPnlNum < 0;
  const sysDown = typeof mtm === "number" && mtm < 0;

  return (
    <section className={`panel outcome outcome--${kind}`} aria-labelledby="outcome-heading">
      <h2 id="outcome-heading">System outcome</h2>
      <p className="outcome__title">{title}</p>

      {tookTrade === true && (
        <dl className="fill-readout">
          <div>
            <dt>Lots</dt>
            <dd>{userFill?.lots || "—"}</dd>
          </div>
          <div>
            <dt>Spot / fill</dt>
            <dd>{userFill?.spot || "—"}</dd>
          </div>
          <div>
            <dt>P-L</dt>
            <dd className={userDown ? "is-down" : "is-up"}>{displayPts(userPnl)}</dd>
          </div>
        </dl>
      )}

      {tookTrade === false && (
        <p className={`outcome__mtm ${sysDown ? "is-down" : "is-up"}`}>
          {formatPts(mtm)}
        </p>
      )}

      <p className="muted">{body}</p>
      {tookTrade !== null && comment && <p className="muted">{comment}</p>}
      {/* TODO(mtm): replace mock points with server-side mark-to-market; never compute live P&amp;L here. */}
    </section>
  );
}

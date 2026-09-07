import {
  formatLevel,
  formatPts,
  paperBookStats,
  sideCopy,
} from "../lib/status.js";

const PATH_LABEL = {
  CUSTOMER: "Customer-taken",
  SHADOW: "Platform shadow",
  OPEN: "Open",
  PAPER: "Paper",
};

export function TodaysBook({ book }) {
  if (!book) return null;
  const summary = book.summary || {};
  const rows = book.rows || [];
  const stats = paperBookStats(rows);
  const winPct =
    summary.winPct != null
      ? summary.winPct
      : stats.winPct;
  const points =
    summary.pointsCaptured != null
      ? summary.pointsCaptured
      : stats.pointsCaptured;

  return (
    <section className="panel book" aria-labelledby="book-heading">
      <div className="panel__head">
        <h2 id="book-heading">Today&apos;s paper book</h2>
        <span className="source-pill">{book.label || "MOCK"}</span>
      </div>
      <p className="muted">
        {book.note ||
          "Mock paper ledger. Not live P/L. Win% is historical paper only — not confidence."}
      </p>

      <dl className="book-summary">
        <div>
          <dt>Closed (paper)</dt>
          <dd>{summary.closedCount ?? stats.closedCount}</dd>
        </div>
        <div>
          <dt>Wins</dt>
          <dd>{summary.winCount ?? stats.winCount}</dd>
        </div>
        <div>
          <dt>Paper win%</dt>
          <dd>{winPct == null ? "N/A" : `${winPct}%`}</dd>
        </div>
        <div>
          <dt>Cumulative pts</dt>
          <dd className={Number(points) < 0 ? "is-down" : "is-up"}>
            {formatPts(points)}
          </dd>
        </div>
      </dl>

      <div className="book-table-wrap">
        <table className="book-table">
          <caption className="visually-hidden">
            Mock paper trades for this session
          </caption>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">Underlying</th>
              <th scope="col">Side</th>
              <th scope="col">Strike</th>
              <th scope="col">Status</th>
              <th scope="col">Result</th>
              <th scope="col">Spot</th>
              <th scope="col">Entry</th>
              <th scope="col">SL</th>
              <th scope="col">Target</th>
              <th scope="col">Lots</th>
              <th scope="col">Points</th>
              <th scope="col">Path</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const side = sideCopy(row.side);
              const down = typeof row.points === "number" && row.points < 0;
              return (
                <tr key={row.id}>
                  <td className="num">{row.timeIst || row.time || "—"}</td>
                  <td>{row.underlying}</td>
                  <td>
                    <span className={`side-mini side-mini--${side.kind}`}>
                      {side.action} {side.option}
                    </span>
                  </td>
                  <td className="num">{formatLevel(row.strike)}</td>
                  <td>{row.displayed_status || row.status || "—"}</td>
                  <td>
                    <span
                      className={`result-chip result-chip--${String(row.result || "").toLowerCase()}`}
                    >
                      {row.result}
                    </span>
                  </td>
                  <td className="num">{formatLevel(row.spot)}</td>
                  <td className="num">{formatLevel(row.entry)}</td>
                  <td className="num">{formatLevel(row.stop ?? row.sl)}</td>
                  <td className="num">{formatLevel(row.target)}</td>
                  <td className="num">{row.lots ?? 1} PAPER</td>
                  <td className={`num ${down ? "is-down" : "is-up"}`}>
                    {formatPts(row.points)}
                  </td>
                  <td>{PATH_LABEL[row.path] || row.path}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

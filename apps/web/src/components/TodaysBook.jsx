import { formatLevel, formatPts, sideCopy } from "../lib/status.js";

const PATH_LABEL = {
  CUSTOMER: "Customer-taken",
  SHADOW: "Platform shadow",
  OPEN: "Open",
};

export function TodaysBook({ book }) {
  if (!book) return null;
  const summary = book.summary || {};
  const rows = book.rows || [];

  return (
    <section className="panel book" aria-labelledby="book-heading">
      <div className="panel__head">
        <h2 id="book-heading">Today&apos;s book</h2>
        <span className="source-pill">{book.label || "MOCK"}</span>
      </div>
      <p className="muted">{book.note || "Mock ledger. Not live P/L."}</p>

      <dl className="book-summary">
        <div>
          <dt>Customer-taken</dt>
          <dd>{summary.customerTaken ?? "—"}</dd>
        </div>
        <div>
          <dt>Platform shadow</dt>
          <dd>{summary.platformShadow ?? "—"}</dd>
        </div>
        <div>
          <dt>Open</dt>
          <dd>{summary.openTickets ?? "—"}</dd>
        </div>
        <div>
          <dt>Points captured</dt>
          <dd className={Number(summary.pointsCaptured) < 0 ? "is-down" : "is-up"}>
            {formatPts(summary.pointsCaptured)}
          </dd>
        </div>
      </dl>

      <div className="book-table-wrap">
        <table className="book-table">
          <caption className="visually-hidden">
            Mock trades for this session
          </caption>
          <thead>
            <tr>
              <th scope="col">Underlying</th>
              <th scope="col">Side</th>
              <th scope="col">Strike</th>
              <th scope="col">Points</th>
              <th scope="col">Result</th>
              <th scope="col">Path</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const side = sideCopy(row.side);
              const down = typeof row.points === "number" && row.points < 0;
              return (
                <tr key={row.id}>
                  <td>{row.underlying}</td>
                  <td>
                    <span className={`side-mini side-mini--${side.kind}`}>
                      {side.action} {side.option}
                    </span>
                  </td>
                  <td className="num">{formatLevel(row.strike)}</td>
                  <td className={`num ${down ? "is-down" : "is-up"}`}>
                    {formatPts(row.points)}
                  </td>
                  <td>
                    <span
                      className={`result-chip result-chip--${String(row.result || "").toLowerCase()}`}
                    >
                      {row.result}
                    </span>
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

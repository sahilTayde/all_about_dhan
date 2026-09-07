import {
  formatLevel,
  formatPremiumSlot,
  formatPts,
  paperBookStats,
  sideCopy,
  sortBookRowsNewestFirst,
} from "../lib/status.js";

const PATH_LABEL = {
  CUSTOMER: "Customer-taken",
  SHADOW: "Platform shadow",
  OPEN: "Open",
  PAPER: "Paper",
};

function BookTable({ rows, caption, emptyMessage }) {
  return (
    <div className="book-table-wrap">
      <table className="book-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Time</th>
            <th scope="col">Underlying</th>
            <th scope="col">Side</th>
            <th scope="col">Strike</th>
            <th scope="col">Status</th>
            <th scope="col">Result</th>
            <th scope="col">Underlying spot</th>
            <th scope="col">Entry (prem)</th>
            <th scope="col">SL (prem)</th>
            <th scope="col">Target (prem)</th>
            <th scope="col">Lots</th>
            <th scope="col">Points</th>
            <th scope="col">Path</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={13} className="muted">
                {emptyMessage || "No rows yet. Not a fill."}
              </td>
            </tr>
          ) : (
            rows.map((row) => {
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
                  <td className="num">{formatPremiumSlot(row.entry)}</td>
                  <td className="num">{formatPremiumSlot(row.stop ?? row.sl)}</td>
                  <td className="num">{formatPremiumSlot(row.target)}</td>
                  <td className="num">{row.lots ?? 1} PAPER</td>
                  <td className={`num ${down ? "is-down" : "is-up"}`}>
                    {formatPts(row.points)}
                  </td>
                  <td>{PATH_LABEL[row.path] || row.path}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

function BookPanel({ book, headingId, title, emptyHint }) {
  if (!book) return null;
  const summary = book.summary || {};
  const rows = sortBookRowsNewestFirst(book.rows || []);
  const stats = paperBookStats(rows);
  const winPct = summary.winPct != null ? summary.winPct : stats.winPct;
  const points =
    summary.pointsCaptured != null ? summary.pointsCaptured : stats.pointsCaptured;
  const isFixture = String(book.source || book.label || "").toLowerCase().includes("fixture")
    || String(book.label || "").toUpperCase() === "FIXTURE"
    || String(book.mode || "").toUpperCase() === "FIXTURE";

  return (
    <section className="panel book" aria-labelledby={headingId}>
      <div className="panel__head">
        <h2 id={headingId}>{title}</h2>
        <span className="source-pill">{book.label || (isFixture ? "FIXTURE" : "PAPER")}</span>
      </div>
      <p className="muted">
        {book.note ||
          emptyHint ||
          "Paper ledger. Not live P/L. Win% is historical paper only — not confidence."}
      </p>
      <p className="muted" style={{ fontSize: "0.85em" }}>
        Sort: newest first by time (IST). Spot = underlying index. Entry/SL/Target =
        option premium (or DATA_INSUFFICIENT). Unit: {book.unit || "OPTION_PREMIUM"}.
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

      <BookTable
        rows={rows}
        caption={isFixture ? "FIXTURE demo trades" : "PAPER session trades"}
        emptyMessage={
          isFixture
            ? "No FIXTURE rows."
            : "No PAPER rows yet — FIXTURE demo is separate below. Not a fill."
        }
      />
    </section>
  );
}

/**
 * Customer paper book (PAPER) + optional FIXTURE demo — never clubbed in one table.
 */
export function TodaysBook({ book, fixtureBook }) {
  return (
    <>
      <BookPanel
        book={book}
        headingId="book-heading"
        title="Today's paper book"
        emptyHint="PAPER only. FIXTURE demo is separate. Not live P/L."
      />
      {fixtureBook ? (
        <BookPanel
          book={fixtureBook}
          headingId="fixture-book-heading"
          title="Fixture demo book"
          emptyHint="FIXTURE UI wiring only — not customer paper."
        />
      ) : null}
    </>
  );
}

import { useMemo, useState } from "react";

function byDayDesc(a, b) {
  return String(b || "").localeCompare(String(a || ""));
}

export function flattenExamSpills(exam) {
  return [...(exam?.days || [])]
    .flatMap((d) =>
      (d.spills || []).map((sp, i) => ({
        key: `${d.day}-${sp.room || ""}-${sp.code || ""}-${sp.underlying || ""}-${sp.side || ""}-${i}`,
        day: d.day,
        ...sp,
      })),
    )
    .sort((a, b) => byDayDesc(a.day, b.day));
}

function Field({ label, value, onChange, options }) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt === "ALL" ? `All ${label.toLowerCase()}` : opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SpillLedger({ exam }) {
  const rows = useMemo(() => flattenExamSpills(exam), [exam]);
  const [day, setDay] = useState("ALL");
  const [room, setRoom] = useState("ALL");
  const [why, setWhy] = useState("ALL");
  const [index, setIndex] = useState("ALL");

  const dayOpts = useMemo(() => ["ALL", ...[...new Set(rows.map((r) => r.day).filter(Boolean))].sort(byDayDesc)], [rows]);
  const roomOpts = useMemo(() => ["ALL", ...[...new Set(rows.map((r) => r.room).filter(Boolean))].sort()], [rows]);
  const whyOpts = useMemo(() => ["ALL", ...[...new Set(rows.map((r) => r.code).filter(Boolean))].sort()], [rows]);
  const indexOpts = useMemo(
    () => ["ALL", ...[...new Set(rows.map((r) => r.underlying).filter(Boolean))].sort()],
    [rows],
  );

  const filtered = useMemo(
    () =>
      rows.filter((r) => {
        if (day !== "ALL" && r.day !== day) return false;
        if (room !== "ALL" && r.room !== room) return false;
        if (why !== "ALL" && r.code !== why) return false;
        if (index !== "ALL" && r.underlying !== index) return false;
        return true;
      }),
    [rows, day, room, why, index],
  );

  return (
    <section className="panel spill-panel">
      <div>
        <h2>Why days spilled</h2>
        <p className="muted exam-lead">
          After-hours honesty. Day, room, why it leaked, and how to read it. Newest day first. Not a retune.
        </p>
      </div>

      <div className="filter-row" role="group" aria-label="Filter spill ledger">
        <Field label="Day" value={day} onChange={setDay} options={dayOpts} />
        <Field label="Room" value={room} onChange={setRoom} options={roomOpts} />
        <Field label="Why it spilled" value={why} onChange={setWhy} options={whyOpts} />
        <Field label="Index" value={index} onChange={setIndex} options={indexOpts} />
      </div>

      {rows.length === 0 ? (
        <p className="muted">
          Spill rows appear after a real exam run. ATM-only tape with no ITM fills is a data story, not a hidden win.
        </p>
      ) : (
        <>
          <p className="muted">
            {filtered.length} of {rows.length} rows
          </p>
          <div className="table-scroll table-scroll--spill">
            <table className="book-table desk-grid spill-table">
              <thead>
                <tr>
                  <th className="col-fit">Day</th>
                  <th className="col-fit">Room</th>
                  <th className="col-fit">Why it spilled</th>
                  <th className="cell-wrap">How to think about it</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length ? (
                  filtered.map((sp) => (
                    <tr key={sp.key}>
                      <td className="col-fit">
                        <strong>{sp.day || "—"}</strong>
                        <small>{[sp.underlying, sp.side].filter(Boolean).join(" ") || "—"}</small>
                      </td>
                      <td className="col-fit">{sp.room || "—"}</td>
                      <td className="col-fit">{sp.code || "—"}</td>
                      <td className="cell-wrap">{sp.plain || "—"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="cell-wrap" colSpan={4}>
                      No spill rows in this filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

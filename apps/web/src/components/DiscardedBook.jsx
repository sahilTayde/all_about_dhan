import { useMemo, useState } from "react";
import {
  discardClock,
  discardEventTs,
  discardOutcome,
  discardTradeLabel,
  discardedWho,
  sessionDate,
  skipPlain,
} from "../lib/paperBoard.js";

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

function whyText(g) {
  const head = skipPlain(g.reason || g.vs_picker);
  const extra = g.why || g.detail || g.observation;
  return extra ? `${head} — ${String(extra)}` : head;
}

export function DiscardedBook({ rows, actorCounts }) {
  const list = useMemo(
    () =>
      [...(rows || [])].sort((a, b) => {
        const dt = discardEventTs(b) - discardEventTs(a);
        if (dt) return dt;
        return String(discardClock(b)).localeCompare(String(discardClock(a)));
      }),
    [rows],
  );
  const [day, setDay] = useState("ALL");
  const [who, setWho] = useState("ALL");
  const [out, setOut] = useState("ALL");
  const [index, setIndex] = useState("ALL");

  const dayOpts = useMemo(() => {
    const seen = [...new Set(list.map((r) => sessionDate(discardClock(r))).filter((d) => d && d !== "—"))];
    return ["ALL", ...seen.sort((a, b) => String(b).localeCompare(String(a)))];
  }, [list]);
  const whoOpts = useMemo(() => ["ALL", ...[...new Set(list.map((r) => discardedWho(r)).filter(Boolean))].sort()], [list]);
  const outOpts = useMemo(() => ["ALL", ...[...new Set(list.map((r) => discardOutcome(r)).filter(Boolean))].sort()], [list]);
  const indexOpts = useMemo(
    () => ["ALL", ...[...new Set(list.map((r) => r.underlying).filter(Boolean))].sort()],
    [list],
  );

  const filtered = useMemo(
    () =>
      list.filter((r) => {
        if (day !== "ALL" && sessionDate(discardClock(r)) !== day) return false;
        if (who !== "ALL" && discardedWho(r) !== who) return false;
        if (out !== "ALL" && discardOutcome(r) !== out) return false;
        if (index !== "ALL" && r.underlying !== index) return false;
        return true;
      }),
    [list, day, who, out, index],
  );

  return (
    <section className="panel">
      <h2>Discarded by boss or dealer</h2>
      <p className="muted">
        Tickets and spoken signals not taken. Datetime newest first. Not the live training book.
      </p>
      {actorCounts?.length ? (
        <p className="discard-actors">
          Who acted:{" "}
          {actorCounts.map((a) => (
            <span key={a.who} className="discard-who">
              {a.who} ×{a.n}
            </span>
          ))}
        </p>
      ) : null}

      <div className="filter-row" role="group" aria-label="Filter discarded tickets">
        <Field label="Datetime" value={day} onChange={setDay} options={dayOpts} />
        <Field label="Who" value={who} onChange={setWho} options={whoOpts} />
        <Field label="Outcome" value={out} onChange={setOut} options={outOpts} />
        <Field label="Index" value={index} onChange={setIndex} options={indexOpts} />
      </div>

      {list.length === 0 ? (
        <p className="muted">Nothing discarded on this snapshot.</p>
      ) : (
        <>
          <p className="muted">
            {filtered.length} of {list.length} rows · newest datetime first
          </p>
          <div className="table-scroll table-scroll--discard">
            <table className="book-table desk-grid discard-table">
              <thead>
                <tr>
                  <th className="col-fit">Datetime (IST)</th>
                  <th className="col-fit">Trade</th>
                  <th className="col-fit">Who</th>
                  <th className="col-fit">Outcome</th>
                  <th className="col-fit">Fill</th>
                  <th className="col-fit">Lots</th>
                  <th className="col-fit">Qty</th>
                  <th className="col-fit">Ticket</th>
                  <th className="col-fit">Book</th>
                  <th className="cell-wrap">Why</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length ? (
                  filtered.map((g, i) => (
                    <tr key={g.trade_id || `${g.reason}-${g.underlying}-${g.side || g.seen_side}-${discardClock(g)}-${i}`}>
                      <td className="col-fit discard-time">{discardClock(g)}</td>
                      <td className="col-fit">
                        <strong>{discardTradeLabel(g)}</strong>
                      </td>
                      <td className="col-fit">
                        <span className="discard-who">{discardedWho(g)}</span>
                      </td>
                      <td className="col-fit">{discardOutcome(g)}</td>
                      <td className="col-fit">{g.filled === true ? "yes" : "no"}</td>
                      <td className="col-fit num">{g.lots ?? "—"}</td>
                      <td className="col-fit num">{g.qty ?? "—"}</td>
                      <td className="col-fit">{g.trade_id || "none"}</td>
                      <td className="col-fit">{g.book_id || g.source || "—"}</td>
                      <td className="cell-wrap">{whyText(g)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="cell-wrap" colSpan={10}>
                      No discarded rows in this filter.
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

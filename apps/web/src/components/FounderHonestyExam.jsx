function examTone(honesty) {
  if (honesty === "CLEAN") return "done";
  if (honesty === "PEEKED") return "pending";
  return "in_progress";
}

function voteClass(honesty) {
  if (honesty === "CLEAN") return "is-clean";
  if (honesty === "PEEKED") return "is-peeked";
  return "is-wait";
}

function byDayDesc(a, b) {
  return String(b || "").localeCompare(String(a || ""));
}

function storyDay(text) {
  const m = String(text || "").match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : "";
}

function scrollRailSideways(e) {
  const el = e.currentTarget;
  if (el.scrollWidth <= el.clientWidth) return;
  if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
  el.scrollLeft += e.deltaY;
  e.preventDefault();
}

export function FounderHonestyExam({ exam }) {
  const days = [...(exam?.days || [])].sort((a, b) => byDayDesc(a.day, b.day));
  const stories = (days.some((d) => d.story)
    ? days.map((d) => d.story).filter(Boolean)
    : [...(exam?.stories || [])].sort((a, b) => byDayDesc(storyDay(a), storyDay(b))));
  const watch = exam?.watch_next || [];
  const spills = days
    .flatMap((d) =>
      (d.spills || []).slice(0, 8).map((sp, i) => ({
        key: `${d.day}-${i}`,
        day: d.day,
        ...sp,
      }))
    )
    .sort((a, b) => byDayDesc(a.day, b.day));

  return (
    <section className="panel exam-panel">
      <div className="exam-head">
        <div>
          <h2>Honesty exam (06)</h2>
          <p className="muted exam-lead">After-hours grade. Last on this page so it never sits on the live book.</p>
        </div>
        <div className="exam-head__pills">
          <span className={`cleanup-pill ${examTone(exam?.overall_honesty)}`}>
            {exam?.overall_honesty || "no file yet"}
          </span>
          <span className="cleanup-pill pending">NO_PROMOTE</span>
        </div>
      </div>

      <p className="exam-headline">{exam?.headline || exam?.reason || "Run the exam to fill this box."}</p>
      <p className="muted exam-rail-hint">Newest day first. Scroll the bar under the boxes, or roll the wheel over them.</p>

      <div
        className="exam-days-rail"
        tabIndex={0}
        aria-label="Exam days, newest first, scroll sideways"
        onWheel={scrollRailSideways}
      >
        {days.length ? (
          days.map((row) => (
            <article key={row.day} className={`exam-day-card ${voteClass(row.honesty)}`}>
              <header>
                <span>{row.day}</span>
                <strong>{row.honesty || "—"}</strong>
              </header>
              <dl>
                <div>
                  <dt>SOD closes</dt>
                  <dd>{row.n_sod_closed ?? "—"}</dd>
                </div>
                <div>
                  <dt>Peeked</dt>
                  <dd>{row.n_peeked_slices ?? 0}</dd>
                </div>
                <div>
                  <dt>Contract fail</dt>
                  <dd>{row.n_fill_contract_fail ?? 0}</dd>
                </div>
              </dl>
              <p>{row.story}</p>
            </article>
          ))
        ) : (
          <article className="exam-day-card is-wait">
            <header>
              <span>No days</span>
              <strong>—</strong>
            </header>
            <p>Run python -m desk_ml sod-exam after close.</p>
          </article>
        )}
      </div>

      <div className="exam-notes">
        <div className="exam-notes__col">
          <h3>Day stories</h3>
          <p className="muted">Newest date first.</p>
          <ul className="exam-notes__scroll">
            {stories.length ? (
              stories.map((s, i) => (
                <li key={`${i}-${String(s).slice(0, 24)}`}>{s}</li>
              ))
            ) : (
              <li className="muted">Stories appear after a real exam run.</li>
            )}
          </ul>
        </div>
        <div className="exam-notes__col">
          <h3>Watch next</h3>
          <ul className="exam-notes__scroll">
            {watch.length ? (
              watch.map((w) => <li key={w}>{w}</li>)
            ) : (
              <li className="muted">No watch list. One bad day is not a retune.</li>
            )}
          </ul>
        </div>
      </div>

      <details className="desk-context exam-contract" open>
        <summary>Fill contract (plain English)</summary>
        <p className="muted">
          {exam?.contract?.plain ||
            "Decide after a finished 1-minute bar. Never book ATM and call it ITM."}
        </p>
        <p className="muted exam-rail-hint">One card per exam day. Newest date first.</p>
        <div className="exam-contract-grid">
          {days.length ? (
            days.map((row) => (
              <article key={`contract-${row.day}`} className={voteClass(row.honesty)}>
                <header>
                  <span>{row.day}</span>
                  <strong>{row.n_fill_contract_fail ? "FAIL" : "OK"}</strong>
                </header>
                <p>
                  <b>{row.fill_contract || exam?.contract?.id || "—"}</b>
                </p>
                <p>{row.tape_note || "No tape note."}</p>
                <p>
                  Fails {row.n_fill_contract_fail ?? 0} · {row.session_kind || "—"}
                </p>
              </article>
            ))
          ) : (
            <article className="is-wait">
              <header>
                <span>No days</span>
                <strong>—</strong>
              </header>
              <p>Run the exam to grade the fill contract per day.</p>
            </article>
          )}
        </div>
      </details>

      {spills.length ? (
        <div className="table-scroll table-scroll--exam">
          <table className="book-table">
            <thead>
              <tr>
                <th>Day</th>
                <th>Room</th>
                <th>Why it spilled</th>
                <th>How to think about it</th>
              </tr>
            </thead>
            <tbody>
              {spills.map((sp) => (
                <tr key={sp.key}>
                  <td>
                    {sp.day} {sp.underlying} {sp.side}
                  </td>
                  <td>{sp.room}</td>
                  <td>{sp.code}</td>
                  <td>{sp.plain}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">
          Spill rows appear after a real exam run. ATM-only tape with no ITM fills is a data story, not a hidden win.
        </p>
      )}
    </section>
  );
}

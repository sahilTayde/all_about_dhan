function voteTone(vote) {
  const v = String(vote || "").toUpperCase();
  if (v === "CE" || v === "CALL") return "ce";
  if (v === "PE" || v === "PUT") return "pe";
  if (v === "HOLD") return "hold";
  return "silent";
}

function killTone(flag) {
  const v = String(flag || "").toUpperCase();
  if (v === "CONFIRM") return "ce";
  if (v === "KILL") return "pe";
  return "silent";
}

export function FounderRoster({ catalog, confirmKill }) {
  const models = catalog?.models || [];
  const strats = catalog?.strategies || [];
  const inds = catalog?.indicators || [];
  const rooms = catalog?.rooms || [];
  const spenders = models.filter((m) => m.capital);
  const voters = models.filter((m) => !m.capital);

  return (
    <section className="panel roster-panel">
      <div className="roster-head">
        <div>
          <h2>Who speaks, who spends</h2>
          <p className="muted">
            Read this as a factory line. Rooms vote. Only the desk spends paper money. KEEP_ALL. UNVALIDATED.
          </p>
        </div>
      </div>

      <ol className="roster-flow" aria-label="How a paper ticket is built">
        {rooms.map((r, i) => (
          <li key={r.id} className={r.id === "MIX-DEFAULT-BUY" ? "is-spend" : ""}>
            <em>{i + 1}</em>
            <strong>{r.name}</strong>
            <p>{r.role}</p>
          </li>
        ))}
      </ol>

      <div className="roster-split">
        <div className="roster-col">
          <h3>Spends paper money</h3>
          <p className="muted">Customer-default book. One ITM fill when SOD is on.</p>
          <div className="roster-card-rail" tabIndex={0} aria-label="Books that spend, scroll sideways">
            {spenders.length ? (
              spenders.map((m) => (
                <article key={m.id} className="roster-card is-fill">
                  <span>{m.kind}</span>
                  <strong>{m.id}</strong>
                  <p>{m.what}</p>
                  <b>SPENDS</b>
                </article>
              ))
            ) : (
              <p className="muted">No spend book on the catalog.</p>
            )}
          </div>
        </div>
        <div className="roster-col">
          <h3>Votes only · no capital</h3>
          <p className="muted">They speak CE / PE / HOLD. The desk can ignore them.</p>
          <div className="roster-card-rail" tabIndex={0} aria-label="Voting models, scroll sideways">
            {voters.map((m) => (
              <article key={m.id} className="roster-card">
                <span>{m.kind}</span>
                <strong>{m.id}</strong>
                <p>{m.what}</p>
                <b>VOTE</b>
              </article>
            ))}
          </div>
        </div>
      </div>

      <div className="roster-block">
        <h3>STRAT-001–014 · KEEP_ALL</h3>
        <p className="muted">Silent is not deleted. DATA_INSUFFICIENT stays on the book.</p>
        <div className="roster-card-rail roster-card-rail--tall" tabIndex={0} aria-label="Strategies, scroll sideways">
          {strats.map((s) => (
            <article key={s.id} className="roster-card roster-card--strat">
              <span>{s.id}</span>
              <strong>{s.name}</strong>
              <em className={`roster-vote roster-vote--${voteTone(s.vote)}`}>{s.vote || "—"}</em>
            </article>
          ))}
        </div>
      </div>

      <div className="roster-block">
        <h3>Indicators · confirm or kill</h3>
        <p className="muted">{confirmKill?.note || "5m lights never open a ticket. KILL holds."}</p>
        <div className="roster-ind-grid">
          {inds.map((i) => (
            <article key={i.id}>
              <strong>{i.name}</strong>
              <p>{i.use}</p>
              {confirmKill?.[i.id] ? (
                <em className={`roster-vote roster-vote--${killTone(confirmKill[i.id])}`}>{confirmKill[i.id]}</em>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

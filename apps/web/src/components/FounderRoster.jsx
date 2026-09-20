export function FounderRoster({ catalog, confirmKill }) {
  const models = catalog?.models || [];
  const strats = catalog?.strategies || [];
  const inds = catalog?.indicators || [];
  const rooms = catalog?.rooms || [];

  return (
    <section className="panel">
      <h2>Rooms, models, strategies, indicators</h2>
      <p className="muted">Everything on the book today. SOD uses one desk fill. KEEP_ALL. UNVALIDATED.</p>
      <div className="roster-rooms">
        {rooms.map((r) => (
          <article key={r.id}>
            <strong>{r.name}</strong>
            <p>{r.role}</p>
          </article>
        ))}
      </div>
      <div className="roster-grid">
        {models.map((m) => (
          <article key={m.id} className={m.capital ? "is-fill" : ""}>
            <span>{m.kind}</span>
            <strong>{m.id}</strong>
            <p>{m.what}</p>
          </article>
        ))}
      </div>
      <details className="desk-context">
        <summary>STRAT-001–014 votes (KEEP_ALL · silent if DATA_INSUFFICIENT)</summary>
        <div className="book-table-wrap">
          <table className="book-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Vote now</th>
              </tr>
            </thead>
            <tbody>
              {strats.map((s) => (
                <tr key={s.id}>
                  <td>{s.id}</td>
                  <td>{s.name}</td>
                  <td>{s.vote}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <details className="desk-context">
        <summary>Indicators (5m = confirm/kill only · Dhan official set)</summary>
        <ul className="ind-list">
          {inds.map((i) => (
            <li key={i.id}>
              <strong>{i.name}</strong>
              <span>{i.use}</span>
              {confirmKill?.[i.id] ? <em>{confirmKill[i.id]}</em> : null}
            </li>
          ))}
        </ul>
        {confirmKill?.note ? <p className="muted">{confirmKill.note}</p> : null}
      </details>
    </section>
  );
}

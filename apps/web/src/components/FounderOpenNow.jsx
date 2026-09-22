import { deskLifeStatus, moneyClass, pathInfo, px } from "../lib/paperBoard.js";

export function FounderOpenNow({ opens }) {
  const rows = opens || [];
  return (
    <section className="panel founder-open-now">
      <div className="panel__head">
        <div>
          <h2>Now open</h2>
          <p className="muted">Live paper ticket. Shows here the second the board writes it — not only after a close.</p>
        </div>
        <span className={`cleanup-pill ${rows.length ? "in_progress" : "pending"}`}>
          {rows.length ? `${rows.length} OPEN` : "none open"}
        </span>
      </div>
      {rows.length ? (
        <div className="founder-open-grid">
          {rows.map((t) => {
            const p = pathInfo(t);
            const life = deskLifeStatus(t);
            return (
              <article key={t.trade_id} className="founder-open-card">
                <header>
                  <span className={`side-mini side-mini--${String(t.side).toLowerCase()}`}>{t.side}</span>
                  <strong>
                    {t.underlying} {t.atm_strike}
                  </strong>
                  <em>{life}</em>
                </header>
                <dl>
                  <div>
                    <dt>Entry</dt>
                    <dd>{px(p.entry)}</dd>
                  </div>
                  <div>
                    <dt>Now</dt>
                    <dd className={moneyClass(p.vsEntry)}>{px(p.last)}</dd>
                  </div>
                  <div>
                    <dt>Stop</dt>
                    <dd>{px(p.stop)}</dd>
                  </div>
                  <div>
                    <dt>Target</dt>
                    <dd>{px(p.target)}</dd>
                  </div>
                  <div>
                    <dt>Pts</dt>
                    <dd className={moneyClass(p.vsEntry)}>
                      {p.vsEntry == null ? "—" : p.vsEntry.toFixed(1)}
                    </dd>
                  </div>
                </dl>
                <p>
                  Opened {String(t.opened_ist || "").replace("T", " ").slice(0, 19) || "—"} ·{" "}
                  {(t.books || [t.book_id]).filter(Boolean).join(" · ") || "MIX-DEFAULT-BUY"}
                </p>
              </article>
            );
          })}
        </div>
      ) : (
        <p className="muted">No open MIX-DEFAULT-BUY. Next CE/PE will land in this box while it is live.</p>
      )}
    </section>
  );
}

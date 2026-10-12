import { STRATEGIES, inr, num, tone } from "../lib/deskModel.js";
import { randomBaseline } from "../lib/strategyBoard.js";

export function StrategiesPage({ snap, dd }) {
  const rank = snap?.board?.book_rank || [];
  const today = dd.byBook || {};
  const rows = STRATEGIES.filter((s) => s.id !== "B2" || today.B2 || rank.some((r) => r.book_id === "B2"));
  return (
    <div className="strategies" data-testid="strategies-page">
      {rows.map((s) => {
        const b = today[s.id];
        const charges = dd.closed.filter((t) => t.book_id === s.id).reduce((x, t) => x + (num(t.charges_inr) || 0), 0);
        const r = rank.find((x) => x.book_id === s.id);
        const rnd = randomBaseline(r, snap?.board?.scoreboard, s.id);
        const wr = b?.n ? (b.wins / b.n) * 100 : null;
        return (
          <section key={s.id} className="card strat-card">
            <header className="card__head"><h2>{s.name}</h2><span className={`badge badge--${s.state.toLowerCase()}`}>{s.state}{s.note ? ` · ${s.note}` : ""}</span></header>
            <p className="strat-card__line">
              Today: <strong>{b?.n ?? 0}</strong> trades, <strong>{b?.wins ?? 0}</strong> won, net <strong className={tone(b?.net)}>{inr(b?.net)}</strong> after {inr(charges, { signed: false })} charges.
            </p>
            <p className="muted small">
              Vs random entries: {rnd == null || wr == null ? "not recorded yet" : `${wr - rnd >= 0 ? "+" : ""}${(wr - rnd).toFixed(1)} pts win rate (random ${rnd.toFixed(1)}%)`}
            </p>
            <p className="muted small">{s.id}</p>
          </section>
        );
      })}
    </div>
  );
}

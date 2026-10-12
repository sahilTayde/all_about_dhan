import { CHARGES_LABEL, STRATEGIES, deskStatusOf, inr, num, strategyName, tone } from "../lib/deskModel.js";
import { randomBaseline } from "../lib/strategyBoard.js";

export function StrategiesPage({ snap, dd }) {
  const L = dd.lists;
  const rows = [...dd.open, ...dd.closed, ...L.parked, ...L.blocked, ...L.dups, ...L.riskBlocked];
  const ids = [...new Set([...STRATEGIES.map((s) => s.id), ...rows.map((r) => r.book_id).filter(Boolean)])].filter((id) => rows.some((r) => r.book_id === id) || L.parkedIds.includes(id));
  const rank = snap?.board?.book_rank || [];
  const scored = ids.map((id) => {
    const t = rows.filter((r) => r.book_id === id && (dd.closed.includes(r)) && deskStatusOf(r) === "TRADED");
    return { id, net: t.reduce((s, r) => s + (num(r.realized_pnl_inr) || 0), 0), n: t.length };
  }).sort((a, b) => (b.n ? b.net : -1e12) - (a.n ? a.net : -1e12));
  ids.sort((a, b) => scored.findIndex((x) => x.id === a) - scored.findIndex((x) => x.id === b));
  return (
    <div className="page strat-grid" data-testid="strategies-page">
      {ids.map((id, rankIdx) => {
        const mine = rows.filter((r) => r.book_id === id);
        const traded = mine.filter((r) => deskStatusOf(r, dd.closed.includes(r) || dd.open.includes(r) ? "TRADED" : "SHADOW_PARKED") === "TRADED" && r.closed_ts != null);
        const net = traded.reduce((s, r) => s + (num(r.realized_pnl_inr) || 0), 0);
        const ch = traded.reduce((s, r) => s + (num(r.charges_inr) || 0), 0);
        const wins = traded.filter((r) => (num(r.realized_pnl_inr) || 0) > 0).length;
        const shadow = mine.filter((r) => L.parked.includes(r)).length;
        const blocked = mine.filter((r) => L.blocked.includes(r) || L.dups.includes(r) || L.riskBlocked.includes(r)).length;
        const r = rank.find((x) => x.book_id === id);
        const rnd = randomBaseline(r, snap?.board?.scoreboard, id);
        const wr = traded.length ? (wins / traded.length) * 100 : null;
        return (
          <section key={id} className="panel strat">
            <header className="panel__head"><h2 title={id}><span className="rank num">#{rankIdx + 1}</span> {strategyName(id)}</h2>{L.parkedIds.includes(id) ? <span className="tag tag--muted">shadow only</span> : traded.length ? <span className="tag tag--ok">traded</span> : null}</header>
            <div className="strat__big"><b className={`num ${tone(net)}`}>{traded.length ? inr(net) : "—"}</b><span className="muted">net today after {inr(ch, { signed: false })} charges ({CHARGES_LABEL})</span></div>
            <p className="strat__line"><b className="num">{traded.length}</b> trades · <b className="num">{wins}</b> won · {shadow} shadow · {blocked} blocked/dup</p>
            <p className="muted small">Vs random entries: {rnd == null || wr == null ? "—" : `${wr - rnd >= 0 ? "+" : ""}${(wr - rnd).toFixed(1)} pts win rate`}</p>
          </section>
        );
      })}
    </div>
  );
}

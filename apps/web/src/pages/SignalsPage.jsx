import { Fragment, useState } from "react";
import { deskStatusOf, exitRule, hhmm, inr, num, researchToday, strategyName, strikeOf, tone } from "../lib/deskModel.js";
import { Side, TradeTable } from "./parts.jsx";

/** Plain status for one fire. Only desk_status / guard values the backend writes (research_rules.py, desk_risk.py). */
const BLOCK_WHY = {
  BLOCKED_OPPOSITE_SIDE: "opposite side",
  RISK_CAP_QTY: "10-lot cap",
  DUP_SAME_CONTRACT: "duplicate",
  RISK_DAY_STOP: "risk limit: day stop",
  RISK_CAP_OPEN: "risk limit: max open",
  RISK_CAP_TRADES: "risk limit: trade cap",
  RISK_STALE_PRICES: "risk limit: stale prices",
  RISK_BLOCKED: "risk limit",
  SHADOW_PARKED: "shadow only",
};

function fireStatus(r, fb) {
  const code = String(fb || r.desk_status || r.guard || "TRADED").toUpperCase();
  if (code === "TRADED") return { taken: true, text: "taken", code };
  return { taken: false, text: `blocked: ${BLOCK_WHY[code] || code.replace(/_/g, " ").toLowerCase()}`, code };
}

const timeOf = (r) => r.sig_min || r.entry_min || hhmm(r.opened_ist) || "";

/** One row per strategy + index; repeat fires update the row with the latest values. */
export function groupByStrategy(fires) {
  const map = new Map();
  for (const f of fires) {
    const r = f.r;
    const key = `${r.book_id || r.rule_id || "—"}|${r.underlying || "—"}`;
    const g = map.get(key) || { key, id: r.book_id || r.rule_id, und: r.underlying, fires: [] };
    g.fires.push(f);
    map.set(key, g);
  }
  return [...map.values()].map((g) => {
    g.fires.sort((a, b) => timeOf(b.r).localeCompare(timeOf(a.r)));
    g.latest = g.fires[0];
    return g;
  }).sort((a, b) => timeOf(b.latest.r).localeCompare(timeOf(a.latest.r)));
}

function Cells({ r, fb }) {
  const st = fireStatus(r, fb);
  const rule = exitRule(r);
  return (
    <>
      <td><Side side={r.side} /></td>
      <td className="r num">{strikeOf(r) ?? "—"}</td>
      <td className="r num">{num(r.spot_at_entry) ?? "—"}</td>
      <td className="r num">{num(r.entry) ?? "—"}</td>
      <td className="num small">{num(r.stop) != null ? num(r.stop) : rule.kind === "time" ? `time exit ${rule.at || "20 min"}` : "—"}</td>
      <td><span className={`tag tag--${st.taken ? "ok" : st.code === "SHADOW_PARKED" ? "muted" : "warn"}`} title={st.code}>{st.text}</span>{st.taken && num(r.realized_pnl_inr) != null ? <b className={`num small ${tone(r.realized_pnl_inr)}`}> {inr(r.realized_pnl_inr)}</b> : null}</td>
      <td className="num">{timeOf(r) || "—"}</td>
    </>
  );
}

export function SignalsPage({ dd }) {
  const L = dd.lists;
  const rt = researchToday(dd);
  const fires = [
    ...rt.cls.map((c) => ({ r: c.r, fb: c.code })),
    ...L.parked.map((r) => ({ r, fb: "SHADOW_PARKED" })),
    ...L.blocked.map((r) => ({ r, fb: "BLOCKED_OPPOSITE_SIDE" })),
    ...L.dups.map((r) => ({ r, fb: "DUP_SAME_CONTRACT" })),
    ...L.riskBlocked.map((r) => ({ r, fb: "RISK_BLOCKED" })),
  ];
  const groups = groupByStrategy(fires);
  const [open, setOpen] = useState({});
  return (
    <div className="page" data-testid="signals-page">
      <div className="kpis" data-testid="signals-summary">
        <div><span>Research desk today</span><b className={`num ${tone(rt.net)}`}>{inr(rt.net)}</b><em>traded rows only · after {inr(rt.charges, { signed: false })} charges · {dd.day || "—"}</em></div>
        <div><span>Trades counted</span><b className="num">{rt.n}</b><em>{rt.wins} won{rt.open ? ` · ${rt.open} open` : ""}</em></div>
        <div><span>Fires today</span><b className="num">{fires.length}</b><em>{rt.n} traded + {fires.length - rt.n} not counted (shadow / blocked / duplicate{rt.notCountedNet ? `, ${inr(rt.notCountedNet)}` : ""})</em></div>
        <div><span>Old MIX book</span><b className={`num ${tone(dd.mix.net)}`}>{inr(dd.mix.net)}</b><em>{dd.mix.trades} trades · not in this page</em></div>
      </div>
      <section className="panel">
        <header className="panel__head"><h2>Signals by strategy</h2><span className="muted">one row per strategy and index · latest fire shown · click ▸ for every fire today</span></header>
        {groups.length ? (
          <div className="tbl-wrap">
            <table className="tbl sigtbl" data-testid="signals-by-strategy">
              <thead><tr><th /><th>Strategy</th><th>Index</th><th>Side</th><th className="r">Strike</th><th className="r">Spot</th><th className="r">Entry</th><th>Stop / exit rule</th><th>Status</th><th>Latest</th><th className="r">Fires today</th></tr></thead>
              <tbody>
                {groups.map((g) => (
                  <Fragment key={g.key}>
                    <tr onClick={() => setOpen((o) => ({ ...o, [g.key]: !o[g.key] }))}>
                      <td className="arrow">{open[g.key] ? "▾" : "▸"}</td>
                      <td title={g.id}><b>{strategyName(g.id)}</b></td>
                      <td><b>{g.und}</b></td>
                      <Cells r={g.latest.r} fb={g.latest.fb} />
                      <td className="r num"><b>{g.fires.length}</b>{g.fires.some((f) => f.fb !== "TRADED") ? <span className="muted small"> ({g.fires.filter((f) => f.fb === "TRADED").length} counted)</span> : null}</td>
                    </tr>
                    {open[g.key] ? g.fires.map((f, i) => (
                      <tr key={`${g.key}|${f.r.trade_id}|${i}`} className="sub">
                        <td /><td className="muted small">fire {g.fires.length - i}</td><td />
                        <Cells r={f.r} fb={f.fb} />
                        <td />
                      </tr>
                    )) : null}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="empty">No research signals yet today.</div>}
      </section>
      <details className="panel details">
        <summary>Details: full raw list of every fire ({fires.length}: {rt.n} counted, {fires.length - rt.n} not counted)</summary>
        <TradeTable rows={fires.map((f) => ({ ...f.r, desk_status: f.fb }))} kind="desk" />
      </details>
    </div>
  );
}

export { deskStatusOf };

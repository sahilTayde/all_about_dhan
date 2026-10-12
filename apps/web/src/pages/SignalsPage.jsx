import { useState } from "react";
import { signalWhy, DESK_STATUS, deskStatusOf, hhmm, inr, num, strikeOf, tone } from "../lib/deskModel.js";
import { Reason, Side, Strat } from "./parts.jsx";

const WHY = {
  TRADED: "Desk took it on paper.",
  SHADOW_PARKED: "Strategy is parked: tracked, not traded, not in P&L.",
  BLOCKED_OPPOSITE_SIDE: "Skipped: the desk already held the other index on the opposite side.",
  DUP_SAME_CONTRACT: "Same contract and minute as another strategy's trade; counted once.",
};

function Card({ r, fb }) {
  const s = deskStatusOf(r, fb);
  const taken = s === "TRADED";
  const ce = String(r.side).toUpperCase() === "CE";
  const pnl = num(r.realized_pnl_inr);
  return (
    <article className={`sig sig--${s.toLowerCase()} ${ce ? "sig--ce" : "sig--pe"}`} data-testid="signal-card">
      <header>
        <span className="sig__dir">{ce ? "▲ Buy Call" : "▼ Buy Put"}</span>
        <span className={`tag tag--${DESK_STATUS[s].tone}`}>{DESK_STATUS[s].text}</span>
      </header>
      <div className="sig__sym"><b>{r.underlying}</b> <span className="num">{strikeOf(r) ?? "—"}</span> <Side side={r.side} /></div>
      <dl className="sig__kv">
        <div><dt>Time</dt><dd className="num">{r.sig_min || r.entry_min || hhmm(r.opened_ist) || "—"} IST</dd></div>
        <div><dt>Strategy</dt><dd><Strat id={r.book_id || r.rule_id} /></dd></div>
        <div><dt>Confidence</dt><dd className="num">{num(r.confidence) ?? num(r.score) ?? "—"}</dd></div>
        {taken || s === "SHADOW_PARKED" ? <div><dt>Result</dt><dd className={`num ${tone(pnl)}`}>{pnl == null ? (r.closed_ts ? "—" : "open") : inr(pnl)}</dd></div> : null}
      </dl>
      <p className="sig__why"><b>Why:</b> {signalWhy(r)}</p>
      <p className="sig__why">{r.dup_of ? `${WHY[s]} (duplicate of ${r.dup_of})` : WHY[s]}{r.exit_reason && s !== "BLOCKED_OPPOSITE_SIDE" ? <> · <Reason code={r.exit_reason} /></> : null}</p>
    </article>
  );
}

export function SignalsPage({ snap, dd }) {
  const L = dd.lists;
  const groups = [
    { id: "all", label: "All" },
    { id: "TRADED", label: "Traded" },
    { id: "SHADOW_PARKED", label: "Shadow only" },
    { id: "BLOCKED_OPPOSITE_SIDE", label: "Blocked" },
    { id: "DUP_SAME_CONTRACT", label: "Duplicate" },
  ];
  const rows = [
    ...[...dd.open, ...dd.closed].filter((t) => t.research_rule || t.desk_status).map((r) => ({ r, fb: "TRADED" })),
    ...L.parked.map((r) => ({ r, fb: "SHADOW_PARKED" })),
    ...L.blocked.map((r) => ({ r, fb: "BLOCKED_OPPOSITE_SIDE" })),
    ...L.dups.map((r) => ({ r, fb: "DUP_SAME_CONTRACT" })),
  ].sort((a, b) => String(b.r.sig_min || b.r.entry_min || "").localeCompare(String(a.r.sig_min || a.r.entry_min || "")));
  const [f, setF] = useState("all");
  const shown = rows.filter((x) => f === "all" || deskStatusOf(x.r, x.fb) === f);
  const count = (id) => rows.filter((x) => deskStatusOf(x.r, x.fb) === id).length;
  const journal = (snap?.board?.decision_journal || []).filter((j) => j.stage === "boss").slice(0, 12);
  return (
    <div className="page" data-testid="signals-page">
      <div className="seg seg--lg">
        {groups.map((g) => <button key={g.id} type="button" className={f === g.id ? "is-on" : ""} onClick={() => setF(g.id)}>{g.label} <span className="num muted">{g.id === "all" ? rows.length : count(g.id)}</span></button>)}
      </div>
      {shown.length ? <div className="sig-grid">{shown.map((x) => <Card key={`${x.r.trade_id}|${x.fb}`} r={x.r} fb={x.fb} />)}</div> : <div className="panel empty">No research signals today{L.blocked.length + L.parked.length + L.dups.length === 0 ? " (the shadow / blocked lists arrive after the backend restart)" : ""}.</div>}
      <details className="panel details">
        <summary>Details: old MIX desk decisions (boss stage, latest {journal.length})</summary>
        <ul className="jrnl">
          {journal.map((j, i) => (
            <li key={i}><span className="num muted">{String(j.ts_ist || "").slice(11, 16)}</span> <b>{j.underlying}</b> <Side side={j.inputs?.side} /> <span className={`tag tag--${j.decision === "pass" ? "ok" : "muted"}`}>{j.decision === "pass" ? "picked" : "skipped"}</span> <span className="muted">{j.reason}</span></li>
          ))}
        </ul>
      </details>
    </div>
  );
}

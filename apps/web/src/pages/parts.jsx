import { levelsOf, signalWhy, DESK_STATUS, deskStatusOf, exitRule, flagsOf, fmtAge, hhmm, inr, num, pctOf, pctText, reasonInfo, strategyName, strikeOf, tone } from "../lib/deskModel.js";

export function Reason({ code }) {
  const r = reasonInfo(code);
  return <span className={`tag tag--${r.tone}`} title={code || ""}>{r.text}</span>;
}

export function StatusTag({ row, fallback }) {
  const s = deskStatusOf(row, fallback);
  return <span className={`tag tag--${DESK_STATUS[s].tone}`} title={s}>{DESK_STATUS[s].text}</span>;
}

export const Strat = ({ id }) => <span className="strat" title={id || ""}>{strategyName(id)}</span>;

export function Side({ side }) {
  const s = String(side || "").toUpperCase();
  return <span className={`side side--${s === "CE" ? "ce" : s === "PE" ? "pe" : "na"}`}>{s || "—"}</span>;
}

/** Trade table. `kind`: desk | shadow | blocked (blocked rows never show an exit price or P&L). */
export function TradeTable({ rows, kind = "desk", onPick, picked, fallback }) {
  if (!rows?.length) return <div className="empty">{kind === "blocked" ? "No blocked signals." : kind === "shadow" ? "No shadow trades." : "No trades yet today."}</div>;
  const blocked = kind === "blocked";
  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>Time</th><th>Contract</th><th>Strategy</th>
            {blocked ? <th>Why</th> : <><th className="r">Buy</th><th className="r">Exit</th><th className="r">P&amp;L</th><th className="r">%</th><th>Stop / Target</th><th>Exit reason</th></>}
            {blocked ? null : <th>Why taken</th>}<th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            const pnl = num(t.realized_pnl_inr);
            const px = num(t.exit) ?? num(t.last_ltp);
            return (
              <tr key={`${t.trade_id}|${t.desk_status || ""}`} className={picked === t.trade_id ? "is-picked" : ""} onClick={onPick ? () => onPick(t.trade_id) : undefined}>
                <td className="num muted">{t.entry_min || hhmm(t.opened_ist) || "—"}{t.closed_ist || t.exit_min ? `–${hhmm(t.closed_ist) || t.exit_min}` : ""}</td>
                <td><b>{t.underlying}</b> <span className="num">{strikeOf(t) ?? "—"}</span> <Side side={t.side} /></td>
                <td><Strat id={t.book_id || t.rule_id} /></td>
                {blocked ? (
                  <td className="muted">{t.dup_of ? `same contract as ${t.dup_of}` : /^RISK/.test(String(t.desk_status || t.guard || fallback || "")) ? `risk limit: ${({ RISK_DAY_STOP: "day stopped: loss limit", RISK_CAP_OPEN: "max open trades reached", RISK_CAP_TRADES: "trade cap reached" })[String(t.desk_status || t.guard || "").toUpperCase()] || "limit reached"}` : "desk already held the other index on the opposite side"}</td>
                ) : (
                  <>
                    <td className="r num">{num(t.entry) ?? "—"}</td>
                    <td className="r num">{px ?? "—"}</td>
                    <td className={`r num ${tone(pnl)}`}>{inr(pnl)}</td>
                    <td className={`r num ${tone(pnl)}`}>{pctText(pctOf(t.entry, px))}</td>
                    <td><Levels t={t} /></td>
                    <td>{t.exit_reason ? <Reason code={t.exit_reason} /> : <span className="muted">{exitRule(t).text}</span>} {flagsOf(t).map((f, i) => <Reason key={`${f}|${i}`} code={f} />)}</td>
                  </>
                )}
                {blocked ? null : <td className="muted why">{signalWhy(t)}</td>}
                <td><StatusTag row={t} fallback={fallback} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function AlertList({ alerts }) {
  if (!alerts?.length) return <div className="empty">No alerts.</div>;
  return (
    <ul className="alerts">
      {alerts.map((a) => (
        <li key={`${a.id}|${a.ts || ""}`} className={`alert alert--${String(a.severity || "").toLowerCase()}`}>
          <b>{a.severity}</b> <span>{a.title}</span> <em className="muted">{fmtAge(a.age)}{a.age != null && a.age > 86400 ? " · old" : ""}</em>
          <p>{a.detail}</p>
        </li>
      ))}
    </ul>
  );
}

export function FeedAges({ rows }) {
  return (
    <ul className="feeds">
      {rows.map((r) => (
        <li key={r.name} className={r.stale ? "is-stale" : ""}>
          <span>{r.name}</span>
          <span className="num">{r.sec == null ? "—" : fmtAge(r.sec)}</span>
          {r.stale ? <span className="tag tag--warn">stale &gt; 5 min</span> : null}
        </li>
      ))}
    </ul>
  );
}

/** Plain words for exit_reason_std (closed rows). */
export const EXIT_STD = { STOP: "stop hit", TARGET: "target hit", TIME: "time exit", RULE_EXIT: "rule exit", OPEN: "open" };
/** stop_target_basis as plain words: text is shown as sent, CODE_LIKE becomes "code like". */
const basisText = (b) => (b == null || b === "" ? null : /^[A-Z0-9_]+$/.test(String(b)) ? String(b).toLowerCase().replace(/_/g, " ") : String(b));
const tm = (v) => (v ? hhmm(v) || String(v) : null);

/** Stop / Target / planned exit from the desk feed only. Nothing is computed; every field optional. */
export function Levels({ t, timeKey = "spec_exit_min", timeLabel = "Exit: time" }) {
  const L = levelsOf(t);
  const planned = tm(t?.planned_exit_ist) || tm(t?.[timeKey]);
  const basis = basisText(t?.stop_target_basis);
  const std = t?.exit_reason_std ? EXIT_STD[String(t.exit_reason_std).toUpperCase()] || basisText(t.exit_reason_std) : null;
  const parts = [];
  if (L.stop != null) parts.push(<span key="s">Stop <b className="num">₹{L.stop}</b>{L.stopPct != null ? <em className="muted"> {pctText(L.stopPct)}</em> : null}</span>);
  if (L.target != null) parts.push(<span key="t">Target <b className="num">₹{L.target}</b>{L.targetPct != null ? <em className="muted"> {pctText(L.targetPct)}</em> : null}</span>);
  if (planned) parts.push(<span key="p">{timeLabel} <b className="num">{planned}</b></span>);
  if (L.stop == null && L.target == null) parts.push(<span key="b" className="muted">{basis || (planned ? "no price stop (exits on time)" : "no stop/target sent")}</span>);
  if (std) parts.push(<span key="r">→ <b>{std}</b></span>);
  return <span className="levels small">{parts.flatMap((x, i) => (i ? [" · ", x] : [x]))}</span>;
}

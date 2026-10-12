import { RULES, exitRule, flagsOf, fmtAge, hhmm, inr, num, reasonInfo, strategyName, strikeOf, tone } from "../lib/deskModel.js";

export function Reason({ code }) {
  const r = reasonInfo(code);
  return <span className={`reason reason--${r.tone}`} title={code || ""}>{r.text}</span>;
}

export function TradeLine({ t }) {
  const flags = flagsOf(t);
  return (
    <li className="trade-line">
      <span className="trade-line__time">{hhmm(t.opened_ist) || "—"}–{hhmm(t.closed_ist) || "…"}</span>
      <strong>{t.underlying} {strikeOf(t) ?? ""} {t.side}</strong>
      <span className="muted small">{strategyName(t.book_id)}</span>
      <span>{num(t.entry) ?? "—"} → {num(t.exit) ?? num(t.last_ltp) ?? "—"}</span>
      <Reason code={t.exit_reason} />
      {flags.map((f) => <Reason key={f} code={f} />)}
      <strong className={tone(t.realized_pnl_inr)}>{inr(t.realized_pnl_inr)}</strong>
    </li>
  );
}

export function DayLossGauge({ net, limit = RULES.dayLossInr, losers = 0 }) {
  const loss = Math.min(0, num(net) || 0);
  const used = Math.min(100, Math.round((loss / limit) * 100));
  const level = used >= 100 ? "red" : used >= 60 ? "amber" : "green";
  return (
    <div className="dlgauge" data-testid="day-loss-dlgauge">
      <div className="dlgauge__label">
        <span>Day loss used</span>
        <strong>{inr(loss)} of {inr(limit)}</strong>
      </div>
      <div className="dlgauge__bar"><i className={`dlgauge__fill dlgauge__fill--${level}`} style={{ width: `${used}%` }} /></div>
      <p className="muted small">Live strategies only (R01). {used}% used · losing trades {losers} of {RULES.maxLosersPerDay} · R01 / B3a slots stop at {inr(RULES.dayLossInrR01)}</p>
    </div>
  );
}

export function AlertList({ alerts }) {
  if (!alerts?.length) return <p className="muted">No alerts.</p>;
  return (
    <ul className="alert-list">
      {alerts.map((a) => (
        <li key={`${a.id}|${a.ts || ""}`} className={`alert-row alert-row--${String(a.severity || "").toLowerCase()}`}>
          <strong>{a.severity}</strong> <span>{a.title}</span>
          <span className="muted small">{fmtAge(a.age)}{a.age != null && a.age > 86400 ? " · old" : ""}</span>
          <p className="small">{a.detail}</p>
        </li>
      ))}
    </ul>
  );
}

export { exitRule };

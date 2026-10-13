import { useEffect, useState } from "react";
import { HISTORY_FAILED, backgroundView, fetchBackgroundTest, istDay } from "../lib/backgroundTest.js";
import { API_BASE } from "../lib/feed.js";
import { inr, num, tone } from "../lib/deskModel.js";
import { Levels } from "../pages/parts.jsx";

const dash = (v) => (v === null || v === undefined || v === "" ? "—" : v);
const px = (v) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(2) : "—");


const STATUS_TAG = { DESK: "tag--ok", BLOCKED_RISK_DAY_STOP: "tag--bad", BLOCKED_OPPOSITE: "tag--bad" };

// Today's desk-strategy signals (10 PX + R01) with what the desk did. Display only; never in any desk total.
export function DeskStrategiesToday({ sec }) {
  if (!sec || !Array.isArray(sec.rows) || sec.rows.length === 0) return null;
  const subs = Array.isArray(sec.per_strategy) ? sec.per_strategy : [];
  return (
    <div data-testid="bg-desk-strategies">
      <h4>Today’s strategy signals — {sec.rows.length} rows <span className="tag tag--muted">not in desk P&amp;L</span></h4>
      <p className="fine">Every signal from the 11 strategies, with what the desk did (DESK = booked; BLOCKED_* = refused by the risk / opposite-side guard; TEST_ONLY_PRE_1206 = before the rule was switched on). Paper only.{sec.as_of_ist ? ` Updated ${sec.as_of_ist.slice(11, 16)} IST.` : ""}</p>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr><th>Strategy</th><th className="r">Trades</th><th className="r">Closed</th><th className="r">Open</th><th>Status</th><th className="r">Net ₹ @1x</th><th className="r">Net ₹ @1.5x</th></tr></thead>
          <tbody>
            {subs.map((s) => (
              <tr key={s.strategy}>
                <td>{s.strategy}</td><td className="r num">{s.trades}</td><td className="r num">{s.closed}</td><td className="r num">{s.open}</td>
                <td className="fine">{Object.entries(s.by_status || {}).map(([k, n]) => `${k} ${n}`).join(" · ")}</td>
                <td className={`r num ${tone(s.net_inr_1x)}`}>{inr(s.net_inr_1x)}</td><td className={`r num ${tone(s.net_inr_1_5x)}`}>{inr(s.net_inr_1_5x)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <details className="details">
        <summary>All {sec.rows.length} rows</summary>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Strategy</th><th>Status</th><th>Und.</th><th>CE/PE</th><th className="r">Strike</th><th>Signal</th><th>Entry</th><th>Exit</th><th className="r">Entry ₹</th><th className="r">Exit ₹</th><th>Exit why</th><th className="r">Net @1x</th><th className="r">Net @1.5x</th></tr></thead>
            <tbody>
              {sec.rows.map((t, i) => (
                <tr key={i}>
                  <td>{dash(t.strategy)}</td>
                  <td><span className={`tag ${STATUS_TAG[t.desk_status] || "tag--muted"}`}>{dash(t.desk_status)}</span></td>
                  <td>{dash(t.underlying)}</td><td>{dash(t.side)}</td><td className="r num">{num(t.strike) ?? "—"}</td>
                  <td>{dash(t.signal_ist)}</td><td>{dash(t.entry_ist)}</td><td>{dash(t.exit_ist)}</td>
                  <td className="r num">{px(t.entry_px)}</td>
                  <td className="r num">{t.status === "OPEN" ? <span className="tag tag--muted">open · {px(t.mark_px)}</span> : px(t.exit_px)}</td>
                  <td>{dash(t.exit_reason_std)}</td>
                  <td className={`r num ${t.net_inr_1x == null ? "" : tone(t.net_inr_1x)}`}>{t.net_inr_1x == null ? "—" : inr(t.net_inr_1x)}</td>
                  <td className={`r num ${t.net_inr_1_5x == null ? "" : tone(t.net_inr_1_5x)}`}>{t.net_inr_1_5x == null ? "—" : inr(t.net_inr_1_5x)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

// Read-only paper research box. Its numbers are NOT desk P&L and are never passed up to any total.
export function BackgroundTestBox() {
  const [body, setBody] = useState(null);
  const [showFail, setShowFail] = useState(false);
  useEffect(() => {
    let ac;
    const load = () => {
      ac?.abort();
      ac = new AbortController();
      fetchBackgroundTest(API_BASE, istDay(), ac.signal).then(setBody).catch((e) => { if (e?.name !== "AbortError") setBody({ ok: false, status: "OFFLINE" }); });
    };
    load();
    const id = setInterval(load, 60000);
    return () => { clearInterval(id); ac?.abort(); };
  }, []);
  const v = backgroundView(body, showFail);
  return (
    <details className="panel details" data-testid="background-test">
      <summary>Background test (not traded) <span className="tag tag--muted">paper research — not in desk P&amp;L</span></summary>
      {!v.ok ? (
        <p className="muted">— No background test for today{body ? "" : " (loading)"}.</p>
      ) : (
        <>
          <p className="fine">These are test signals checked against real prices. Nothing here was traded and none of it is in the desk total.{v.asOf ? ` Updated ${v.asOf.slice(11, 16)} IST.` : ""}</p>
          <p className="fine warn" data-testid="bg-warning"><b>⚠ 1 day only · without top 3 = {v.withoutTop3 == null ? "—" : inr(v.withoutTop3)}</b>{v.top?.length ? ` (top 3: ${v.top.join(", ")})` : ""} · these strategies failed history tests: {HISTORY_FAILED.strategies.join(", ")} <em className="muted">(source: {HISTORY_FAILED.source})</em></p>
          {v.failed ? (
            <label className="fine"><input type="checkbox" checked={showFail} onChange={(e) => setShowFail(e.target.checked)} /> show {v.failed} that failed the check</label>
          ) : null}
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Strategy</th><th>CE/PE</th><th className="r">Strike</th><th>Signal</th><th className="r">Entry ₹</th><th className="r">Exit ₹</th><th>Stop / Target / exit</th><th className="r">Net ₹ @1.5x</th><th>Verified</th></tr></thead>
              <tbody>
                {v.rows.length === 0 ? <tr><td colSpan={9} className="muted">—</td></tr> : v.rows.map((t, i) => {
                  const dup = t.duplicate_of;
                  const net = typeof t.net_inr_1_5x === "number" ? t.net_inr_1_5x : null;
                  return (
                    <tr key={i} style={dup ? { opacity: 0.5 } : undefined} title={t.verify_reason || ""}>
                      <td>{dash(t.strategy)}{dup ? <em className="muted"> · same as {dup}</em> : null}</td>
                      <td>{dash(t.side)}</td>
                      <td className="r num">{num(t.strike) ?? "—"}</td>
                      <td>{dash(t.signal_ist)}</td>
                      <td className="r num">{px(t.entry_px)}</td>
                      <td className="r num">{t.status === "OPEN" ? <span className="tag tag--muted" title="P&L marked to last price">marked, not closed</span> : px(t.exit_px)}</td>
                      <td><Levels t={t} timeKey="planned_exit_ist" /></td>
                      <td className={`r num ${net === null ? "" : tone(net)}`}>{net === null || t.status === "OPEN" ? "—" : inr(net)}</td>
                      <td>{t.verified === "PASS" ? <span className="tag tag--ok">pass</span> : t.verified === "FAIL" ? <span className="tag tag--bad">fail</span> : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <DeskStrategiesToday sec={body?.desk_strategies_today} />
          <p className="fine">Unique closed: {v.closedUnique ?? "—"}, net {v.net === null ? "—" : inr(v.net)} after 1.5x charges — not traded.</p>
        </>
      )}
    </details>
  );
}

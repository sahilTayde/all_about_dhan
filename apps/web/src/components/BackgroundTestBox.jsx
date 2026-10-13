import { useEffect, useState } from "react";
import { HISTORY_FAILED, backgroundView, fetchBackgroundTest, istDay } from "../lib/backgroundTest.js";
import { API_BASE } from "../lib/feed.js";
import { inr, num, tone } from "../lib/deskModel.js";
import { Levels } from "../pages/parts.jsx";

const dash = (v) => (v === null || v === undefined || v === "" ? "—" : v);
const px = (v) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(2) : "—");

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
          <p className="fine">Unique closed: {v.closedUnique ?? "—"}, net {v.net === null ? "—" : inr(v.net)} after 1.5x charges — not traded.</p>
        </>
      )}
    </details>
  );
}

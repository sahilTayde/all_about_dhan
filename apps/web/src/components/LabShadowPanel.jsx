import { useEffect, useState } from "react";
import { istDay } from "../lib/backgroundTest.js";
import { API_BASE } from "../lib/feed.js";
import { clock, fetchLabShadow, labShadowView } from "../lib/labShadow.js";
import { inr, num, tone } from "../lib/deskModel.js";

const dash = (v) => (v === null || v === undefined || v === "" ? "—" : v);
const px = (v) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(2) : null);
const STATUS_WORDS = { PRIMARY: "Primary", WATCH: "Watch list", PARKED: "Parked", OTHER: "Status not given" };
const STATUS_TAG = { PRIMARY: "tag--ok", WATCH: "tag--warn", PARKED: "tag--muted", OTHER: "tag--muted" };

function Leg({ time, price }) {
  const t = clock(time) || (time ? String(time) : null);
  const p = px(price);
  if (!t && !p) return "—";
  return <>{t || "—"}{p ? <span className="muted"> @ {p}</span> : null}</>;
}

const Net = ({ v }) => (num(v) == null ? "—" : <span className={tone(v)}>{inr(v)}</span>);

// Read-only lab shadow panel. Its numbers are NOT desk paper, NOT desk P&L, NOT paper-extra; never passed to any total.
export function LabShadowPanel() {
  const [body, setBody] = useState(null);
  useEffect(() => {
    let ac;
    const load = () => {
      ac?.abort();
      ac = new AbortController();
      fetchLabShadow(API_BASE, istDay(), ac.signal).then(setBody).catch((e) => { if (e?.name !== "AbortError") setBody({ ok: false, status: "OFFLINE" }); });
    };
    load();
    const id = setInterval(load, 120000);
    return () => { clearInterval(id); ac?.abort(); };
  }, []);
  const v = labShadowView(body);
  return (
    <details className="panel details" data-testid="lab-shadow" open>
      <summary>Lab shadow trades <span className="tag tag--warn" data-testid="lab-shadow-badge">Lab shadow — not desk paper, ~20 min delayed</span></summary>
      {!v.ok ? (
        <p className="muted" data-testid="lab-shadow-empty">— {body ? (v.status === "NO_DATA" ? "No lab feed yet today." : `No lab feed (${v.status}).`) : "Loading lab feed…"}</p>
      ) : (
        <>
          <p className="fine">Trades the research lab's strategies would have taken, priced at the real ask in / bid out, net after 1.5× charges on 10 lots. Nothing here was traded by the desk and none of it is in the desk total or paper-extra.
            {v.updated ? ` File updated ${v.updated} IST.` : ""}{v.lastSeen ? ` Latest row seen ${v.lastSeen} IST.` : ""}</p>
          {v.feedStarts ? <p className="fine warn" data-testid="lab-shadow-feed-starts"><b>Feed starts {v.feedStarts} IST</b> — earlier trades are not in this list.</p> : null}
          {v.missingColumns.length ? <p className="fine warn">Lab file is missing: {v.missingColumns.join(", ")} (shown as —).</p> : null}
          {v.trades.length === 0 ? <p className="muted">— No lab trades in the file yet.</p> : null}
          {v.groups.map((g) => (
            <div key={g.status} data-testid={`lab-shadow-${g.status}`}>
              <h4><span className={`tag ${STATUS_TAG[g.status]}`}>{STATUS_WORDS[g.status]}</span></h4>
              <div className="tbl-wrap">
                <table className="tbl">
                  <thead><tr><th>Strategy</th><th>Family</th><th className="r">Trades</th><th className="r">Net ₹ @1.5x (lab)</th></tr></thead>
                  <tbody>
                    {g.strategies.map((s) => (
                      <tr key={s.strategy}>
                        <td>{s.strategy}{s.also.length ? <em className="muted"> · also: {s.also.join(", ")}</em> : null}</td>
                        <td>{dash(s.family)}</td>
                        <td className="r num">{s.trades}</td>
                        <td className="r num">{s.net15 === null ? "—" : <Net v={s.net15} />}{s.net15 !== null && s.withNet < s.trades ? <em className="muted"> ({s.trades - s.withNet} open)</em> : null}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          {v.trades.length ? (
            <details className="details">
              <summary>All {v.trades.length} lab trades{v.merged ? ` (${v.merged} listed under two names, shown once)` : ""}</summary>
              <div className="tbl-wrap">
                <table className="tbl" data-testid="lab-shadow-rows">
                  <thead><tr><th>Time</th><th>Strategy</th><th>Index</th><th>CE/PE</th><th className="r">Strike</th><th>Entry</th><th>Exit</th><th className="r">Net ₹ @1.5x</th></tr></thead>
                  <tbody>
                    {v.trades.map((t, i) => (
                      <tr key={i} title={t.reason || ""}>
                        <td>{dash(clock(t.seen_ist))}</td>
                        <td>{dash(t.strategy)}{t.also.length ? <em className="muted"> · also: {t.also.join(", ")}</em> : null}</td>
                        <td>{dash(t.und)}</td><td>{dash(t.side)}</td><td className="r num">{num(t.strike) ?? "—"}</td>
                        <td><Leg time={t.entry} price={t.ask_in} /></td>
                        <td>{t.exit || num(t.bid_out) != null ? <Leg time={t.exit} price={t.bid_out} /> : <span className="tag tag--muted">not closed yet</span>}</td>
                        <td className="r num"><Net v={t.net15} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          ) : null}
          <p className="fine muted">Time = when the lab row was seen (IST). Entry / exit = time @ option price. Hover a row for the lab's reason.{v.sources.length ? ` Source: ${v.sources.join(", ")}.` : ""}</p>
        </>
      )}
    </details>
  );
}

import { useEffect, useState } from "react";
import { istDay } from "../lib/backgroundTest.js";
import { API_BASE } from "../lib/feed.js";
import { inr, tone } from "../lib/deskModel.js";
import { CAPTION, fetchPxExits, pxExitsView, regimeText, statusCard } from "../lib/pxExits.js";

// PX exit labels + shadow exits. DISPLAY ONLY: labels change no exit, shadow money is never in desk / paper-extra totals.

/** Polls the read-only route every 5 s (the runner rewrites the sidecar every ~3 s). */
export function usePxExits(ms = 5000) {
  const [body, setBody] = useState(null);
  useEffect(() => {
    let ac;
    const load = () => {
      ac?.abort();
      ac = new AbortController();
      fetchPxExits(API_BASE, istDay(), ac.signal).then(setBody).catch((e) => { if (e?.name !== "AbortError") setBody({ ok: false, status: "OFFLINE" }); });
    };
    load();
    const id = setInterval(load, ms);
    return () => { clearInterval(id); ac?.abort(); };
  }, [ms]);
  return body;
}

export function LabelBadge({ card, small }) {
  if (!card) return null;
  if (card.na) return <span className="tag tag--muted" title={card.error} data-testid="px-label-na">status n/a</span>;
  if (!card.label) return <span className="tag tag--muted">—</span>;
  return (
    <span data-testid="px-label" style={{ background: card.color, color: card.label === "FADING" ? "#1a1a1a" : "#fff", fontWeight: 700, borderRadius: 4, padding: small ? "1px 6px" : "2px 8px", fontSize: small ? 11 : 12, letterSpacing: ".04em" }}>{card.label}</span>
  );
}

const money = (v) => (v == null ? "—" : inr(v));
const cell = (v) => <td className={`r num ${v == null ? "" : tone(v)}`}>{money(v)}</td>;
const yn = (b) => (b == null ? "—" : b ? "✓" : "✗");

function ExitCard({ o }) {
  const r = o.row, c = o.card;
  return (
    <div className="panel" style={{ padding: 10, margin: "8px 0", borderLeft: `4px solid ${c?.color || "var(--s3, #555)"}` }} data-testid="px-exit-card">
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <b>{r.rule_id}</b><span className="muted">{r.underlying} {r.strike ?? "—"} {r.side} · signal {r.signal_time ?? "—"} IST</span>
        {c ? <LabelBadge card={c} /> : <span className="tag tag--muted">no label yet</span>}
        {c && !c.na && c.reasons.length ? <span className="fine" style={{ margin: 0 }}>{c.reasons.join(" · ")}</span> : null}
      </div>
      {c && !c.na ? (
        <>
          <div className="num" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "2px 14px", marginTop: 6, fontSize: 13 }}>
            <span>{c.now}</span><span>{c.price}</span><span>{c.index}</span><span>{c.slope}</span>
            <span>{c.prem}</span><span style={c.vwapAgainst ? { color: "#c62828", fontWeight: 600 } : undefined}>{c.vwap}</span><span>{c.held}</span>
          </div>
          <p className="fine num" style={{ margin: "4px 0 0" }}>{c.levels}</p>
          <p className="fine num" style={{ margin: "2px 0 0" }} data-testid="px-live-stop"><b>{c.liveStop}</b> <em className="muted">· from live_exits.json (stop_floor / trail_gap)</em></p>
          <p className="fine" style={{ margin: "2px 0 0", opacity: c.stale ? 0.5 : 1 }} data-testid="px-updated">{c.updated}{c.stale ? " · older than 60 s" : ""}{c.src ? ` · ${c.src}` : ""}</p>
        </>
      ) : c?.na ? <p className="fine">status n/a <em className="muted">({c.error})</em></p> : <p className="fine">— (no exit_status for this trade yet)</p>}
      <p className="fine" style={{ margin: "4px 0 0" }}>
        <span className="tag tag--muted">shadow</span> Regime: {regimeText(o.regime)} · Narrow-open rule: {o.narrow ? `${o.narrow.would_skip ? "would skip" : "would trade"}${o.narrow.would_halve ? " / halve" : ""} (OR15 ${o.narrow.or15 ?? "—"})` : "—"}
      </p>
      <p className="fine" style={{ margin: "2px 0 0" }}><i>{CAPTION}</i></p>
    </div>
  );
}

function ShadowStrip({ strip }) {
  const f = strip.footer;
  const d = (x) => (x.value == null ? "—" : `${inr(x.value)}${x.n < x.of ? ` (${x.n} of ${x.of} trades)` : ""}`);
  return (
    <div data-testid="px-shadow-strip">
      <h4>Closed PX trades — other exits <span className="tag tag--warn">{strip.label}</span></h4>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr><th>Trade</th><th>Entry</th><th className="r">Actual</th><th className="r">base60_1m</th><th className="r">T50</th><th className="r">TS</th><th>TS target / why</th><th>DR would skip</th><th className="r">If DR applied</th><th>Giveback</th></tr></thead>
          <tbody>
            {strip.rows.length === 0 ? <tr><td colSpan={10} className="muted">— no closed PX trade logged yet</td></tr> : strip.rows.map((r, i) => (
              <tr key={i}>
                <td>{r.key}</td><td>{r.entry ?? "—"}</td>{cell(r.actual)}{cell(r.base60)}{cell(r.t50)}{cell(r.ts)}
                <td className="fine">{r.tsTarget == null ? "—" : `@${Math.round(r.tsTarget * 100)}%`}{r.tsReasons.length ? ` · ${r.tsReasons.join(", ")}` : ""}</td>
                <td>{yn(r.drSkip)}</td>{cell(r.dr)}<td>{yn(r.giveback)}</td>
              </tr>
            ))}
          </tbody>
          {strip.rows.length ? (
            <tfoot><tr><td colSpan={2}><b>Day (shadow)</b></td>{cell(f.actual)}{cell(f.base60)}{cell(f.t50)}{cell(f.ts)}<td colSpan={2} /><td className="r num">{money(f.dr)}</td><td /></tr></tfoot>
          ) : null}
        </table>
      </div>
      <p className="fine">T50 − base60: <b className="num">{d(f.t50MinusBase)}</b> · TS − base60: <b className="num">{d(f.tsMinusBase)}</b> · all money net ₹ after 1.5x charges · SHADOW, not traded — not in desk or paper-extra totals.</p>
    </div>
  );
}

function NarrowTable({ rows }) {
  return (
    <div data-testid="px-narrow">
      <h4>Narrow-open rule <span className="tag tag--warn">SHADOW, not traded</span></h4>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr><th>Trade</th><th>Entry</th><th>Exit</th><th>OR15</th><th>Cell</th><th>Would skip</th><th>Would halve</th><th className="r">Actual</th><th className="r">If skipped</th><th className="r">If halved</th></tr></thead>
          <tbody>
            {rows.length === 0 ? <tr><td colSpan={10} className="muted">— no closed trade logged yet</td></tr> : rows.map((r, i) => (
              <tr key={i}><td>{r.key}</td><td>{r.entry ?? "—"}</td><td>{r.exit ?? "—"}{r.why ? ` ${r.why}` : ""}</td><td>{r.or15 ?? "—"}</td><td>{r.cell ?? "—"}</td><td>{yn(r.skip)}</td><td>{yn(r.half)}</td>{cell(r.actual)}{cell(r.ifSkip)}{cell(r.ifHalf)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Whole box: open-trade labels, closed shadow strip, narrow-open shadow, per-file state. */
export function PxExitsPanel({ body }) {
  const v = pxExitsView(body);
  return (
    <section className="panel" data-testid="px-exits">
      <header className="panel__head"><h2>PX exits — labels &amp; shadow</h2><span className="tag tag--muted">display only · not in desk P&amp;L</span></header>
      {!v.ok ? (
        <p className="muted">— {v.status === "NO_ROUTE" ? "API has no /research/px-exits yet (needs API restart after merge)" : v.status === "LOADING" ? "loading" : `no data (${v.status})`}.</p>
      ) : (
        <>
          <p className="fine" data-testid="px-sources">Files for {v.day}: {v.sources.map((s) => `${s.name} ${s.state === "ok" ? "✓" : s.state}`).join(" · ")}{v.badLines.shadow_overlays ? ` · ${v.badLines.shadow_overlays} bad shadow line(s) skipped` : ""}</p>
          <h4>Open PX trades</h4>
          {v.open.length === 0 ? <p className="muted">— no open PX trade</p> : v.open.map((o) => <ExitCard key={o.row.key || o.row.rule_id} o={o} />)}
          <ShadowStrip strip={v.strip} />
          <NarrowTable rows={v.narrow} />
        </>
      )}
    </section>
  );
}


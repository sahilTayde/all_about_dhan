// PX exit labels (HEALTHY / FADING / REVERSING) + shadow exits, from GET /research/px-exits (DESK_PAGE_SPEC.md, 2026-10-19).
// DISPLAY ONLY. Labels change nothing about exits. Shadow numbers are "SHADOW, not traded" and must never be added to any
// desk / paper-extra total. deskModel.js imports only trailText (wording); no money value from here reaches periodNets / riskView / books.

export async function fetchPxExits(base, day, signal) {
  const r = await fetch(`${base || ""}/research/px-exits?day=${encodeURIComponent(day)}`, { signal, cache: "no-store" });
  if (!r.ok) return { ok: false, status: r.status === 404 ? "NO_ROUTE" : `HTTP_${r.status}` };
  return r.json();
}

export const LABEL_COLOR = { HEALTHY: "#2e7d32", FADING: "#f9a825", REVERSING: "#c62828" };
export const CAPTION = "Label is information only. Exits are unchanged (stop 30% / target 60% / trail).";
export const STALE_S = 60;

const fin = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const f2 = (v) => (fin(v) == null ? "—" : fin(v).toFixed(2));
const f1 = (v) => (fin(v) == null ? "—" : fin(v).toFixed(1));
const sgn = (v, d = 1) => (fin(v) == null ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : Object.is(v, -0) ? "−" : ""}${Math.abs(v).toFixed(d)}`);
const pct = (v) => (fin(v) == null ? "—" : `${sgn(v)}%`);
const hm = (s) => { const m = String(s || "").match(/(\d{2}:\d{2})(:\d{2})?/); return m ? m[1] : null; };
const hms = (s) => { const m = String(s || "").match(/T?(\d{2}:\d{2}:\d{2})/); return m ? m[1] : hm(s); };

export function pxKey(rule, und, sig) {
  if (!rule || !sig) return null;
  return `${rule}|${und || "NIFTY"}|${sig}`;
}

/** Key for a desk board trade (rule_id / book_id, underlying, sig_min). */
export function boardKey(t) {
  return pxKey(t?.rule_id || t?.book_id, t?.underlying, t?.sig_min || t?.signal_time || t?.signal_min);
}

/** Live trail / stop text from the live pricer state. Never fixed text: '—' when the data is not there. */
export function trailText(live) {
  if (!live || fin(live.live_stop) == null) return "—";
  const bits = [];
  if (live.binding === "gap trail") bits.push(`trail ${Math.round(live.trail_gap * 100)}% under HW ${f2(live.hw)}`);
  else if (live.binding === "stop floor") bits.push("stop floor");
  else if (live.binding === "BE trail") bits.push(`BE trail, HW ${f2(live.hw)} × 0.70`);
  else bits.push(live.trail_armed ? "trail on" : "trail off, BE at +30%");
  if (fin(live.stop_floor) != null && live.binding !== "stop floor") bits.push(`floor ${f2(live.stop_floor)}`);
  if (fin(live.trail_gap) != null && live.binding !== "gap trail") bits.push(`gap ${Math.round(live.trail_gap * 100)}%`);
  return `Live stop ${f2(live.live_stop)} (${bits.join(" · ")})`;
}

/** One open card. null = show nothing (no key / no status); {na:true} = "status n/a" (exit_status.error). */
export function statusCard(row, nowMs = Date.now()) {
  const es = row?.exit_status;
  if (!es || typeof es !== "object") return null;
  if (es.error) return { na: true, error: String(es.error) };
  const label = LABEL_COLOR[es.label] ? es.label : null;
  const upd = es.updated_ist ? Date.parse(es.updated_ist) : NaN;
  const ageS = Number.isFinite(upd) ? Math.max(0, (nowMs - upd) / 1000) : null;
  const vw = es.vwap_side === "WITH" || es.vwap_side === "AGAINST" ? es.vwap_side : null;
  const trailWord = es.trail_armed ? `Trail on${fin(es.trail_px) != null ? ` ${f2(es.trail_px)}` : ""}` : "Trail off";
  const live = row.live || null;
  return {
    na: false, label, color: label ? LABEL_COLOR[label] : null, reasons: Array.isArray(es.reasons) ? es.reasons : [],
    now: `Now ${pct(es.gain_now_pct)} · Peak ${pct(es.peak_gain_pct)} (${f2(es.peak_px)})`,
    price: `${f2(es.price_now)} @${hm(es.price_time) || "—"} IST (${es.price_src === "v2_depth" ? "v2_depth" : "1m close"})`,
    index: fin(es.index_vs_entry_bps) == null ? "Index —" : `Index ${sgn(es.index_vs_entry_bps)} bps ${es.index_vs_entry_bps >= 0 ? "with us" : "against us"}`,
    slope: `3m ${sgn(es.slope3_bps)} / 10m ${sgn(es.slope10_bps)} bps`,
    prem: `Prem 3m ${pct(es.premium_3min_pct)}`,
    vwap: vw ? `${vw} VWAP ${fin(es.vwap) == null ? "—" : Math.round(es.vwap)} (idx ${fin(es.index) == null ? "—" : Math.round(es.index)})` : "VWAP —",
    vwapAgainst: vw === "AGAINST",
    held: fin(es.minutes_held) == null ? "— min" : `${Math.round(es.minutes_held)} min`,
    levels: `Entry ${f2(es.entry_px)} · Stop ${f2(es.stop_px)} · Tgt ${f2(es.target_px)} · ${trailWord} (${es.trail_rule ? es.trail_rule.replace("high-water x 0.70", "HW×0.70") : "—"})`,
    liveStop: trailText(live),
    updated: `updated ${hms(es.updated_ist) || "—"} IST`, stale: ageS == null || ageS > STALE_S, src: row.exit_status_src || null,
  };
}

const leg = (x) => (x && typeof x === "object" ? fin(x.net_inr_1_5x) : null);

/** Closed-trade shadow strip. All money is net_inr_1_5x; a null leg is null ('—'), never 0. */
export function shadowStrip(lines) {
  const rows = (Array.isArray(lines) ? lines : []).filter((l) => l && typeof l === "object").map((l) => ({
    key: Array.isArray(l.key) ? l.key.join(" · ") : "—", entry: hm(l.entry_time),
    actual: leg(l.actual), base60: leg(l.base60_1m), t50: leg(l.t50), ts: leg(l.ts),
    tsTarget: fin(l.ts_target), tsReasons: Array.isArray(l.ts_reasons) ? l.ts_reasons : [],
    drSkip: l.dr && typeof l.dr.would_skip === "boolean" ? l.dr.would_skip : null, dr: leg(l.if_dr_applied),
    giveback: typeof l.giveback === "boolean" ? l.giveback : null,
  }));
  const sum = (k) => { const v = rows.map((r) => r[k]).filter((x) => x != null); return v.length ? v.reduce((a, b) => a + b, 0) : null; };
  const delta = (k) => { // only over trades where both legs exist, so a missing leg never looks like a gain or loss
    const both = rows.filter((r) => r[k] != null && r.base60 != null);
    return { value: both.length ? both.reduce((a, r) => a + (r[k] - r.base60), 0) : null, n: both.length, of: rows.length };
  };
  return { rows, footer: { actual: sum("actual"), base60: sum("base60"), t50: sum("t50"), ts: sum("ts"), dr: sum("dr"),
    t50MinusBase: delta("t50"), tsMinusBase: delta("ts") }, label: "SHADOW, not traded" };
}

/** Narrow-open rule shadow lines (regime bundle). */
export function narrowRows(lines) {
  return (Array.isArray(lines) ? lines : []).filter((l) => l && typeof l === "object").map((l) => ({
    key: Array.isArray(l.key) ? l.key.join(" · ") : "—", entry: hm(l.entry_time), exit: hm(l.exit_time), why: l.exit_reason || null,
    or15: l.shadow?.or15 ?? l.regime?.or15 ?? null, skip: typeof l.shadow?.would_skip === "boolean" ? l.shadow.would_skip : null,
    half: typeof l.shadow?.would_halve === "boolean" ? l.shadow.would_halve : null, cell: l.regime?.cell ?? null,
    actual: leg(l.actual), ifSkip: leg(l.if_rule_applied), ifHalf: leg(l.if_half_applied),
  }));
}

export const regimeText = (r) => (r && typeof r === "object"
  ? [r.cell || [r.trend_chop, r.side_vs_move, r.vix_bucket].map((x) => x || "—").join("|"), r.or15 ? `OR15 ${r.or15}` : null, r.gap_bucket, r.prior_day_type, r.expiry_day ? "expiry" : null].filter(Boolean).join(" · ")
  : "—");

const SRC_NAME = { rows: "day json", live_status: "live_exits_status.json", live_exits: "live_exits.json", shadow_overlays: "shadow_overlays jsonl", shadow_narrow_open: "shadow_narrow_open jsonl" };

/** Whole view. Every money number here is shadow; no field is shaped like a desk total. */
export function pxExitsView(body, nowMs = Date.now()) {
  if (!body || body.ok === false) return { ok: false, status: body?.status || "LOADING", open: [], closed: [], strip: shadowStrip([]), narrow: [], sources: [] };
  const rows = Array.isArray(body.rows) ? body.rows : [];
  const open = rows.filter((r) => r.status === "OPEN").map((r) => ({ row: r, card: statusCard(r, nowMs), regime: r.regime || null, narrow: r.shadow_narrow_open || null }));
  const sources = Object.entries(body.sources || {}).map(([k, v]) => ({ name: SRC_NAME[k] || k, state: v }));
  return { ok: true, status: "OK", day: body.day, open, strip: shadowStrip(body.shadow_overlays), narrow: narrowRows(body.shadow_narrow_open),
    sources, badLines: body.bad_lines || {}, byKey: Object.fromEntries(rows.filter((r) => r.key).map((r) => [r.key, r])) };
}

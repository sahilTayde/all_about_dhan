// "Lab shadow trades" panel: research-box shadow rows from GET /research/lab-shadow (events.csv, ~20 min delayed).
// Display only. Nothing here may feed any desk total (desk P&L, paper-extra, header, meter, history, strategies).

export async function fetchLabShadow(base, day, signal) {
  const r = await fetch(`${base || ""}/research/lab-shadow?day=${encodeURIComponent(day)}`, { signal, cache: "no-store" });
  if (!r.ok) return { ok: false, status: r.status === 404 ? "NO_ROUTE" : `HTTP_${r.status}` };
  return r.json();
}

export const STATUS_ORDER = ["PRIMARY", "WATCH", "PARKED"];
const RANK = { PRIMARY: 0, WATCH: 1, PARKED: 2 };
const fin = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
/**
 * What rand15 is compared against depends on the row type (research lab live_runner.py normalize()); there is no
 * cmp_kind column yet, so it is read from reason / strategy / src / family. Checked in this order:
 *   "vs random exit" : reason says "vs random exit" (QT:* rows; rand15 = RAND_EXIT)
 *   "vs base"        : reason has "(vs base" (F2_UNWIND, G5_UNWIND, ANTICHASE_AC1, FRESH:* "(vs base G00)"); rand15 = base net
 *   "vs base/random" : strategy starts "ROUTER:" (rand15 = base_or_random)
 *   "random"         : src gbv, or a lab cell row (src twoday/llm/rangebox/pinfade/r07fear/bigmove_cc/harvest/rb1utbot,
 *                      reason "<src> cell <id> fired HH:MM"); rand15 = rand_net15
 *   "vs base"        : any other exit-overlay row whose reason doesn't mention "random"
 *   null             : anything else, or rand15 empty -> no comparison, shown as —
 * ROUTER and gbv are checked before the exit-overlay fallback because both are family exit-overlay.
 */
export const CELL_SRCS = ["twoday", "llm", "rangebox", "pinfade", "r07fear", "bigmove_cc", "harvest", "rb1utbot"];
export const KIND_ORDER = ["random", "vs base", "vs random exit", "vs base/random"];
export const isLabCell = (r) => CELL_SRCS.includes(String(r?.src || "").trim().toLowerCase()) || /^\S+ cell \S+ fired\b/i.test(String(r?.reason || ""));
export function compareKind(r) {
  if (fin(r?.rand15) === null) return null;
  const reason = String(r.reason || "");
  if (/vs random exit/i.test(reason)) return "vs random exit";
  if (/\(vs base/i.test(reason)) return "vs base";
  if (/^ROUTER:/i.test(String(r.strategy || "").trim())) return "vs base/random";
  if (String(r.src || "").trim().toLowerCase() === "gbv" || isLabCell(r)) return "random";
  if (/exit[- _]?overlay/i.test(String(r.family || "")) && !/random/i.test(reason)) return "vs base";
  return null;
}
/** Per-row comparison: { kind, value: rand15, delta } — delta (net15 − rand15, what the overlay added) only for "vs base". */
export function comparison(r) {
  const kind = compareKind(r);
  if (!kind) return null;
  const value = fin(r.rand15); const net = fin(r.net15);
  return { kind, value, delta: kind === "vs base" && net !== null ? Math.round((net - value) * 100) / 100 : null };
}
const r2 = (x) => Math.round(x * 100) / 100;

/** Non-empty data_gap = the lab's prices had a hole for this trade. */
export const hasGap = (r) => r?.data_gap != null && String(r.data_gap).trim() !== "";

/** "HH:MM" from bare "10:45" / "9:05" (the real feed), "2026-10-19 09:51" or "2026-10-19T09:51:00+05:30"; null if none. */
export function clock(v) {
  const m = String(v ?? "").match(/(?:^|[ T])(\d{1,2}):(\d{2})/);
  return m ? `${m[1].padStart(2, "0")}:${m[2]}` : null;
}

/** Same trade = same index, side, strike and entry time (bare or full form). null when any part is missing (never merged then). */
export function tradeKey(r) {
  const parts = [r?.und, r?.side, r?.strike == null || r.strike === "" ? null : Number(r.strike), clock(r?.entry) || r?.entry];
  if (parts.some((p) => p === null || p === undefined || p === "")) return null;
  return parts.map((p) => String(p).trim().toUpperCase()).join("|");
}

/**
 * Unique trades + per-strategy groups. One trade listed under two names is shown once (under the higher status,
 * then the earlier row) with `also` naming the other(s), and counted once. Returns nothing for desk totals.
 */
export function labShadowView(body) {
  const ok = body && body.ok !== false && Array.isArray(body.rows);
  if (!ok) return { ok: false, status: body?.status || "NO_DATA", trades: [], groups: [], feedStarts: null };
  const raw = body.rows.filter((r) => r && typeof r === "object").map((r, i) => ({ ...r, _i: i }));
  const byKey = new Map();
  const trades = [];
  let relisted = 0; let aliased = 0;
  for (const r of raw) {
    const k = tradeKey(r);
    const prev = k ? byKey.get(k) : null;
    if (!prev) {
      const t = { ...r, also: [] };
      trades.push(t);
      if (k) byKey.set(k, t);
      continue;
    }
    if (prev.strategy === r.strategy) { // same name re-listed (e.g. "exit censored" then final): keep the newer row, count once
      relisted += 1;
      Object.assign(prev, { ...r, also: prev.also, _i: prev._i });
      continue;
    }
    aliased += 1;
    const better = (RANK[r.status] ?? 9) < (RANK[prev.status] ?? 9);
    if (better) {
      const also = [prev.strategy, ...prev.also].filter((n) => n && n !== r.strategy);
      Object.assign(prev, { ...r, also, _i: prev._i });
    } else if (r.strategy && !prev.also.includes(r.strategy)) prev.also.push(r.strategy);
  }
  trades.sort((a, b) => (clock(a.seen_ist) || "99:99").localeCompare(clock(b.seen_ist) || "99:99") || a._i - b._i);

  for (const t of trades) t.cmp = comparison(t);
  const groups = [];
  for (const st of [...STATUS_ORDER, "OTHER"]) {
    const mine = trades.filter((t) => (STATUS_ORDER.includes(t.status) ? t.status : "OTHER") === st);
    if (!mine.length) continue;
    const per = new Map();
    for (const t of mine) {
      const name = t.strategy || "—";
      const g = per.get(name) || { strategy: name, family: t.family || null, trades: 0, withNet: 0, net15: null, cmp: new Map(), dataGaps: 0, also: new Set() };
      g.trades += 1;
      const n = fin(t.net15);
      if (n !== null) { g.withNet += 1; g.net15 = Math.round(((g.net15 ?? 0) + n) * 100) / 100; }
      const c = t.cmp; // each comparison kind keeps its own sum; only rows the lab gave a value for; never filled in
      if (c) {
        const k = g.cmp.get(c.kind) || { kind: c.kind, sum: 0, k: 0, delta: null, kDelta: 0 };
        k.sum = r2(k.sum + c.value); k.k += 1;
        if (c.delta !== null) { k.delta = r2((k.delta ?? 0) + c.delta); k.kDelta += 1; }
        g.cmp.set(c.kind, k);
      }
      if (hasGap(t)) g.dataGaps += 1;
      t.also.forEach((a) => g.also.add(a));
      per.set(name, g);
    }
    groups.push({ status: st, strategies: [...per.values()].map((g) => ({ ...g, also: [...g.also], cmp: KIND_ORDER.filter((k) => g.cmp.has(k)).map((k) => g.cmp.get(k)) })) });
  }

  const firstSeen = raw.map((t) => clock(t.seen_ist)).filter(Boolean).sort()[0] || null; // first row in the file
  const feedStarts = firstSeen && firstSeen > "09:20" ? firstSeen : null;
  const srcs = [...new Set(raw.map((r) => r.src).filter(Boolean))];
  return {
    ok: true, status: "OK", trades, groups, feedStarts, firstSeen, sources: srcs,
    lastSeen: raw.map((t) => clock(t.seen_ist)).filter(Boolean).sort().pop() || null,
    updated: clock(body.file_updated_ist), missingColumns: Array.isArray(body.missing_columns) ? body.missing_columns : [],
    merged: raw.length - trades.length, aliased, relisted,
  };
}

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

/** "HH:MM" from "2026-10-19 09:51", "2026-10-19T09:51:00+05:30" or "09:51"; null if none. */
export function clock(v) {
  const m = String(v ?? "").match(/(?:^|[ T])(\d{1,2}):(\d{2})/);
  return m ? `${m[1].padStart(2, "0")}:${m[2]}` : null;
}

/** Same trade = same index, side, strike and entry time. null when any part is missing (never merged then). */
export function tradeKey(r) {
  const parts = [r?.und, r?.side, r?.strike, r?.entry];
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
  for (const r of raw) {
    const k = tradeKey(r);
    const prev = k ? byKey.get(k) : null;
    if (!prev) {
      const t = { ...r, also: [] };
      trades.push(t);
      if (k) byKey.set(k, t);
      continue;
    }
    if (prev.strategy === r.strategy) { // same name re-listed: keep the newer row's numbers, count once
      Object.assign(prev, { ...r, also: prev.also, _i: prev._i });
      continue;
    }
    const better = (RANK[r.status] ?? 9) < (RANK[prev.status] ?? 9);
    if (better) {
      const also = [prev.strategy, ...prev.also].filter((n) => n && n !== r.strategy);
      Object.assign(prev, { ...r, also, _i: prev._i });
    } else if (r.strategy && !prev.also.includes(r.strategy)) prev.also.push(r.strategy);
  }
  trades.sort((a, b) => (clock(a.seen_ist) || "99:99").localeCompare(clock(b.seen_ist) || "99:99") || a._i - b._i);

  const groups = [];
  for (const st of [...STATUS_ORDER, "OTHER"]) {
    const mine = trades.filter((t) => (STATUS_ORDER.includes(t.status) ? t.status : "OTHER") === st);
    if (!mine.length) continue;
    const per = new Map();
    for (const t of mine) {
      const name = t.strategy || "—";
      const g = per.get(name) || { strategy: name, family: t.family || null, trades: 0, withNet: 0, net15: null, also: new Set() };
      g.trades += 1;
      const n = fin(t.net15);
      if (n !== null) { g.withNet += 1; g.net15 = Math.round(((g.net15 ?? 0) + n) * 100) / 100; }
      t.also.forEach((a) => g.also.add(a));
      per.set(name, g);
    }
    groups.push({ status: st, strategies: [...per.values()].map((g) => ({ ...g, also: [...g.also] })) });
  }

  const firstSeen = raw.map((t) => clock(t.seen_ist)).filter(Boolean).sort()[0] || null; // first row in the file
  const feedStarts = firstSeen && firstSeen > "09:20" ? firstSeen : null;
  const srcs = [...new Set(raw.map((r) => r.src).filter(Boolean))];
  return {
    ok: true, status: "OK", trades, groups, feedStarts, firstSeen, sources: srcs,
    lastSeen: raw.map((t) => clock(t.seen_ist)).filter(Boolean).sort().pop() || null,
    updated: clock(body.file_updated_ist), missingColumns: Array.isArray(body.missing_columns) ? body.missing_columns : [],
    merged: raw.length - trades.length,
  };
}

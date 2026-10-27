// "Background test (not traded)" box: paper research rows from GET /research/background-test.
// Display only. Nothing here may feed any desk total (desk P&L, header, meter, history, strategies).

export function istDay(now = Date.now()) {
  return new Date(now + 330 * 60000).toISOString().slice(0, 10);
}

export async function fetchBackgroundTest(base, day, signal) {
  const r = await fetch(`${base || ""}/research/background-test?day=${encodeURIComponent(day)}`, { signal, cache: "no-store" });
  if (!r.ok) return { ok: false, status: r.status === 404 ? "NO_ROUTE" : `HTTP_${r.status}` };
  return r.json();
}

const fin = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);

/** Rows to show + footer numbers. FAIL rows hidden unless showFail. Never returns anything for desk totals. */
export function backgroundView(body, showFail = false) {
  const ok = body && body.ok !== false && Array.isArray(body.trades);
  if (!ok) return { ok: false, status: body?.status || "NO_DATA", rows: [], failed: 0, closedUnique: null, net: null };
  const all = body.trades.filter((t) => t && typeof t === "object");
  const failed = all.filter((t) => t.verified === "FAIL").length;
  const rows = all.filter((t) => showFail || t.verified !== "FAIL");
  const s = body.summary || {};
  return {
    ok: true, status: "OK", rows, failed: fin(s.failed) ?? failed,
    closedUnique: fin(s.closed_unique), net: fin(s.net_inr_1_5x), asOf: body.as_of_ist || null, day: body.day || null,
    ...withoutTop(all, fin(s.net_inr_1_5x)),
  };
}

/** Unique closed rows (the ones in the box total): CLOSED, counted, not a duplicate. */
export const uniqueClosed = (all) => all.filter((t) => t.status === "CLOSED" && t.count_in_total !== false && !t.duplicate_of && fin(t.net_inr_1_5x) != null);

/** Box net minus its 3 best unique closed trades. Uses the box's own rows only. */
export function withoutTop(all, net, n = 3) {
  const rows = uniqueClosed(all || []);
  const total = net ?? rows.reduce((a, t) => a + t.net_inr_1_5x, 0);
  const top = [...rows].sort((a, b) => b.net_inr_1_5x - a.net_inr_1_5x).slice(0, n);
  if (rows.length <= n) return { top: top.map((t) => t.strategy), withoutTop3: null };
  return { top: top.map((t) => t.strategy), withoutTop3: Math.round((total - top.reduce((a, t) => a + t.net_inr_1_5x, 0)) * 100) / 100 };
}

/** History verdicts as written in Opposition's review (2026-10-13_webdev_quantlead_review.md, "Real-price / history verdicts"). */
export const HISTORY_FAILED = { source: "Opposition review 13 Oct 2026", strategies: ["R01", "B2", "EP-010", "EP-018", "R07", "ORB_A", "VWAP_CONT", "ENG_5", "IB_15", "IB_5", "MINE_PE"] };

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
  };
}

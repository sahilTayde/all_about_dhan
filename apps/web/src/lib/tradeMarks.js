/**
 * Known premium marks for one paper trade.
 * Only timestamps that exist on the record. No interpolated path.
 */

function num(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function tsSec(raw) {
  const n = num(raw);
  if (n == null || n <= 0) return null;
  return n > 1e12 ? Math.floor(n / 1000) : Math.floor(n);
}

function push(points, t, v, label) {
  if (t == null || v == null) return;
  points.push({ time: t, value: Number(v), label });
}

/** Time-stamped premium points from the trade record or an explicit path array. */
export function premiumMarks(t) {
  if (!t) return { points: [], lines: [], marketKind: null, reason: null };
  const path = t.premium_path || t.path_marks || t.marks;
  const points = [];
  if (Array.isArray(path)) {
    for (const p of path) {
      const v = num(p?.v ?? p?.value ?? p?.premium);
      const time = tsSec(p?.t ?? p?.time ?? p?.ts) ?? (Number.isFinite(Number(p?.t)) && Number(p.t) < 1e6 ? null : tsSec(p?.t));
      if (v == null) continue;
      if (time != null) push(points, time, v, p.label || "");
    }
  }
  if (!points.length) {
    push(points, tsSec(t.opened_ts), num(t.entry ?? t.limit_price), "entry");
    push(points, tsSec(t.last_updated_ts), num(t.last_ltp), "ltp");
    push(points, tsSec(t.closed_ts), num(t.exit), "exit");
  }
  const seen = new Set();
  const uniq = [];
  for (const p of points.sort((a, b) => a.time - b.time)) {
    const k = `${p.time}|${p.value}|${p.label}`;
    if (seen.has(k)) continue;
    seen.add(k);
    uniq.push(p);
  }
  const lines = [
    { id: "entry", value: num(t.entry ?? t.limit_price), label: "Entry" },
    { id: "exit", value: num(t.exit), label: "Exit" },
    { id: "stop", value: num(t.stop), label: "Stop" },
    { id: "target", value: num(t.target), label: "Target" },
    { id: "high", value: num(t.seen_high), label: "Seen high" },
    { id: "low", value: num(t.seen_low), label: "Seen low" },
  ].filter((l) => l.value != null);
  return {
    points: uniq,
    lines,
    marketKind: t.market_kind_open || t.index_regime || null,
    reason: t.exit_reason || t.status || null,
  };
}

export function hasPremiumChart(marks) {
  return (marks?.points || []).length >= 2;
}

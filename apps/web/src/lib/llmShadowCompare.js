/** Founder-view helpers for the take/skip shadow compare panel. Shadow only. */

export function shadowCompareView(raw) {
  const src = raw && typeof raw === "object" ? raw : {};
  const r3 = num(src.r3_net);
  const random = num(src.random_mean);
  const delta = src.r3_minus_random != null ? num(src.r3_minus_random) : r3 != null && random != null ? r3 - random : null;
  return {
    ok: Boolean(src.ok) && (src.n_days || 0) > 0,
    status: src.status || (src.ok ? "ok" : "NO_DATA"),
    r3Net: r3,
    logitNet: num(src.logit_net),
    randomMean: random,
    delta,
    nDays: Number(src.n_days) || (Array.isArray(src.days) ? src.days.length : 0),
    days: Array.isArray(src.days) ? src.days : [],
    promote: false,
    trade: false,
  };
}

function num(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function moneyLine(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const sign = v > 0 ? "+" : "";
  return `${sign}${Math.round(v).toLocaleString("en-IN")}`;
}

const API_URL = import.meta.env.VITE_API_URL;
export const UNIQUE_BOOKS = ["MIX-DEFAULT-BUY", "MIX-ML-LOGIT", "MIX-ML-LOGIT-XR", "MIX-ML-GREEKS"];
const STALE_MS = 90_000;

const _cache = { board: null, boardAt: 0, lab: null };

async function getJson(url, signal) {
  const res = await fetch(url, { signal, cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchMlPaperBoard({ force = false, signal } = {}) {
  const now = Date.now();
  if (!force && _cache.board && now - _cache.boardAt < 5000) return _cache.board;
  const url = API_URL ? `${API_URL}/paper/ml-books` : "/mock/ml_paper_dashboard.json";
  const json = await getJson(`${url}${url.includes("?") ? "&" : "?"}t=${now}`, signal);
  _cache.board = json;
  _cache.boardAt = now;
  return json;
}

export async function fetchSodExam({ signal } = {}) {
  const now = Date.now();
  const url = API_URL ? `${API_URL}/paper/sod-exam` : "/paper/sod-exam";
  try {
    return await getJson(`${url}${url.includes("?") ? "&" : "?"}t=${now}`, signal);
  } catch {
    try {
      return await getJson(`/mock/sod_exam_report.json?t=${now}`, signal);
    } catch {
      return {
        ok: false,
        overall_honesty: "NOT_ENOUGH_DATA",
        headline: "Exam file missing. Run python -m desk_ml sod-exam after close.",
        days: [],
        stories: [],
        watch_next: [],
        promote: false,
        orders: "REFUSED",
      };
    }
  }
}

export async function fetchFounderLab({ signal } = {}) {
  if (_cache.lab) return _cache.lab;
  try {
    _cache.lab = await getJson(`/mock/founder_lab.json`, signal);
  } catch {
    _cache.lab = { ok: false, catalog: { models: [], strategies: [], indicators: [], rooms: [] }, fill_rooms: {}, extra_closed: [], day_series: [] };
  }
  return _cache.lab;
}

export function inr(n, { signed = true, digits = 0 } = {}) {
  if (n == null || n === "" || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const body = `₹${Math.abs(v).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })}`;
  if (!signed) return v < 0 ? `-${body}` : body;
  if (v > 0) return `+${body}`;
  if (v < 0) return `-${body}`;
  return body;
}

export function px(n) {
  if (n == null || n === "" || Number.isNaN(Number(n))) return "—";
  return Number(n).toFixed(2);
}

export function clock(ist) {
  if (!ist) return "—";
  const m = String(ist).match(/T(\d{2}:\d{2})/);
  return m ? m[1] : String(ist);
}

export function sessionDate(ist) {
  if (!ist) return "—";
  const m = String(ist).match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : String(ist);
}

export function moneyClass(n) {
  const v = Number(n);
  if (!Number.isFinite(v) || v === 0) return "";
  return v > 0 ? "is-up" : "is-down";
}

export function pct(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(1)}%`;
}

export function shortWhy(text) {
  if (!text) return "—";
  const now = String(text).match(/why_now=([^;|]+)/);
  if (now) return now[1].trim();
  const close = String(text).split("| CLOSE:")[0];
  const bit = close.replace(/^NIFTY buy /i, "").trim();
  return bit.length > 220 ? `${bit.slice(0, 217)}…` : bit;
}

function fillKey(t) {
  return [
    t.opened_ts || t.opened_ist || "",
    t.underlying,
    t.side,
    t.atm_strike,
    t.entry ?? t.limit_price,
    t.exit ?? "",
    t.exit_reason || t.status || "OPEN",
  ].join("|");
}

export function uniqueFills(rows) {
  const map = new Map();
  for (const t of rows || []) {
    const k = fillKey(t);
    if (!map.has(k)) {
      map.set(k, { ...t, books: [t.book_id].filter(Boolean) });
    } else {
      const row = map.get(k);
      if (t.book_id && !row.books.includes(t.book_id)) row.books.push(t.book_id);
    }
  }
  return [...map.values()];
}

export function pathInfo(t) {
  const last = Number(t.last_ltp ?? t.exit ?? t.entry ?? t.limit_price);
  const stop = Number(t.trail_stop ?? t.stop);
  const hardStop = Number(t.stop);
  const target = Number(t.target2 && t.target_step >= 1 ? t.target2 : t.target);
  const entry = Number(t.entry ?? t.limit_price);
  const span = target - stop;
  const pctAlong =
    Number.isFinite(span) && span !== 0 && Number.isFinite(last) ? (last - stop) / span : null;
  const toTarget = Number.isFinite(last) && Number.isFinite(target) ? target - last : null;
  const slRoom = Number.isFinite(last) && Number.isFinite(stop) ? last - stop : null;
  const vsEntry = Number.isFinite(last) && Number.isFinite(entry) ? last - entry : null;
  const distTgt = Number.isFinite(toTarget) ? Math.abs(toTarget) : null;
  const distSl = Number.isFinite(slRoom) ? Math.abs(slRoom) : null;
  const pathSum = distTgt != null && distSl != null ? distTgt + distSl : null;
  const hitTargetPct = pathSum && pathSum > 0 ? Math.round((distSl / pathSum) * 100) : null;
  const hitStopPct = hitTargetPct == null ? null : 100 - hitTargetPct;
  return {
    last,
    stop,
    hardStop,
    target,
    entry,
    pct: pctAlong,
    toTarget,
    slRoom,
    vsEntry,
    hitTargetPct,
    hitStopPct,
    trailing: t.trail_stop != null && Number(t.trail_stop) !== Number(t.stop),
  };
}

export function deskLifeStatus(t, { nowMs = Date.now() } = {}) {
  const status = String(t?.status || "");
  const reason = String(t?.exit_reason || "");
  if (!t) return "DEAD";
  if (status.includes("OPEN") || status === "IN_PROGRESS" || status === "ACTIVE") {
    const updated = Number(t.last_updated_ts);
    const ageMs = Number.isFinite(updated) && updated > 1e12 ? nowMs - updated : null;
    const ageSec = Number.isFinite(updated) && updated < 1e12 ? nowMs / 1000 - updated : null;
    const stale = (ageMs != null && ageMs > STALE_MS) || (ageSec != null && ageSec > 90);
    if (stale) return "STALE";
    const last = Number(t.last_ltp);
    if (Number.isFinite(last)) return "PROGRESS";
    return "ACTIVE";
  }
  if (reason.startsWith("CANCEL") || status.includes("CANCEL") || status.includes("DEAD")) {
    return "DEAD";
  }
  if (status.includes("CLOSED") || t.exit != null) return "DONE";
  return "DEAD";
}

export function outcomeLabel(t) {
  const reason = String(t?.exit_reason || "");
  const step = Number(t?.target_step || 0);
  const targetHit = t?.target_hit === true || reason === "TARGET" || reason === "TARGET2";
  if (reason === "TARGET2" || (targetHit && step >= 2)) return "TARGET 2 HIT";
  if (targetHit || reason === "TARGET") return "TARGET HIT";
  if (reason.includes("TRAIL") || (reason === "STOP" && t?.trail_hit)) return "STOP LOSS TRAIL HIT";
  if (reason === "STOP" || t?.sl_hit) return "STOP LOSS HIT";
  if (reason.startsWith("CANCEL") || String(t?.status || "").includes("CANCEL")) return "CANCELLED";
  if (reason === "TIME" || reason.startsWith("FLATTEN")) return reason === "TIME" ? "TIME" : "FLATTEN";
  if (t?.result === "SUCCESS") return "ACHIEVED";
  if (t?.result === "LOSS") return "STOP LOSS HIT";
  return reason || t?.status || "—";
}

export function outcomeSlug(label) {
  const s = String(label || "").toLowerCase();
  if (s.includes("target 2")) return "target2";
  if (s.includes("target")) return "target";
  if (s.includes("trail")) return "trail";
  if (s.includes("stop")) return "stop";
  if (s.includes("cancel")) return "cancel";
  if (s === "time" || s === "flatten") return "time";
  if (s.includes("achiev") || s.includes("done")) return "done";
  return "plain";
}

export function skipPlain(reason) {
  const r = String(reason || "");
  if (r === "FOCUS_NIFTY_ONLY") return "SENSEX parked — this ship is NIFTY only";
  if (r === "FOCUS_NIFTY_SENSEX") return "BANKNIFTY parked";
  if (r === "NIFTY_WAIT_STRENGTH") return "Waiting for last-3 / pause-continue / short-cover";
  if (r === "GREEKS_NO_CLONE") return "Greeks book does not copy the same fill";
  if (r === "NO_NEW_AFTER_1515") return "No new paper after 15:15 IST";
  if (r.startsWith("XR")) return "XR filter skipped this side";
  if (r.includes("OBSERVE")) return "Observe book — ₹0, no fill";
  if (r.includes("ML-001") || r.includes("HOLD")) return "ML-001 holding";
  if (r.includes("VETO")) return "Observer / boss veto";
  if (r.includes("DEALER")) return "Dealer discarded";
  return r.replaceAll("_", " ");
}

export function discardedWho(row) {
  const reason = String(row.reason || row.action || "");
  const dealer = String(row.dealer_verdict || "").toUpperCase();
  const ignored = row.ignored_by_boss === true;
  const observer = String(row.observer_action || "").toUpperCase();
  if (ignored || observer === "VETO") return "Boss / observer";
  if (dealer === "HOLD" || dealer === "KILL" || dealer === "VETO") return "Dealer";
  if (reason.startsWith("CANCEL") || row.action === "CANCEL") return "Dealer";
  if (String(row.book_id || "").includes("DEFAULT")) return "Dealer";
  return "Boss / model";
}

export function groupSkips(rows) {
  const map = new Map();
  for (const t of rows || []) {
    const k = `${t.reason || t.vs_picker || "SKIP"}|${t.underlying || "?"}|${t.seen_side || t.side || "—"}`;
    if (!map.has(k)) {
      map.set(k, {
        reason: t.reason || t.vs_picker,
        underlying: t.underlying,
        side: t.seen_side || t.side,
        why: t.why || t.detail || t.observation,
        who: discardedWho(t),
        books: [],
        n: 0,
      });
    }
    const g = map.get(k);
    g.n += 1;
    if (t.book_id && !g.books.includes(t.book_id)) g.books.push(t.book_id);
    if (t.source && !g.books.includes(t.source)) g.books.push(t.source);
  }
  return [...map.values()].sort((a, b) => b.n - a.n);
}

function dailyBuckets(rows) {
  const days = new Map();
  for (const t of rows || []) {
    const day = sessionDate(t.closed_ist || t.opened_ist || t.last_updated_ist);
    if (!days.has(day)) {
      days.set(day, { day, n: 0, wins: 0, profit: 0, loss: 0, net: 0, charges: 0, byBook: new Map() });
    }
    const d = days.get(day);
    const pnl = Number(t.realized_pnl_inr) || 0;
    const charges = Number(t.charges_inr) || 0;
    d.n += 1;
    d.net += pnl;
    d.charges += charges;
    if (pnl > 0) {
      d.wins += 1;
      d.profit += pnl;
    } else if (pnl < 0) {
      d.loss += pnl;
    }
    const book = t.book_id || "UNKNOWN";
    if (!d.byBook.has(book)) d.byBook.set(book, { book, n: 0, wins: 0, net: 0 });
    const b = d.byBook.get(book);
    b.n += 1;
    b.net += pnl;
    if (pnl > 0) b.wins += 1;
  }
  return [...days.values()]
    .map((d) => ({
      ...d,
      wr: d.n ? Math.round((d.wins / d.n) * 1000) / 10 : null,
      books: [...d.byBook.values()].map((b) => ({
        ...b,
        wr: b.n ? Math.round((b.wins / b.n) * 1000) / 10 : null,
      })),
    }))
    .sort((a, b) => String(b.day).localeCompare(String(a.day)));
}

export function derivePaperBoard(data, lab = null) {
  if (!data) return null;
  const today = data.today || {};
  const byUpdated = (a, b) => {
    const ta = Number(a?.last_updated_ts || a?.closed_ts || a?.opened_ts || 0);
    const tb = Number(b?.last_updated_ts || b?.closed_ts || b?.opened_ts || 0);
    return tb - ta;
  };
  const liveMoney = Boolean(data.live_session) || Boolean(data.session_ist_date);
  const closed = [...(data.closed_trades || [])].sort(byUpdated);
  const open = [...(data.open_trades || [])].sort(byUpdated);
  const uniqueClosed = uniqueFills(closed);
  const uniqueOpen = uniqueFills(open);
  const uniqueNet = uniqueClosed.reduce((s, t) => s + (Number(t.realized_pnl_inr) || 0), 0);
  const uniqueCharges = uniqueClosed.reduce((s, t) => s + (Number(t.charges_inr) || 0), 0);
  const uniqueGross = uniqueClosed.reduce((s, t) => s + (Number(t.gross_pnl_inr) || 0), 0);
  const uniqueWins = uniqueClosed.filter((t) => Number(t.realized_pnl_inr) > 0).length;
  const uniqueWr = uniqueClosed.length ? Math.round((uniqueWins / uniqueClosed.length) * 1000) / 10 : null;
  const nTarget = uniqueClosed.filter((t) => outcomeLabel(t) === "TARGET HIT" || outcomeLabel(t) === "TARGET 2 HIT").length;
  const nStop = uniqueClosed.filter((t) => String(outcomeLabel(t)).includes("STOP LOSS")).length;
  const startCap = Number(data.starting_desk_inr || today.starting_desk_inr || 0);
  const headlineNet = Number(today.net_pnl_inr ?? data.overall_pnl_inr);
  const equity = Number.isFinite(startCap) ? startCap + (Number.isFinite(headlineNet) ? headlineNet : uniqueNet) : null;
  const charges = Number(today.charges_inr ?? data.overall_charges_inr ?? uniqueCharges);
  const cloneDrag = Number.isFinite(headlineNet) ? headlineNet - uniqueNet : null;
  const seen = data.seen_not_taken || today.seen_not_taken || {};
  const modelSignals = data.model_signals || today.model_signals || {};
  const discardedRows = [
    ...(seen.skipped_latest || []),
    ...(seen.cancelled || []),
    ...(modelSignals.latest || []).filter((r) => r.ignored_by_boss || r.observer_action === "VETO" || r.vs_picker === "DISSENT"),
  ];
  const days = liveMoney ? dailyBuckets(uniqueClosed) : mergeDaySeries(dailyBuckets(uniqueClosed), lab?.day_series);
  const bookDays = dailyBuckets(closed);
  const sessionDay = data.session_ist_date || sessionDate(data.as_of_ist);
  const todayBookDay = bookDays.find((d) => d.day === sessionDay) || (liveMoney ? null : bookDays[0]);
  const todayDay = days.find((d) => d.day === sessionDay) || {
    day: sessionDay || "—",
    n: 0,
    wr: null,
    profit: 0,
    loss: 0,
    net: 0,
    charges: 0,
    books: [],
  };
  const uniqueRank = (data.book_rank || []).filter((r) =>
    (today.unique_books || UNIQUE_BOOKS).includes(r.book_id)
  );
  const books = (data.book_rank || uniqueRank).map((r) => {
    const dayBook = (todayBookDay?.books || []).find((b) => b.book === r.book_id);
    return {
      ...r,
      day_wr: dayBook?.wr ?? (r.n_filled ? r.win_rate_net_pct : null),
      day_n: dayBook?.n ?? r.n_filled,
    };
  });
  const regimes = data.last_index_regime || {};
  const signals = modelSignals.latest || [];
  const nMatch = signals.filter((r) => r.vs_picker === "MATCH").length;
  const nDissent = signals.filter((r) => r.vs_picker === "DISSENT").length;
  const fillRooms = lab?.fill_rooms || {};
  const currentId = uniqueOpen[0]?.trade_id;
  return {
    today,
    closed,
    open,
    uniqueClosed,
    uniqueOpen,
    uniqueNet,
    uniqueCharges,
    uniqueGross,
    uniqueWr,
    nTarget,
    nStop,
    startCap,
    headlineNet,
    equity,
    charges,
    cloneDrag,
    seen,
    modelSignals,
    discardedRows,
    skipGroups: groupSkips(discardedRows),
    days,
    todayDay,
    books,
    regimes,
    moneyWr: data.win_rate_net_pct ?? today.win_rate_net_pct,
    targetWr: uniqueClosed.length ? Math.round((nTarget / uniqueClosed.length) * 1000) / 10 : null,
    current: uniqueOpen[0] || null,
    catalog: lab?.catalog || { models: [], strategies: [], indicators: [], rooms: [] },
    confirmKill: lab?.confirm_kill || {},
    fillRooms,
    currentRoom: (currentId && fillRooms[currentId]) || null,
    liveMoney,
    training: lab?.training || null,
    nMatch,
    nDissent,
    nSilent: signals.filter((r) => r.vs_picker === "SILENT" || r.side === "SILENT").length,
    byRegime: groupNet(uniqueClosed, "index_regime"),
    byIndex: groupNet(uniqueClosed, "underlying"),
  };
}

function mergeDaySeries(computed, extra) {
  const map = new Map();
  for (const row of extra || []) {
    map.set(row.day, { ...row, books: row.books || [] });
  }
  for (const d of computed) {
    const prev = map.get(d.day);
    if (!prev || (d.n || 0) >= (prev.n || 0)) map.set(d.day, d);
  }
  return [...map.values()].sort((a, b) => String(b.day).localeCompare(String(a.day)));
}

function groupNet(rows, key) {
  const map = new Map();
  for (const t of rows || []) {
    const k = t[key] || "UNKNOWN";
    if (!map.has(k)) map.set(k, { key: k, n: 0, wins: 0, net: 0 });
    const g = map.get(k);
    const pnl = Number(t.realized_pnl_inr) || 0;
    g.n += 1;
    g.net += pnl;
    if (pnl > 0) g.wins += 1;
  }
  return [...map.values()].map((g) => ({
    ...g,
    wr: g.n ? Math.round((g.wins / g.n) * 1000) / 10 : null,
  }));
}

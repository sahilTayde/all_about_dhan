/**
 * Strategy leaderboard view-model.
 * Paper / shadow only. The five cards are the C5 paper slots from
 * config/v2/strategies/registry.yaml. Missing fills stay empty — never invented.
 */

function sessionDate(ist) {
  if (!ist) return "—";
  const m = String(ist).match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : String(ist);
}

/** C5 paper slots (registry stage: paper). Readable name first; id is the subtitle. */
export const PAPER_SLOTS = Object.freeze([
  { id: "R01_PDIV_5_ALL_H20", name: "Premium divergence" },
  { id: "R01_B3A_VOL", name: "Premium divergence · high vol" },
  { id: "B8B_B3A_EX_CHOPPY", name: "High-vol skip-chop" },
  { id: "R07_MOM3_TREND", name: "Momentum" },
  { id: "B8A_R07_NO_PRE1030", name: "Momentum after 10:30" },
]);

export const PAPER_SLOT_IDS = Object.freeze(PAPER_SLOTS.map((s) => s.id));

const SLOT_NAME = Object.fromEntries(PAPER_SLOTS.map((s) => [s.id, s.name]));

/** Roster / pooled-tape aliases → C5 slot id. */
export const SLOT_ALIASES = Object.freeze({
  "R07_MOM_3_0.0005_TREND_H20": "R07_MOM3_TREND",
  "R07_MOM_3_0.0005_TREND": "R07_MOM3_TREND",
});

export function canonicalSlotId(raw) {
  const s = String(raw || "").trim();
  return SLOT_ALIASES[s] || s;
}

export const SORT_KEYS = Object.freeze(["net", "trades", "win", "dd", "name"]);

function num(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function tradeTs(t) {
  const raw = Number(t?.closed_ts ?? t?.opened_ts ?? t?.last_updated_ts ?? 0);
  return Number.isFinite(raw) ? raw : 0;
}

export function isShadowTrade(t) {
  return t?.shadow === true || String(t?.execution || "").toLowerCase() === "shadow";
}

export function tradeSlotIds(t) {
  const ids = [];
  const push = (v) => {
    const s = String(v || "").trim();
    if (s && !ids.includes(s)) ids.push(s);
  };
  push(t?.strategy_id);
  push(t?.book_id);
  push(t?.journal_tag);
  push(t?.slot);
  for (const b of t?.books || []) push(b);
  for (const m of t?.model_names || []) push(m);
  return ids;
}

export function equityCurve(trades) {
  let run = 0;
  const points = [];
  for (const t of [...(trades || [])].sort((a, b) => tradeTs(a) - tradeTs(b))) {
    const pnl = num(t.realized_pnl_inr);
    if (pnl == null) continue;
    run += pnl;
    points.push({ t: tradeTs(t), v: run });
  }
  return points;
}

/** Peak-to-trough on the book's cumulative net. Null when the curve has no trades. */
export function maxDrawdown(curve) {
  if (!curve?.length) return null;
  let peak = curve[0].v;
  let dd = 0;
  for (const p of curve) {
    if (p.v > peak) peak = p.v;
    const drop = peak - p.v;
    if (drop > dd) dd = drop;
  }
  return dd;
}

export function avgWinLoss(trades) {
  const wins = [];
  const losses = [];
  for (const t of trades || []) {
    const pnl = num(t.realized_pnl_inr);
    if (pnl == null) continue;
    if (pnl > 0) wins.push(pnl);
    else if (pnl < 0) losses.push(pnl);
  }
  const mean = (xs) => (xs.length ? xs.reduce((s, n) => s + n, 0) / xs.length : null);
  return { avgWin: mean(wins), avgLoss: mean(losses), nWin: wins.length, nLoss: losses.length };
}

/**
 * TRADE only when the book is thick, profitable after costs, and beats random.
 * Never TRADE on a losing or thin book. N is shown next to the badge.
 */
export function slotBadge({ nFilled, net, vsRandom }) {
  const n = nFilled || 0;
  const money = num(net);
  if (n >= 30 && money != null && money < 0) return "DROP";
  if (n >= 30 && money != null && money > 0 && vsRandom != null && vsRandom > 0) return "TRADE";
  return "WATCH";
}

/** Recorded random baseline only. Never a 50% coin-flip stand-in. */
export function randomBaseline(rank, scoreboard, bookId) {
  return (
    num(rank?.random_win_pct ?? rank?.win_vs_random_pct ?? rank?.random_wr_pct) ??
    num(scoreboard?.[bookId]?.random_win_pct ?? scoreboard?.[bookId]?.win_pct)
  );
}

export function winVsRandom(rank, scoreboard, bookId, wr) {
  const win = wr ?? num(rank?.win_rate_net_pct ?? rank?.win_rate_pct);
  const rnd = randomBaseline(rank, scoreboard, bookId);
  if (win == null || rnd == null) return null;
  return win - rnd;
}

function bookTrades(rows, bookId, shadow) {
  return (rows || []).filter((t) => {
    if (!tradeSlotIds(t).includes(bookId)) return false;
    return shadow ? isShadowTrade(t) : !isShadowTrade(t);
  });
}

export const SHADOW_RULES = Object.freeze(["DEAD3_7", "R19 quiet", "expiry pin", "skip-coil", "IN_PHASE_ONLY"]);

function lastDots(trades) {
  return [...(trades || [])]
    .sort((a, b) => tradeTs(a) - tradeTs(b))
    .slice(-5)
    .map((t) => {
      const pnl = num(t.realized_pnl_inr);
      return pnl == null ? "flat" : pnl > 0 ? "up" : "down";
    });
}

function cardFrom({ bookId, name, rank, closed, open, shadow, sessionDay, scoreboard }) {
  const fills = bookTrades(closed, bookId, shadow);
  const opens = bookTrades(open, bookId, shadow);
  const curve = equityCurve(fills);
  const avg = avgWinLoss(fills);
  const nFilled = num(rank?.n_filled) ?? fills.length;
  const wins = num(rank?.n_wins) ?? avg.nWin;
  const net = num(rank?.sum_pnl_inr) ?? fills.reduce((s, t) => s + (num(t.realized_pnl_inr) || 0), 0);
  const wr = nFilled ? Math.round(((wins || 0) / nFilled) * 1000) / 10 : num(rank?.win_rate_net_pct);
  const todayFills = sessionDay ? fills.filter((t) => sessionDate(t.closed_ist || t.opened_ist) === sessionDay) : fills;
  const vsRandom = shadow ? null : winVsRandom(rank, scoreboard, bookId, wr);
  const randomWin = randomBaseline(rank, scoreboard, bookId);
  const payoff = avg.avgWin != null && avg.avgLoss ? Math.abs(avg.avgWin / avg.avgLoss) : null;
  return {
    id: shadow ? `${bookId}·SHADOW` : bookId,
    bookId,
    name: name || SLOT_NAME[bookId] || bookId,
    label: name || SLOT_NAME[bookId] || bookId,
    kind: shadow ? "SHADOW" : rank?.kind || "PAPER",
    shadow: Boolean(shadow),
    rules: shadow ? SHADOW_RULES : [],
    nFilled,
    nOpen: opens.length,
    nToday: todayFills.length,
    winPct: nFilled ? wr : null,
    randomWin,
    vsRandom,
    avgWin: avg.avgWin,
    avgLoss: avg.avgLoss,
    payoff,
    net: nFilled || opens.length ? net : null,
    maxDd: maxDrawdown(curve),
    curve,
    dots: lastDots(fills),
    badge: slotBadge({ nFilled, net, vsRandom }),
    rank,
  };
}

export function buildStrategyCards(board, { uniqueClosed = [], uniqueOpen = [] } = {}) {
  const rankBy = new Map((board?.book_rank || []).map((r) => [r.book_id, r]));
  const scoreboard = board?.shadow_scoreboard || board?.random_scoreboard || {};
  const sessionDay = board?.session_ist_date || sessionDate(board?.as_of_ist);
  const cards = [];
  for (const slot of PAPER_SLOTS) {
    cards.push(
      cardFrom({
        bookId: slot.id,
        name: slot.name,
        rank: rankBy.get(slot.id) || null,
        closed: uniqueClosed,
        open: uniqueOpen,
        shadow: false,
        sessionDay,
        scoreboard,
      }),
    );
    cards.push(
      cardFrom({
        bookId: slot.id,
        name: `${slot.name} · shadow`,
        rank: null,
        closed: uniqueClosed,
        open: uniqueOpen,
        shadow: true,
        sessionDay,
        scoreboard,
      }),
    );
  }
  return cards;
}

export function sortStrategyCards(cards, key = "net", dir = "desc") {
  const sign = dir === "asc" ? 1 : -1;
  const val = (c) => {
    if (key === "trades") return c.nFilled ?? -1;
    if (key === "win") return c.winPct ?? -1;
    if (key === "dd") return c.maxDd ?? -1;
    if (key === "name") return c.name || c.bookId;
    return c.net ?? 0;
  };
  return [...(cards || [])].sort((a, b) => {
    const av = val(a);
    const bv = val(b);
    if (typeof av === "string" || typeof bv === "string") return sign * String(av).localeCompare(String(bv));
    if (av === bv) return String(a.name || a.bookId).localeCompare(String(b.name || b.bookId));
    return sign * ((av ?? 0) - (bv ?? 0));
  });
}

export function todayTimeline(open, closed, sessionDay) {
  const dayOf = (t) => sessionDate(t.closed_ist || t.opened_ist || t.last_updated_ist);
  const rows = [...(open || []), ...(closed || [])].filter((t) => !sessionDay || dayOf(t) === sessionDay || !t.closed_ist);
  return rows.sort((a, b) => tradeTs(b) - tradeTs(a));
}

export function matchesSlot(trade, bookId, shadow) {
  if (!tradeSlotIds(trade).includes(bookId)) return false;
  return Boolean(trade.shadow) === Boolean(shadow) || (shadow && isShadowTrade(trade));
}

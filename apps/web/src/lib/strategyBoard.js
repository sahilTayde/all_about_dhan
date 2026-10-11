/**
 * Strategy leaderboard view-model.
 * Paper / shadow only. Numbers come from the board + closed fills.
 * Missing fields stay null and render as empty — never invented.
 */

const UNIQUE_BOOKS = ["MIX-DEFAULT-BUY", "MIX-ML-LOGIT", "MIX-ML-LOGIT-XR", "MIX-ML-GREEKS"];

function sessionDate(ist) {
  if (!ist) return "—";
  const m = String(ist).match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : String(ist);
}

/** Five paper books the desk ranks. Extra book_rank rows still appear. */
export const PAPER_SLOT_IDS = Object.freeze([
  "MIX-DEFAULT-BUY",
  "MIX-ML-LOGIT",
  "MIX-ML-LOGIT-XR",
  "MIX-ML-GREEKS",
  "MIX-TV-EP-024",
]);

const SLOT_LABEL = {
  "MIX-DEFAULT-BUY": "Desk default",
  "MIX-ML-LOGIT": "Logit",
  "MIX-ML-LOGIT-XR": "Logit × XR",
  "MIX-ML-GREEKS": "Greeks",
  "MIX-TV-EP-024": "TV-EP lab",
};

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
 * TRADE = open paper fill on this book.
 * WATCH = closed fills or a shadow book (observe, do not promote).
 * DROP = no fills on the record.
 */
export function slotBadge({ nFilled, openCount, shadow }) {
  if (openCount > 0) return "TRADE";
  if (shadow) return "WATCH";
  if ((nFilled || 0) > 0) return "WATCH";
  return "DROP";
}

/** Recorded random baseline only. Never a 50% coin-flip stand-in. */
export function winVsRandom(rank) {
  const wr = num(rank?.win_rate_net_pct ?? rank?.win_rate_pct);
  const rnd = num(rank?.random_win_pct ?? rank?.win_vs_random_pct ?? rank?.random_wr_pct);
  if (wr == null || rnd == null) return null;
  return wr - rnd;
}

function bookTrades(rows, bookId, shadow) {
  return (rows || []).filter((t) => {
    const books = t.books?.length ? t.books : [t.book_id];
    if (!books.includes(bookId)) return false;
    return shadow ? isShadowTrade(t) : !isShadowTrade(t);
  });
}

function cardFrom({ bookId, rank, closed, open, shadow, sessionDay }) {
  const fills = bookTrades(closed, bookId, shadow);
  const opens = bookTrades(open, bookId, shadow);
  const curve = equityCurve(fills);
  const avg = avgWinLoss(fills);
  const nFilled = num(rank?.n_filled) ?? fills.length;
  const wins = num(rank?.n_wins) ?? avg.nWin;
  const net = num(rank?.sum_pnl_inr) ?? fills.reduce((s, t) => s + (num(t.realized_pnl_inr) || 0), 0);
  const wr = nFilled ? Math.round(((wins || 0) / nFilled) * 1000) / 10 : num(rank?.win_rate_net_pct);
  const todayFills = sessionDay ? fills.filter((t) => sessionDate(t.closed_ist || t.opened_ist) === sessionDay) : fills;
  return {
    id: shadow ? `${bookId}·SHADOW` : bookId,
    bookId,
    label: SLOT_LABEL[bookId] || bookId,
    kind: shadow ? "SHADOW" : rank?.kind || "PAPER",
    shadow: Boolean(shadow),
    nFilled,
    nOpen: opens.length,
    nToday: todayFills.length,
    winPct: nFilled ? wr : null,
    vsRandom: shadow ? null : winVsRandom(rank),
    avgWin: avg.avgWin,
    avgLoss: avg.avgLoss,
    net,
    maxDd: maxDrawdown(curve),
    curve,
    badge: slotBadge({ nFilled, openCount: opens.length, shadow }),
    rank,
  };
}

export function buildStrategyCards(board, { uniqueClosed = [], uniqueOpen = [] } = {}) {
  if (!board) return [];
  const rankBy = new Map((board.book_rank || []).map((r) => [r.book_id, r]));
  const ids = [];
  for (const id of PAPER_SLOT_IDS) {
    if (!ids.includes(id)) ids.push(id);
  }
  for (const r of board.book_rank || []) {
    if (r.book_id && !ids.includes(r.book_id)) ids.push(r.book_id);
  }
  for (const id of UNIQUE_BOOKS) {
    if (!ids.includes(id)) ids.push(id);
  }
  const sessionDay = board.session_ist_date || sessionDate(board.as_of_ist);
  const cards = [];
  for (const bookId of ids) {
    cards.push(
      cardFrom({
        bookId,
        rank: rankBy.get(bookId) || null,
        closed: uniqueClosed,
        open: uniqueOpen,
        shadow: false,
        sessionDay,
      }),
    );
    const shadowClosed = bookTrades(uniqueClosed, bookId, true);
    const shadowOpen = bookTrades(uniqueOpen, bookId, true);
    if (shadowClosed.length || shadowOpen.length) {
      cards.push(
        cardFrom({
          bookId,
          rank: null,
          closed: uniqueClosed,
          open: uniqueOpen,
          shadow: true,
          sessionDay,
        }),
      );
    }
  }
  return cards;
}

export function sortStrategyCards(cards, key = "net", dir = "desc") {
  const sign = dir === "asc" ? 1 : -1;
  const val = (c) => {
    if (key === "trades") return c.nFilled ?? -1;
    if (key === "win") return c.winPct ?? -1;
    if (key === "dd") return c.maxDd ?? -1;
    if (key === "name") return c.bookId;
    return c.net ?? 0;
  };
  return [...(cards || [])].sort((a, b) => {
    const av = val(a);
    const bv = val(b);
    if (typeof av === "string" || typeof bv === "string") return sign * String(av).localeCompare(String(bv));
    if (av === bv) return String(a.bookId).localeCompare(String(b.bookId));
    return sign * ((av ?? 0) - (bv ?? 0));
  });
}

export function todayTimeline(open, closed, sessionDay) {
  const dayOf = (t) => sessionDate(t.closed_ist || t.opened_ist || t.last_updated_ist);
  const rows = [...(open || []), ...(closed || [])].filter((t) => !sessionDay || dayOf(t) === sessionDay || !t.closed_ist);
  return rows.sort((a, b) => tradeTs(b) - tradeTs(a));
}

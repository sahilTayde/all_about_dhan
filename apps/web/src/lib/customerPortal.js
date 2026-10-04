/**
 * Customer `/` view-model (C5-03).
 * Paper / shadow / mock only. Five paper seats. No Dhan. No win rates.
 *
 * Auth coordination: packages/auth CUSTOMER_CHANNELS = {signals:public}.
 * This module never reads founder snapshot keys.
 */

export const ALLOWED_BOOK_MODES = Object.freeze(["PAPER", "SHADOW", "MOCK"]);
export const MARKET_VIEWS = Object.freeze(["CALL", "PUT", "HOLD"]);
export const STALE_TTL_MS = 180_000;
export const CUSTOMER_CHANNEL = "signals:public";

/** Never paint LIVE / LIMITED_LIVE on the customer badge. */
export function displayMode(raw) {
  const m = String(raw || "")
    .trim()
    .toUpperCase()
    .replace(/[\s-]+/g, "_");
  if (m === "PAPER" || m === "LIVE_PAPER" || m === "PAPER_LIVE") return "PAPER";
  if (m === "SHADOW") return "SHADOW";
  if (m === "MOCK" || m === "FIXTURE" || m === "DEMO") return "MOCK";
  return "MOCK";
}

export function badgeIsAllowed(label) {
  return ALLOWED_BOOK_MODES.includes(String(label || "").toUpperCase());
}

export function marketView(side) {
  const s = String(side || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "_");
  if (s === "CALL" || s === "CE" || s === "BUY_CE" || s === "BUYCE") return "CALL";
  if (s === "PUT" || s === "PE" || s === "BUY_PE" || s === "BUYPE") return "PUT";
  return "HOLD";
}

export function normalizeSide(side) {
  const view = marketView(side);
  if (view === "CALL") return "BUY_CE";
  if (view === "PUT") return "BUY_PE";
  return "HOLD";
}

function finitePremium(value) {
  if (value === "" || value == null) return false;
  const upper = String(value).trim().toUpperCase();
  if (upper === "DATA_INSUFFICIENT" || upper === "DI" || upper === "UNKNOWN") return false;
  return Number.isFinite(Number(value));
}

export function ticketStatus(signal) {
  if (!signal) return "HOLD";
  const outcome = String(signal.lifecycle?.outcome || signal.outcome || "").toUpperCase();
  if (outcome === "DEALER_KILLED") return "DEALER_KILLED";
  if (["ACHIEVED", "STOPPED", "INVALIDATED", "EXPIRED"].includes(outcome)) return outcome;
  if (outcome === "LOST") return "STOPPED";

  const staged = String(signal.staged?.state || signal.state || "").toUpperCase();
  if (staged === "DEALER_KILLED") return "DEALER_KILLED";
  if (staged === "VETOED") return "HOLD";
  if (marketView(signal.side) === "HOLD") return "HOLD";
  if (staged === "WATCH" || staged === "EARLY" || staged === "CONFIRMED" || staged === "IN-PROGRESS") {
    return staged;
  }
  if (finitePremium(signal.entry) && finitePremium(signal.stop) && finitePremium(signal.target)) {
    return "IN-PROGRESS";
  }
  return "WATCH";
}

export function heroTone(status, view) {
  const s = String(status || "").toUpperCase();
  if (s === "ACHIEVED" || s === "IN-PROGRESS") return "green";
  if (s === "WATCH" || s === "EARLY" || s === "CONFIRMED") return "blue";
  if (s === "HOLD") return "amber";
  if (s === "STOPPED" || s === "INVALIDATED" || s === "DEALER_KILLED") return "red";
  if (s === "EXPIRED") return "grey";
  return view === "HOLD" ? "amber" : "grey";
}

export function isStale(asOf, now = Date.now(), ttlMs = STALE_TTL_MS) {
  if (!asOf) return true;
  const t = Date.parse(asOf);
  if (!Number.isFinite(t)) return true;
  return now - t > ttlMs;
}

export function staleLabel(asOf, now = Date.now(), { placeholder = false } = {}) {
  if (placeholder) return "static fixture";
  if (!asOf) return "DATA_INSUFFICIENT";
  if (isStale(asOf, now)) return "stale";
  return "fresh";
}

function slot(value) {
  if (value === "" || value == null) return "DATA_INSUFFICIENT";
  const u = String(value).trim().toUpperCase();
  if (["DI", "UNKNOWN", "N/A", "NA", "—", "-"].includes(u)) return "DATA_INSUFFICIENT";
  return value;
}

function citeNews(payload) {
  const cited = payload?.cited_news;
  if (cited && typeof cited === "object") {
    const headline = cited.headline || cited.title;
    if (headline) return String(headline);
  }
  if (typeof payload?.news === "string" && payload.news.trim()) return payload.news.trim();
  return "";
}

export function whyLine(signal) {
  const note = signal?.customer?.note || signal?.note || "";
  if (note) return String(note);
  const parts = [signal?.trend, signal?.chain_3m, citeNews(signal)].filter(Boolean);
  return parts.length ? parts.join(" · ") : "DATA_INSUFFICIENT";
}

function bookFrom(raw, fallbackMode) {
  const book = raw || {};
  return {
    label: displayMode(book.label || book.source || fallbackMode),
    note: book.note || "Today only. Not live P/L. Not a win rate.",
    rows: Array.isArray(book.rows) ? book.rows : [],
  };
}

export function deskFromMock(raw) {
  const meta = raw?.meta || {};
  const mode = displayMode(meta.label || meta.source || "MOCK");
  const underlyings =
    Array.isArray(raw?.underlyings) && raw.underlyings.length
      ? raw.underlyings
      : ["NIFTY", "BANKNIFTY", "SENSEX"];
  return {
    feed: "mock",
    mode,
    placeholder: Boolean(meta.placeholder ?? true),
    asOf: meta.asOf || raw?.asOf || "",
    note: meta.note || "Safe mock feed. No Dhan from the browser.",
    underlyings,
    signals: raw?.signals && typeof raw.signals === "object" ? raw.signals : {},
    book: bookFrom(raw?.todaysBook, mode),
    role: "customer",
    denied: [],
  };
}

function payloadOf(item) {
  if (item?.payload && typeof item.payload === "object") return item.payload;
  return item && typeof item === "object" ? item : {};
}

export function deskFromV2Public(snap) {
  const items = snap?.channels?.[CUSTOMER_CHANNEL]?.items || [];
  const signals = {};
  const underlyings = [];
  for (const item of items) {
    const payload = payloadOf(item);
    const und = String(payload.underlying || "NIFTY").toUpperCase();
    if (!underlyings.includes(und)) underlyings.push(und);
    signals[und] = {
      underlying: und,
      side: normalizeSide(payload.side || payload.decision),
      decision: payload.decision,
      trend: payload.trend,
      chain_3m: payload.chain_3m,
      news: payload.news,
      cited_news: payload.cited_news,
      strike: payload.strike,
      entry: payload.entry,
      stop: payload.stop,
      target: payload.target,
      expiry: payload.expiry,
      lots: payload.lots,
      invalid_if: payload.invalid_if,
      timeIst: payload.timeIst,
      staged: { state: payload.state || payload.staged || "" },
      customer: {
        headline: payload.headline || payload.trend || "",
        note: whyLine(payload),
      },
      lifecycle: payload.lifecycle && typeof payload.lifecycle === "object" ? payload.lifecycle : {},
    };
  }
  const list = underlyings.length ? underlyings : ["NIFTY", "BANKNIFTY", "SENSEX"];
  if (!underlyings.length) {
    for (const und of list) {
      signals[und] = { underlying: und, side: "HOLD" };
    }
  }
  const mode = displayMode(snap?.mode || snap?.book_mode || "PAPER");
  return {
    feed: CUSTOMER_CHANNEL,
    mode,
    placeholder: false,
    asOf: snap?.as_of || "",
    note: "V2 signals:public · customer role · paper/shadow only",
    underlyings: list,
    signals,
    book: bookFrom({ label: mode, rows: snap?.book || [] }, mode),
    role: "customer",
    denied: Array.isArray(snap?.denied) ? snap.denied : [],
  };
}

export function isCustomerV2Snapshot(body) {
  if (!body || typeof body !== "object") return false;
  if (body.role && body.role !== "customer") return false;
  return Boolean(body.channels && CUSTOMER_CHANNEL in body.channels);
}

export function selectCustomerView(desk, underlying, now = Date.now()) {
  const und = String(underlying || desk?.underlyings?.[0] || "NIFTY").toUpperCase();
  const signal = desk?.signals?.[und] || { underlying: und, side: "HOLD" };
  const market = marketView(signal.side);
  const status = ticketStatus(signal);
  const waiting = market === "HOLD" || status === "HOLD" || status === "DEALER_KILLED";
  const mode = displayMode(desk?.mode);
  const outcome = String(signal.lifecycle?.outcome || "").toUpperCase();
  return {
    underlying: und,
    market,
    status,
    tone: heroTone(status, market),
    mode,
    bookMode: displayMode(desk?.book?.label || mode),
    feed: desk?.feed || "mock",
    asOf: desk?.asOf || "",
    stale: desk?.placeholder ? false : isStale(desk?.asOf, now),
    staleText: staleLabel(desk?.asOf, now, { placeholder: Boolean(desk?.placeholder) }),
    placeholder: Boolean(desk?.placeholder),
    waiting,
    why: waiting ? signal.customer?.note || "No suggested ticket. HOLD. Not advice." : whyLine(signal),
    invalidIf:
      signal.invalid_if ||
      signal.customer?.invalid_if ||
      (waiting ? "No ticket to invalidate." : "DATA_INSUFFICIENT"),
    outcome: ["ACHIEVED", "STOPPED", "INVALIDATED", "EXPIRED", "DEALER_KILLED"].includes(outcome)
      ? outcome
      : status === "DEALER_KILLED"
        ? "DEALER_KILLED"
        : "",
    ticket: waiting
      ? null
      : {
          strike: slot(signal.strike),
          entry: slot(signal.entry),
          stop: slot(signal.stop),
          target: slot(signal.target),
          lots: signal.lots ?? signal.ticket?.lots ?? "—",
          expiry: signal.expiry || signal.ticket?.expiry || "—",
          time: signal.timeIst || signal.ticket?.timeIst || desk?.asOf || "—",
        },
    bookRows: Array.isArray(desk?.book?.rows) ? desk.book.rows : [],
    underlyings: desk?.underlyings || [und],
    note: desk?.note || "",
  };
}

/** Empty-state fixture for tests. HOLD, no ticket, empty PAPER book. */
export function emptyDeskFixture() {
  return deskFromMock({
    meta: {
      source: "mock",
      label: "MOCK",
      placeholder: true,
      asOf: "2026-10-04T11:00:00+05:30",
      note: "Empty customer fixture. Not a fill.",
    },
    underlyings: ["NIFTY"],
    signals: {
      NIFTY: {
        underlying: "NIFTY",
        side: "HOLD",
        customer: { headline: "", note: "Waiting for the next paper lean." },
        staged: { state: "HOLD" },
      },
    },
    todaysBook: { label: "PAPER", source: "paper", rows: [] },
  });
}

/** One CALL ticket fixture for tests. Premium path only — not a fill. */
export function oneTicketFixture() {
  return deskFromMock({
    meta: {
      source: "mock",
      label: "MOCK",
      placeholder: true,
      asOf: "2026-10-04T11:05:00+05:30",
      note: "One-ticket customer fixture. Not a fill.",
    },
    underlyings: ["NIFTY"],
    signals: {
      NIFTY: {
        underlying: "NIFTY",
        side: "BUY_CE",
        strike: 25000,
        entry: 120,
        stop: 90,
        target: 180,
        expiry: "2026-10-07",
        lots: 1,
        timeIst: "11:05",
        invalid_if: "Spot closes below 24950 or premium loses the 120 entry.",
        customer: {
          headline: "Call ticket — you decide",
          note: "Index trend up. 3m chain bid near ATM. No cited news.",
        },
        staged: { state: "IN-PROGRESS" },
        ticket: { unit: "OPTION_PREMIUM", lots: 1, levels_ready: true, expiry: "2026-10-07" },
      },
    },
    todaysBook: {
      label: "PAPER",
      source: "paper",
      rows: [
        {
          id: "paper-nifty-ce-1",
          timeIst: "11:05",
          underlying: "NIFTY",
          side: "BUY_CE",
          strike: 25000,
          status: "IN-PROGRESS",
          result: "OPEN",
          path: "PAPER",
          entry: 120,
          stop: 90,
          target: 180,
        },
      ],
    },
  });
}

export function formatSlot(value) {
  if (value === "" || value == null) return "DATA_INSUFFICIENT";
  const raw = String(value).trim();
  const upper = raw.toUpperCase();
  if (upper === "DATA_INSUFFICIENT" || upper === "DI" || upper === "UNKNOWN") {
    return "DATA_INSUFFICIENT";
  }
  const n = Number(value);
  if (Number.isFinite(n)) return n.toLocaleString("en-IN");
  return raw;
}

export function formatWhen(value) {
  if (!value || value === "—") return "—";
  const raw = String(value).trim();
  if (/^\d{1,2}:\d{2}/.test(raw)) return raw;
  const t = Date.parse(raw);
  if (!Number.isFinite(t)) return raw;
  try {
    const clock = new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(t);
    return `${clock} IST`;
  } catch {
    return raw;
  }
}

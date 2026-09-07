/** Customer-facing ticket status. Indicator names stay off this surface. */

export const STAGES = ["WATCH", "EARLY", "CONFIRMED", "IN-PROGRESS"];

export const OUTCOMES = [
  "ACHIEVED",
  "STOPPED",
  "INVALIDATED",
  "EXPIRED",
  "LOST",
];

/** Honesty labels shown on customer `/` (Astra + desk 2026-09-06). */
export const HONESTY_LABELS = [
  "NEW SIGNAL",
  "NEW ENTRY",
  "IN-PROGRESS",
  "DO NOT ENTER",
  "INVALIDATED",
  "STOP LOSS HIT",
  "TARGET HIT",
  "TRADE COMPLETED",
  "WAITING FOR NEXT SIGNAL",
];

/**
 * Engine / lifecycle → customer honesty label.
 * Display words are the UI source of truth on `/`.
 */
export const ENGINE_TO_HONESTY = {
  WATCH: "NEW SIGNAL",
  EARLY: "DO NOT ENTER",
  CONFIRMED: "NEW ENTRY",
  "IN-PROGRESS": "IN-PROGRESS",
  VETOED: "DO NOT ENTER",
  STOPPED: "STOP LOSS HIT",
  ACHIEVED: "TARGET HIT",
  INVALIDATED: "INVALIDATED",
  EXPIRED: "INVALIDATED",
  LOST: "TRADE COMPLETED",
  HOLD: "WAITING FOR NEXT SIGNAL",
  WAITING: "WAITING FOR NEXT SIGNAL",
};

export const STATE_LEGEND = [
  {
    id: "WAITING FOR NEXT SIGNAL",
    label: "WAITING FOR NEXT SIGNAL",
    meaning: "No active suggested ticket. Signal window stays blank.",
  },
  {
    id: "NEW SIGNAL",
    label: "NEW SIGNAL",
    meaning: "Lean forming. Not a ticket yet.",
  },
  {
    id: "DO NOT ENTER",
    label: "DO NOT ENTER",
    meaning: "Early lean, veto, or hold. Do not treat as an entry.",
  },
  {
    id: "NEW ENTRY",
    label: "NEW ENTRY",
    meaning: "Setup confirmed as a suggestion. Still not a broker fill.",
  },
  {
    id: "IN-PROGRESS",
    label: "IN-PROGRESS",
    meaning: "Paper path open. Strike and levels are on the ticket.",
  },
  {
    id: "TARGET HIT",
    label: "TARGET HIT",
    meaning: "Paper target printed. Ticket closed.",
  },
  {
    id: "STOP LOSS HIT",
    label: "STOP LOSS HIT",
    meaning: "Paper stop printed. Ticket closed.",
  },
  {
    id: "INVALIDATED",
    label: "INVALIDATED",
    meaning: "Signal withdrawn or window expired unfilled. Do not chase.",
  },
  {
    id: "TRADE COMPLETED",
    label: "TRADE COMPLETED",
    meaning: "Paper path closed (not stop/target wording).",
  },
];

export const SENTIMENT_LEGEND = [
  { id: "BULLISH", meaning: "Tape bias up over that window." },
  { id: "BEARISH", meaning: "Tape bias down over that window." },
  { id: "SIDEWAYS", meaning: "No clean directional bias over that window." },
];

export const CAS_LEGEND = [
  {
    id: "BOUNCE",
    meaning: "Closing auction / cash close looks higher than the 15:15 print.",
  },
  {
    id: "SIDEWAYS",
    meaning: "Auction mixed, or we do not have a live book yet.",
  },
  {
    id: "FALL",
    meaning: "Closing auction / cash close looks lower than the 15:15 print.",
  },
];

export function fieldsFromSignal(signal) {
  if (!signal) {
    return { strike: "", entry: "", stop: "", target: "" };
  }
  return {
    strike: String(signal.strike ?? ""),
    entry: String(signal.entry ?? ""),
    stop: String(signal.stop ?? ""),
    target: String(signal.target ?? ""),
  };
}

export function hasLevels(signal) {
  if (!signal) return false;
  return [signal.strike, signal.entry, signal.stop, signal.target].every(
    (value) => value !== "" && value != null
  );
}

export function outcomeId(lifecycle) {
  const raw = String(lifecycle?.outcome || "").toUpperCase();
  return OUTCOMES.includes(raw) ? raw : "";
}

function mapHonesty(engineKey) {
  const key = String(engineKey || "").toUpperCase();
  return ENGINE_TO_HONESTY[key] || key || "WAITING FOR NEXT SIGNAL";
}

/**
 * Customer honesty status for `/`.
 * Terminal outcome wins; empty/HOLD → WAITING; EARLY/VETOED → DO NOT ENTER.
 */
export function customerStatus(signal) {
  if (!signal) return "WAITING FOR NEXT SIGNAL";

  const closed = outcomeId(signal?.lifecycle);
  if (closed) return mapHonesty(closed);

  const side = String(signal.side || "").toUpperCase();
  if (side === "HOLD" || side === "" || side === "NONE") {
    return "WAITING FOR NEXT SIGNAL";
  }

  const staged = String(signal?.staged?.state || "").toUpperCase();
  if (staged === "VETOED") return "DO NOT ENTER";
  if (staged === "EARLY" || signal?.staged?.waiting) return "DO NOT ENTER";
  if (staged === "WATCH") return "NEW SIGNAL";
  if (staged === "CONFIRMED") return "NEW ENTRY";
  if (staged === "IN-PROGRESS" || hasLevels(signal)) return "IN-PROGRESS";

  return "WAITING FOR NEXT SIGNAL";
}

/** True when the ticket hero should stay blank. */
export function isWaitingStatus(status) {
  return String(status || "") === "WAITING FOR NEXT SIGNAL";
}

export function formatLevel(value) {
  if (value === "" || value == null) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN");
}

export function formatPts(n) {
  if (typeof n !== "number" || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n} pts`;
}

export function sideCopy(side) {
  if (side === "HOLD" || !side) return { action: "HOLD", option: "—", kind: "unk" };
  if (side === "BUY_PE") return { action: "BUY", option: "PE", kind: "pe" };
  if (side === "BUY_CE") return { action: "BUY", option: "CE", kind: "ce" };
  return { action: "—", option: "—", kind: "unk" };
}

export function slugState(state) {
  return String(state || "waitingfornextsignal")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

/** Paper book summary helpers (MOCK / PAPER only). */
export function paperBookStats(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const closed = list.filter((r) => {
    const o = String(r.result || r.outcome || "").toUpperCase();
    return o === "WIN" || o === "LOSS" || o === "SUCCESS" || o === "FLAT";
  });
  const wins = closed.filter((r) => {
    const o = String(r.result || r.outcome || "").toUpperCase();
    return o === "WIN" || o === "SUCCESS";
  });
  const points = list.reduce((sum, r) => {
    const p = Number(r.points);
    return Number.isFinite(p) ? sum + p : sum;
  }, 0);
  const winPct =
    closed.length === 0 ? null : Math.round((wins.length / closed.length) * 1000) / 10;
  return {
    closedCount: closed.length,
    winCount: wins.length,
    pointsCaptured: points,
    winPct,
  };
}

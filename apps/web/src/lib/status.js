/** Customer-facing ticket status. Indicator names stay off this surface. */

export const STAGES = ["WATCH", "EARLY", "CONFIRMED", "IN-PROGRESS"];

export const OUTCOMES = [
  "ACHIEVED",
  "STOPPED",
  "INVALIDATED",
  "EXPIRED",
  "LOST",
];

export const STATE_LEGEND = [
  {
    id: "WATCH",
    label: "WATCH",
    meaning: "Scanning. No live ticket yet.",
  },
  {
    id: "EARLY",
    label: "EARLY",
    meaning: "Early lean. Not confirmed. Wait before treating this as a ticket.",
  },
  {
    id: "CONFIRMED",
    label: "CONFIRMED",
    meaning: "Setup confirmed. Still not a fill promise.",
  },
  {
    id: "IN-PROGRESS",
    label: "IN-PROGRESS",
    meaning: "Live signal issued. Strike and levels are on the ticket. Path is open.",
  },
  {
    id: "VETOED",
    label: "VETOED",
    meaning: "Killed. Do not take.",
  },
  {
    id: "ACHIEVED",
    label: "ACHIEVED",
    meaning: "Target hit. Ticket closed.",
  },
  {
    id: "STOPPED",
    label: "STOPPED",
    meaning: "Stop-loss hit. Ticket closed.",
  },
  {
    id: "INVALIDATED",
    label: "INVALIDATED",
    meaning: "Signal withdrawn. Do not treat as live.",
  },
  {
    id: "EXPIRED",
    label: "EXPIRED",
    meaning: "Time window closed. Do not chase.",
  },
  {
    id: "LOST",
    label: "LOST",
    meaning: "Closed at a loss.",
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

/**
 * Customer status: terminal outcome wins; else a live issued ticket is IN-PROGRESS.
 * WATCH / EARLY / CONFIRMED remain for pre-issue honesty states.
 */
export function customerStatus(signal) {
  const closed = outcomeId(signal?.lifecycle);
  if (closed) return closed;
  if (hasLevels(signal)) return "IN-PROGRESS";
  return String(signal?.staged?.state || "WATCH").toUpperCase();
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
  if (side === "HOLD") return { action: "HOLD", option: "—", kind: "unk" };
  if (side === "BUY_PE") return { action: "BUY", option: "PE", kind: "pe" };
  if (side === "BUY_CE") return { action: "BUY", option: "CE", kind: "ce" };
  return { action: "—", option: "—", kind: "unk" };
}

export function slugState(state) {
  return String(state || "watch")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

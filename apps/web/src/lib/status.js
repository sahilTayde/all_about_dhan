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
  const raw = String(value).trim();
  const upper = raw.toUpperCase();
  if (
    upper === "DATA_INSUFFICIENT" ||
    upper === "DI" ||
    upper === "UNKNOWN" ||
    upper === "N/A" ||
    upper === "NA"
  ) {
    return upper === "UNKNOWN" ? "UNKNOWN" : "DATA_INSUFFICIENT";
  }
  if (raw === "—" || raw === "-") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return raw;
  return n.toLocaleString("en-IN");
}

/** Premium Entry/SL/Target: empty → DATA_INSUFFICIENT (never invent a number). */
export function formatPremiumSlot(value) {
  if (value === "" || value == null) return "DATA_INSUFFICIENT";
  return formatLevel(value);
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

/**
 * Sort paper/fixture book rows newest-first by timeIst (HH:MM or HH:MM:SS).
 * Documented UX: founder sees latest ticket at top.
 */
export function sortBookRowsNewestFirst(rows) {
  const list = Array.isArray(rows) ? [...rows] : [];
  return list.sort((a, b) => {
    const ta = String(a?.timeIst || a?.time || "00:00");
    const tb = String(b?.timeIst || b?.time || "00:00");
    if (ta === tb) return 0;
    return ta < tb ? 1 : -1;
  });
}

/**
 * Customer CE/PE ticket strip = option premium labels.
 * Index overlays belong on the chart — never relabel index as Entry/Stop/Target.
 */
export function levelFieldDefs(unit) {
  const u = String(unit || "OPTION_PREMIUM").toUpperCase();
  // INDEX_POINTS_* is quarantined at the SignalCard — still label as premium slots.
  if (u === "INDEX_POINTS_PROXY" || u === "INDEX_POINTS" || u.includes("PREMIUM") || !u) {
    return [
      { key: "strike", label: "Strike" },
      { key: "entry", label: "Entry (premium)" },
      { key: "stop", label: "Stop (premium)" },
      { key: "target", label: "Target (premium)" },
    ];
  }
  return [
    { key: "strike", label: "Strike" },
    { key: "entry", label: "Entry (premium)" },
    { key: "stop", label: "Stop (premium)" },
    { key: "target", label: "Target (premium)" },
  ];
}


/**
 * Top customer-facing veto / hold reasons when WAITING (no indicator soup).
 * Prefers signal.top_veto_reasons / meta.veto_banner / staged.vetoes.
 */
export function topVetoReasons(signal, deskMeta) {
  const fromSignal = Array.isArray(signal?.top_veto_reasons)
    ? signal.top_veto_reasons
    : Array.isArray(signal?.vetoes)
      ? signal.vetoes
      : Array.isArray(signal?.staged?.vetoes)
        ? signal.staged.vetoes
        : [];
  const fromMeta = Array.isArray(deskMeta?.veto_banner)
    ? deskMeta.veto_banner
    : Array.isArray(deskMeta?.top_veto_reasons)
      ? deskMeta.top_veto_reasons
      : [];
  const merged = [...fromSignal, ...fromMeta]
    .map((r) => String(r || "").trim())
    .filter(Boolean);
  const out = [];
  for (const r of merged) {
    if (!out.includes(r)) out.push(r);
    if (out.length >= 3) break;
  }
  return out;
}

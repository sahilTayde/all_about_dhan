/**
 * Live trade pipeline from recorded fills, skips, and /paper/trace.
 * Never invent a stage. Missing = waiting. MIX-* never shown.
 */
import { PAPER_SLOTS, canonicalSlotId } from "./strategyBoard.js";
import { formatIst, plainText } from "./plainWords.js";

export const PIPE_LANES = Object.freeze(["NIFTY", "SENSEX"]);

export const PIPE_STAGES = Object.freeze([
  { id: "analyst", label: "Analyst", hint: "Signal" },
  { id: "desk", label: "Desk", hint: "Ticket" },
  { id: "overlay", label: "Overlay", hint: "Filters" },
  { id: "boss", label: "Boss", hint: "Decision" },
  { id: "imm", label: "IMM", hint: "Paper fill" },
  { id: "live", label: "In trade", hint: "Open" },
  { id: "exit", label: "Exit", hint: "Close" },
]);

const TRACE_TO_PIPE = Object.freeze({
  analysts: "analyst",
  analyst: "analyst",
  desk: "desk",
  overlay: "overlay",
  risk: "overlay",
  confirm: "overlay",
  boss: "boss",
  broker: "imm",
  fill: "imm",
  imm: "imm",
  execution: "imm",
});

const SLOT_NAME = Object.fromEntries(PAPER_SLOTS.map((s) => [s.id, s.name]));

export function strategyName(t) {
  if (!t) return "";
  for (const id of [t.strategy_id, t.slot, t.journal_tag, t.book_id, t.rule]) {
    const sid = canonicalSlotId(id);
    if (sid && SLOT_NAME[sid]) return SLOT_NAME[sid];
  }
  const raw = canonicalSlotId(t.strategy_id || t.book_id || "");
  if (!raw || /^MIX-/i.test(String(raw))) return "";
  return String(raw);
}

export function scrubMix(value) {
  if (value == null || value === "") return "";
  return String(value)
    .replace(/MIX-[A-Z0-9_-]+/gi, "")
    .replace(/\s{2,}/g, " ")
    .replace(/^[,;:.\s]+|[,;:.\s]+$/g, "")
    .replace(/\bvia\b\s*$/i, "")
    .replace(/\bagreed:?\s*$/i, "Analysts agreed")
    .trim();
}

export function leakMix(value) {
  return /MIX-/i.test(String(value || ""));
}

function clockOf(ist) {
  const f = formatIst(ist);
  return f.text === "—" ? null : f;
}

function clockMs(at) {
  if (!at) return null;
  if (Number.isFinite(at.ms)) return at.ms;
  if (at.raw) {
    const n = Date.parse(at.raw);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function laterClock(a, b) {
  const am = clockMs(a);
  const bm = clockMs(b);
  if (am == null) return b || a || null;
  if (bm == null) return a;
  return bm >= am ? b : a;
}

/** Later station clocks never go backwards vs a previous recorded stage. */
export function monotonicStages(stages) {
  let floor = null;
  return PIPE_STAGES.map((meta) => {
    const s = stages?.[meta.id] || waiting(meta.id);
    if (s.state !== "waiting" && s.at) {
      const next = laterClock(floor, s.at);
      if (clockMs(next) != null) floor = next;
      return { ...s, at: next };
    }
    return s;
  });
}

function waiting(id) {
  const meta = PIPE_STAGES.find((s) => s.id === id) || { id, label: id, hint: "" };
  return {
    id,
    label: meta.label,
    hint: meta.hint,
    state: "waiting",
    who: null,
    why: "waiting",
    at: null,
    rule: null,
    code: null,
    inputs: {},
  };
}

function metaWho(id) {
  return PIPE_STAGES.find((s) => s.id === id)?.label || id;
}

function done(id, { who, why, at, rule, inputs, code } = {}) {
  return {
    ...waiting(id),
    state: "done",
    who: who || metaWho(id),
    why: why || "Recorded",
    at: at || null,
    rule: rule || null,
    code: code || null,
    inputs: inputs || {},
  };
}

function active(id, extra) {
  return { ...done(id, extra), state: "active" };
}

function blocked(id, { who, why, at, rule, inputs, code } = {}) {
  return {
    ...waiting(id),
    state: "blocked",
    who: who || "Overlay",
    why: why || "Skipped",
    at: at || null,
    rule: rule || null,
    code: code || null,
    inputs: inputs || {},
  };
}

const EXIT_PLAIN = Object.freeze({
  TARGET: "Target hit",
  STOP: "Stop hit",
  TIME: "Time exit",
  CANCEL_AGAINST: "Thesis broke",
  CANCEL_NO_PROGRESS: "Exited: no progress",
  COVER_LONG_UNWIND: "Long unwind",
  OVERLAY_COIL: "Skipped: coil market",
  NO_NEW_AFTER_1516: "Skipped: too late in the session",
  PATH_KIND_HOLD: "Skipped: coil market",
  SIDEWAYS_HOLD: "Skipped: coil market",
});

const RULE_PLAIN = Object.freeze({
  OVERLAY_COIL: "skip coil market",
  PATH_KIND_HOLD: "skip coil market",
  SIDEWAYS_HOLD: "skip coil market",
  CANCEL_NO_PROGRESS: "no progress",
  CANCEL_AGAINST: "thesis broke",
  NO_NEW_AFTER_1516: "too late in the session",
  TARGET: "target hit",
  STOP: "stop hit",
  TIME: "time exit",
});

export function engineCode(raw) {
  const s = String(raw || "").trim();
  if (!s) return null;
  const u = s.toUpperCase();
  if (EXIT_PLAIN[u]) return u;
  // Token-like codes only. Never match STOP inside "dropped to the stop".
  if (/^[A-Z][A-Z0-9_]+$/.test(u)) {
    for (const key of Object.keys(EXIT_PLAIN)) {
      if (u.includes(key)) return key;
    }
    return u;
  }
  return null;
}

function cleanWhy(raw, fallback) {
  const s = scrubMix(raw);
  if (!s) return fallback;
  const code = engineCode(s);
  if (code && EXIT_PLAIN[code]) return EXIT_PLAIN[code];
  if (/coil/i.test(s)) return "Skipped: coil market";
  if (/no progress/i.test(s)) return "Exited: no progress";
  if (/^[A-Z][A-Z0-9_]+$/.test(s)) return s.replaceAll("_", " ").toLowerCase();
  return plainText(s, fallback);
}

function cleanRule(raw) {
  const s = scrubMix(raw);
  if (!s) return null;
  const code = engineCode(s);
  if (code && RULE_PLAIN[code]) return RULE_PLAIN[code];
  if (/coil/i.test(s)) return "skip coil market";
  if (/^[A-Z][A-Z0-9_]+$/.test(s)) return s.replaceAll("_", " ").toLowerCase();
  return null;
}

function cleanInputs(fields) {
  const inputs = {};
  for (const [k, v] of Object.entries(fields || {})) {
    const key = String(k);
    if (/book|mix|journal/i.test(key)) continue;
    if (v == null || v === "") continue;
    if (typeof v === "string") {
      if (leakMix(v) && !scrubMix(v)) continue;
      const text = scrubMix(v) || plainText(v);
      if (!text || leakMix(text)) continue;
      inputs[key] = text;
    } else if (Array.isArray(v)) {
      const list = v.map((x) => (typeof x === "string" ? scrubMix(x) : x)).filter((x) => x && !leakMix(x));
      if (list.length) inputs[key] = list.join(", ");
    } else if (typeof v !== "object") {
      inputs[key] = v;
    }
  }
  return inputs;
}

export function skipWhoWhy(row) {
  const blob = `${row?.reason || ""} ${row?.why || ""} ${row?.action || ""} ${row?.detail || ""}`;
  const who = /overlay|coil|chop|stall|regime/i.test(blob)
    ? "Overlay"
    : /boss|picker|observer|veto/i.test(blob)
      ? "Boss"
      : /desk/i.test(blob)
        ? "Desk"
        : /analyst|model/i.test(blob)
          ? "Analyst"
          : "Overlay";
  if (/coil|chop/i.test(blob)) return { who, why: "Skipped: coil market", code: "OVERLAY_COIL", rule: "skip coil market" };
  if (/NO_NEW_AFTER/i.test(blob)) {
    return { who, why: "Skipped: too late in the session", code: "NO_NEW_AFTER_1516", rule: "too late in the session" };
  }
  if (/CANCEL_AGAINST/i.test(blob)) return { who, why: "Skipped: thesis broke", code: "CANCEL_AGAINST", rule: "thesis broke" };
  if (/CANCEL_NO_PROGRESS/i.test(blob)) {
    return { who, why: "Exited: no progress", code: "CANCEL_NO_PROGRESS", rule: "no progress" };
  }
  const why = cleanWhy(row?.why || row?.reason, "Skipped");
  const code = engineCode(row?.reason || row?.why);
  return { who, why, code, rule: cleanRule(row?.reason) };
}

const JOURNAL_STAGE = Object.freeze({
  analyst: "analyst",
  llm_explain: "analyst",
  desk: "desk",
  overlay: "overlay",
  boss: "boss",
  imm: "imm",
  in_trade: "live",
  live: "live",
  exit: "exit",
});

const MARKET_PLAIN = Object.freeze({
  "trend up": "trend up",
  "trend down": "trend down",
  chop: "chop",
  "tight range": "tight range",
  "expiry pin": "expiry pin",
  "high-VIX": "high-VIX",
  TREND_UP: "trend up",
  TREND_DOWN: "trend down",
  CHOP: "chop",
  CHOPPY: "chop",
  TIGHT_RANGE: "tight range",
  EXPIRY_PIN: "expiry pin",
  HIGH_VIX: "high-VIX",
});

export function plainMarketType(raw) {
  if (raw == null || raw === "") return "";
  const s = String(raw).trim();
  if (MARKET_PLAIN[s]) return MARKET_PLAIN[s];
  const key = s.toLowerCase().replace(/[\s_]+/g, "-");
  if (key === "trend-up" || key === "uptrend") return "trend up";
  if (key === "trend-down" || key === "downtrend") return "trend down";
  if (key === "tight-range" || key === "range") return "tight range";
  if (key === "expiry-pin" || key === "expiry") return "expiry pin";
  if (key === "high-vix" || key === "highvix") return "high-VIX";
  if (key === "chop" || key === "choppy" || key === "sideways") return "chop";
  return "";
}

export function fromJournal(rows) {
  const out = {};
  for (const row of rows || []) {
    const id = JOURNAL_STAGE[row.stage];
    if (!id) continue;
    const at = clockOf(row.ts_ist || row.ts);
    const who = row.actor || metaWho(id);
    const why = cleanWhy(row.reason, "waiting");
    const code = engineCode(row.reason);
    const inputs = cleanInputs(row.inputs || {});
    const extra = { who, why, at, rule: cleanRule(row.reason), code, inputs };
    if (row.decision === "skip") out[id] = blocked(id, extra);
    else if (id === "live" && row.decision === "pass") out[id] = active(id, extra);
    else if (row.decision === "fill" || row.decision === "exit" || row.decision === "pass") out[id] = done(id, extra);
  }
  return out;
}

function journalForLane(rows, und, tradeId) {
  const mine = (rows || []).filter((r) => String(r.underlying || "").toUpperCase() === und);
  if (tradeId) {
    return mine.filter((r) => r.candidate_id === tradeId || r.trade_id === tradeId);
  }
  const ids = [...new Set(mine.map((r) => r.candidate_id).filter(Boolean))];
  const latest = ids[ids.length - 1];
  return latest ? mine.filter((r) => r.candidate_id === latest) : mine;
}

function fromTrace(trace) {
  const out = {};
  for (const step of trace?.steps || []) {
    const id = TRACE_TO_PIPE[step.id];
    if (!id) continue;
    const inputs = cleanInputs(step.fields);
    const why = cleanWhy(step.why || step.decided, step.status === "NO_DATA" ? "waiting" : "Recorded");
    const at = clockOf(step.at || step.ist || step.fields?.opened);
    if (step.status === "NO_DATA") {
      if (!out[id]) out[id] = waiting(id);
      continue;
    }
    const code = engineCode(step.why || step.source || step.decided);
    if (/skip|veto|block|fail|hold/i.test(`${step.status} ${step.why} ${step.decided}`)) {
      out[id] = blocked(id, { who: metaWho(id), why, at, rule: cleanRule(step.source || step.why), code, inputs });
    } else {
      out[id] = done(id, { who: metaWho(id), why, at, rule: cleanRule(step.source), code, inputs });
    }
  }
  return out;
}

function mergeStages(base, extra) {
  const out = { ...base };
  for (const [id, stage] of Object.entries(extra || {})) {
    if (!stage) continue;
    const prev = out[id];
    if (stage.state === "waiting" && prev && prev.state !== "waiting") continue;
    out[id] = {
      ...stage,
      at: stage.at || prev?.at || null,
      inputs: { ...(prev?.inputs || {}), ...(stage.inputs || {}) },
      why: stage.why && stage.why !== "Recorded" ? stage.why : prev?.why || stage.why,
      code: stage.code || prev?.code || null,
      rule: stage.rule || prev?.rule || null,
    };
  }
  return out;
}

function inferFromTrade(t) {
  const openAt = clockOf(t.opened_ist);
  const closeAt = clockOf(t.closed_ist);
  const kind = t.market_kind_open || t.index_regime;
  const name = strategyName(t);
  const stages = {
    analyst: done("analyst", {
      why: t.llm_explanation || (name ? `${name} spoke` : "Analyst recorded"),
      at: openAt,
      inputs: cleanInputs({
        side: t.side,
        market_type: plainMarketType(t.market_type),
        explanation: t.llm_explanation,
      }),
    }),
    desk: done("desk", {
      why: `${t.side} ${t.atm_strike ?? ""}`.trim(),
      at: openAt,
      inputs: cleanInputs({ entry: t.entry, lots: t.lots }),
    }),
    overlay: done("overlay", {
      why: kind ? `Market ${kind}` : "Filters passed",
      at: openAt,
      rule: kind,
      inputs: cleanInputs({ market: kind }),
    }),
    boss: done("boss", { why: `Buy ${t.side}`, at: openAt }),
    imm: done("imm", { why: "Paper fill", at: openAt, inputs: cleanInputs({ entry: t.entry }) }),
    live:
      t.exit == null && !t.closed_ist
        ? active("live", { why: "Trade in progress", at: laterClock(openAt, clockOf(t.last_updated_ist)) })
        : done("live", { why: "Was in trade", at: openAt }),
    exit:
      t.exit != null || t.closed_ist
        ? done("exit", {
            why: cleanWhy(t.exit_reason, "Closed"),
            at: closeAt,
            code: engineCode(t.exit_reason),
            inputs: cleanInputs({ exit: t.exit }),
          })
        : waiting("exit"),
  };
  return stages;
}

function inferFromSkip(row) {
  const { who, why, code, rule } = skipWhoWhy(row);
  const at = clockOf(row.last_updated_ist || row.ts_ist || row.opened_ist);
  const blockedId = who === "Boss" ? "boss" : who === "Desk" ? "desk" : who === "Analyst" ? "analyst" : "overlay";
  const stages = Object.fromEntries(PIPE_STAGES.map((s) => [s.id, waiting(s.id)]));
  if (blockedId !== "analyst") stages.analyst = done("analyst", { why: "Signal seen", at });
  if (blockedId === "overlay" || blockedId === "boss") stages.desk = done("desk", { why: "Ticket formed", at });
  stages[blockedId] = blocked(blockedId, {
    who,
    why,
    at,
    rule: rule || cleanRule(row.reason),
    code: code || engineCode(row.reason),
    inputs: cleanInputs({ side: row.side, market: row.market_kind || row.regime }),
  });
  return stages;
}

function finish(und, kind, title, trade, stages) {
  const list = monotonicStages(stages);
  return {
    underlying: und,
    kind,
    title: scrubMix(title) || `${und} · waiting`,
    name: strategyName(trade),
    tradeId: trade?.trade_id || trade?.id || null,
    stages: list,
    who: list.find((s) => s.state === "blocked")?.who || null,
    why: list.find((s) => s.state === "blocked")?.why || list.find((s) => s.state === "active")?.why || null,
  };
}

export function buildLane(underlying, { open = [], closed = [], skips = [], traces = {}, journal = [] } = {}) {
  const und = String(underlying || "").toUpperCase();
  const live = (open || []).find((t) => String(t.underlying).toUpperCase() === und) || null;
  const lastClosed = (closed || []).find((t) => String(t.underlying).toUpperCase() === und) || null;
  const skip = (skips || []).find((s) => String(s.underlying).toUpperCase() === und) || null;
  const jRows = journalForLane(journal, und, live?.trade_id || lastClosed?.trade_id);
  const jStages = fromJournal(jRows);
  if (live) {
    const stages = mergeStages(mergeStages(inferFromTrade(live), fromTrace(traces[live.trade_id])), jStages);
    stages.live =
      jStages.live ||
      active("live", {
        why: "Trade in progress",
        at: laterClock(clockOf(live.opened_ist), clockOf(live.last_updated_ist)),
      });
    stages.exit = jStages.exit || waiting("exit");
    return finish(und, "live", `${und} ${live.side} ${live.atm_strike ?? ""}`.trim(), live, stages);
  }
  if (skip) {
    return finish(und, "skipped", `${und} skipped`, skip, mergeStages(inferFromSkip(skip), jStages));
  }
  if (lastClosed) {
    const stages = mergeStages(mergeStages(inferFromTrade(lastClosed), fromTrace(traces[lastClosed.trade_id])), jStages);
    return finish(und, "closed", `${und} ${lastClosed.side} closed`, lastClosed, stages);
  }
  if (Object.keys(jStages).length) {
    const blockedRow = Object.values(jStages).find((s) => s.state === "blocked");
    const kind = blockedRow ? "skipped" : "empty";
    return finish(und, kind, blockedRow ? `${und} skipped` : `${und} · waiting`, null, jStages);
  }
  return finish(und, "empty", `${und} · waiting`, null, Object.fromEntries(PIPE_STAGES.map((s) => [s.id, waiting(s.id)])));
}

export function stagesForRecord(row, traces = {}) {
  if (!row) return PIPE_STAGES.map((s) => waiting(s.id));
  if (row.exit != null || row.closed_ist || row.opened_ist) {
    const stages = mergeStages(inferFromTrade(row), fromTrace(traces[row.trade_id]));
    return monotonicStages(stages);
  }
  return monotonicStages(inferFromSkip(row));
}

function dayOf(t) {
  return String(t.closed_ist || t.opened_ist || t.last_updated_ist || t.ts_ist || "").slice(0, 10);
}

export function pipelineHistory(closed, skips, sessionDay, liveIds = new Set()) {
  const fills = (closed || [])
    .filter((t) => !liveIds.has(t.trade_id))
    .filter((t) => !sessionDay || dayOf(t) === sessionDay)
    .map((t) => ({
      id: t.trade_id,
      underlying: t.underlying,
      label: `${t.underlying} ${t.side} ${t.atm_strike ?? ""}`.trim(),
      name: strategyName(t),
      state: "done",
      why: cleanWhy(t.exit_reason, "Closed"),
      code: engineCode(t.exit_reason),
      pnl: Number.isFinite(Number(t.realized_pnl_inr)) ? Number(t.realized_pnl_inr) : null,
      at: clockOf(t.closed_ist || t.opened_ist),
      record: t,
    }));
  const skipped = (skips || []).map((s, i) => {
    const { why, code } = skipWhoWhy(s);
    return {
      id: s.id || s.trade_id || `skip-${s.underlying}-${i}`,
      underlying: s.underlying,
      label: `${s.underlying} ${s.side || ""}`.trim(),
      name: strategyName(s),
      state: "blocked",
      why,
      code,
      pnl: null,
      at: clockOf(s.last_updated_ist || s.ts_ist),
      record: s,
    };
  });
  return [...skipped, ...fills].slice(0, 12);
}

export function buildPipelines(board, { uniqueOpen = [], uniqueClosed = [], traces = {}, journal } = {}) {
  const skips = board?.seen_not_taken?.skipped_latest || board?.skipped || [];
  const sessionDay = board?.session_ist_date;
  const liveIds = new Set((uniqueOpen || []).map((t) => t.trade_id).filter(Boolean));
  const rows = journal || board?.decision_journal || [];
  return {
    lanes: PIPE_LANES.map((und) => buildLane(und, { open: uniqueOpen, closed: uniqueClosed, skips, traces, journal: rows })),
    history: pipelineHistory(uniqueClosed, skips, sessionDay, liveIds),
  };
}

export function pipelineText(model) {
  const bits = [];
  for (const lane of model.lanes || []) {
    bits.push(lane.title, lane.name, lane.why);
    for (const s of lane.stages || []) bits.push(s.label, s.why, s.who, s.rule, ...Object.values(s.inputs || {}));
  }
  for (const row of model.history || []) bits.push(row.label, row.name, row.why);
  return bits.filter(Boolean).join(" ");
}

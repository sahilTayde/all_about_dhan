/**
 * Customer trade-journey view-model (C5-08).
 * Paper / shadow / mock only. Never invent live prices.
 * Path comes from last-known journal marks or the paper/demo feed.
 */

import { formatWhen } from "./customerPortal.js";

export const JOURNEY_STEPS = Object.freeze(["SIGNAL", "ENTRY", "HOLD", "EXIT"]);

const EXIT_STATUSES = new Set(["ACHIEVED", "STOPPED", "INVALIDATED", "EXPIRED", "DEALER_KILLED"]);
const SIGNAL_STATUSES = new Set(["WATCH", "EARLY"]);

function finiteNum(value) {
  if (value === "" || value == null) return false;
  const upper = String(value).trim().toUpperCase();
  if (["DATA_INSUFFICIENT", "DI", "UNKNOWN", "N/A", "NA", "—", "-"].includes(upper)) return false;
  return Number.isFinite(Number(value));
}

function asPoint(t, v, label) {
  return { t: Number(t), v: Number(v), label: label || "" };
}

/** Active journey phase. HOLD here means the open paper path, not market-view HOLD. */
export function journeyPhase(status, { waiting = false, hasTicket = false } = {}) {
  const s = String(status || "").toUpperCase();
  if (EXIT_STATUSES.has(s)) return "EXIT";
  if (s === "IN-PROGRESS" && hasTicket && !waiting) return "HOLD";
  if (s === "IN-PROGRESS" || s === "CONFIRMED") return hasTicket && !waiting ? "ENTRY" : "SIGNAL";
  if (SIGNAL_STATUSES.has(s)) return "SIGNAL";
  if (waiting || s === "HOLD" || !s) return "SIGNAL";
  return "SIGNAL";
}

export function journeySteps(phase) {
  const idx = JOURNEY_STEPS.indexOf(phase);
  const activeAt = idx < 0 ? 0 : idx;
  return JOURNEY_STEPS.map((id, i) => ({
    id,
    label: id,
    state: i < activeAt ? "done" : i === activeAt ? "active" : "wait",
  }));
}

export function lastKnownPath({ chart, ticket, bookRow, lifecycle } = {}) {
  const bars = chart?.bars;
  if (Array.isArray(bars) && bars.length >= 2) {
    const points = [];
    for (const bar of bars) {
      const value = bar?.v ?? bar?.value;
      if (!finiteNum(value)) continue;
      points.push(asPoint(bar.t ?? bar.time ?? points.length, value, bar.label));
    }
    if (points.length >= 2) {
      const label = String(chart.label || "MOCK").toUpperCase();
      return {
        points,
        source: label === "MOCK" || label === "FIXTURE" || label === "DEMO" ? "paper-demo" : "paper-demo",
        unit: chart.unit || "INDEX_POINTS",
        invented: false,
      };
    }
  }

  const marks = bookRow?.path_marks || bookRow?.marks;
  if (Array.isArray(marks) && marks.length >= 2) {
    const points = [];
    for (const [i, mark] of marks.entries()) {
      if (!finiteNum(mark?.v ?? mark?.value)) continue;
      points.push(asPoint(mark.t ?? mark.time ?? i, mark.v ?? mark.value, mark.label));
    }
    if (points.length >= 2) {
      return {
        points,
        source: "last-known journal",
        unit: bookRow.unit || "OPTION_PREMIUM",
        invented: false,
      };
    }
  }

  if (ticket && finiteNum(ticket.entry)) {
    const entry = Number(ticket.entry);
    const recorded =
      finiteNum(bookRow?.last_mark) ? Number(bookRow.last_mark)
      : finiteNum(bookRow?.points) ? entry + Number(bookRow.points)
      : finiteNum(lifecycle?.shadowPaper?.mtmPts) ? entry + Number(lifecycle.shadowPaper.mtmPts)
      : finiteNum(lifecycle?.mtmPts) ? entry + Number(lifecycle.mtmPts)
      : null;
    const points = [asPoint(0, entry, "entry")];
    if (recorded != null) points.push(asPoint(1, recorded, "last-known"));
    return {
      points,
      source: recorded != null ? "last-known journal" : "last-known ticket",
      unit: "OPTION_PREMIUM",
      invented: false,
    };
  }

  return { points: [], source: "DATA_INSUFFICIENT", unit: "", invented: false };
}

export function journalStamp(journal) {
  if (!journal || typeof journal !== "object") return null;
  const tape = journal.tape_last && typeof journal.tape_last === "object" ? journal.tape_last : {};
  const asOf = tape.as_of_ist || tape.as_of || journal.as_of || "";
  const lastPrice = finiteNum(tape.ltp) ? Number(tape.ltp) : finiteNum(tape.last) ? Number(tape.last) : null;
  return {
    asOf,
    when: asOf ? formatWhen(asOf) : "",
    source: tape.source || "journal",
    n: Number.isFinite(Number(journal.n)) ? Number(journal.n) : Array.isArray(journal.items) ? journal.items.length : 0,
    lastPrice,
  };
}

export function journeyChips(view, path, journal) {
  const chips = [
    { id: "mode", label: view?.mode || "MOCK", tone: String(view?.mode || "mock").toLowerCase() },
    { id: "status", label: view?.status || "HOLD", tone: view?.tone || "amber" },
    { id: "market", label: view?.market || "HOLD", tone: String(view?.market || "hold").toLowerCase() },
  ];
  if (view?.staleText) {
    chips.push({ id: "fresh", label: view.staleText, tone: view.stale ? "red" : "green" });
  }
  if (path?.source && path.source !== "DATA_INSUFFICIENT") {
    chips.push({ id: "path", label: path.source, tone: "grey" });
  }
  const stamp = journalStamp(journal);
  if (stamp?.asOf) {
    chips.push({ id: "tape", label: stamp.when ? `tape ${stamp.when}` : "last known tape", tone: "grey" });
  }
  return chips;
}

export function sparklineGeometry(points, { width = 320, height = 96, pad = 12 } = {}) {
  if (!Array.isArray(points) || points.length === 0) {
    return { d: "", area: "", dots: [], width, height, pad };
  }
  const ts = points.map((p) => Number(p.t));
  const vs = points.map((p) => Number(p.v));
  const tMin = Math.min(...ts);
  const tMax = Math.max(...ts);
  const vMin = Math.min(...vs);
  const vMax = Math.max(...vs);
  const tSpan = tMax - tMin || 1;
  const vSpan = vMax - vMin || 1;
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;
  const dots = points.map((p) => {
    const x = pad + ((Number(p.t) - tMin) / tSpan) * innerW;
    const y = pad + (1 - (Number(p.v) - vMin) / vSpan) * innerH;
    return { x, y, t: Number(p.t), v: Number(p.v), label: p.label || "" };
  });
  const d = dots.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
  const last = dots[dots.length - 1];
  const first = dots[0];
  const area = `${d} L${last.x.toFixed(2)},${(height - pad).toFixed(2)} L${first.x.toFixed(2)},${(height - pad).toFixed(2)} Z`;
  return { d, area, dots, width, height, pad, vMin, vMax };
}

export function motionAllowed(query = globalThis.matchMedia) {
  try {
    const media = typeof query === "function" ? query("(prefers-reduced-motion: reduce)") : query;
    return !media?.matches;
  } catch {
    return true;
  }
}

export function buildJourney(view, journal) {
  const path = lastKnownPath({
    chart: view?.chart,
    ticket: view?.ticket,
    bookRow: view?.bookRow,
    lifecycle: view?.lifecycle,
  });
  const phase = journeyPhase(view?.status, {
    waiting: Boolean(view?.waiting),
    hasTicket: Boolean(view?.ticket),
  });
  return {
    phase,
    steps: journeySteps(phase),
    chips: journeyChips(view, path, journal),
    path,
    spark: sparklineGeometry(path.points),
    stamp: journalStamp(journal),
  };
}

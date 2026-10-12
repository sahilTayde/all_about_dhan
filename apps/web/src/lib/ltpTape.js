import { useEffect, useRef, useState } from "react";
import { num } from "./deskModel.js";

const KEY = "desk.ltpTape.v1";

function load() {
  try {
    const raw = JSON.parse(sessionStorage.getItem(KEY) || "{}");
    return raw && typeof raw === "object" ? raw : {};
  } catch {
    return {};
  }
}

/**
 * Premium prints seen on the live feed, per trade_id: [{t (unix s), p}].
 * The API sends no candle history, so this tape only holds the entry fill, every last_ltp
 * the feed pushes while this browser tab is open, and the exit fill. Never interpolated.
 */
export function useLtpTape(rows) {
  const ref = useRef(null);
  if (ref.current == null) ref.current = load();
  const [, bump] = useState(0);
  useEffect(() => {
    const tape = ref.current;
    let changed = false;
    const add = (id, t, p) => {
      if (!id || t == null || p == null) return;
      const list = (tape[id] = tape[id] || []);
      if (list.some((x) => x.t === t && x.p === p)) return;
      list.push({ t, p });
      list.sort((a, b) => a.t - b.t);
      if (list.length > 4000) list.splice(0, list.length - 4000);
      changed = true;
    };
    for (const r of rows || []) {
      const id = r.trade_id;
      add(id, num(r.opened_ts), num(r.entry));
      if (r.closed_ts != null) add(id, num(r.closed_ts), num(r.exit));
      else add(id, num(r.last_updated_ts), num(r.last_ltp));
    }
    if (changed) {
      try {
        sessionStorage.setItem(KEY, JSON.stringify(tape));
      } catch {
        /* storage full: keep in memory */
      }
      bump((n) => n + 1);
    }
  }, [rows]);
  return ref.current;
}

/** 1-minute OHLC candles from prints. */
export function toCandles(prints) {
  const out = [];
  for (const { t, p } of prints || []) {
    const m = Math.floor(t / 60) * 60;
    const last = out[out.length - 1];
    if (last && last.time === m) {
      last.high = Math.max(last.high, p);
      last.low = Math.min(last.low, p);
      last.close = p;
    } else out.push({ time: m, open: last ? last.close : p, high: Math.max(p, last ? last.close : p), low: Math.min(p, last ? last.close : p), close: p });
  }
  return out;
}

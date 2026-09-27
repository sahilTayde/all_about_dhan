import { useEffect, useState } from "react";
import { BOARD_POLL_MS } from "./paperBoard.js";

export const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const POLL_MS = BOARD_POLL_MS;

async function getJson(url, signal) {
  const res = await fetch(url, { signal, cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** API down: the static mock board and exam, clearly marked offline. No health, no history. */
export async function mockSnapshot(signal) {
  const [board, exam] = await Promise.all([
    getJson("/mock/ml_paper_dashboard.json", signal),
    getJson("/mock/sod_exam_report.json", signal).catch(() => null),
  ]);
  return { ok: true, offline: true, board, exam, health: [], alerts: null, days: [], account: null, founder: {} };
}

/**
 * One feed per page: server-sent events from /ui/stream (pushed on change). If the stream drops,
 * one batched poll of /ui/snapshot every 2 s, which re-opens the stream as soon as the API answers.
 * `conn` is live | polling | offline; `latencyMs` is fetch-to-state time of the last update.
 */
export function useFeed() {
  const [state, setState] = useState({ snap: null, conn: "connecting", latencyMs: null });

  useEffect(() => {
    let es = null;
    let timer = null;
    let stopped = false;
    const ac = new AbortController();

    const accept = (snap, conn, t0) =>
      setState({ snap, conn, latencyMs: t0 == null ? null : Math.round(performance.now() - t0) });

    function openStream() {
      if (typeof EventSource === "undefined") return poll();
      es = new EventSource(`${API_BASE}/ui/stream`);
      es.onmessage = (e) => {
        const t0 = performance.now();
        accept(JSON.parse(e.data), "live", t0);
      };
      es.onerror = () => {
        es.close();
        es = null;
        setState((s) => ({ ...s, conn: "polling" }));
        if (!stopped) timer = setTimeout(poll, POLL_MS);
      };
    }

    async function poll() {
      const t0 = performance.now();
      try {
        const snap = await getJson(`${API_BASE}/ui/snapshot?t=${Date.now()}`, ac.signal);
        accept(snap, "polling", t0);
        if (!stopped) return openStream();
      } catch (err) {
        if (err?.name === "AbortError") return;
        try {
          accept(await mockSnapshot(ac.signal), "offline", t0);
        } catch {
          setState((s) => ({ ...s, conn: "offline" }));
        }
      }
      if (!stopped) timer = setTimeout(poll, POLL_MS);
    }

    poll();
    return () => {
      stopped = true;
      ac.abort();
      if (es) es.close();
      clearTimeout(timer);
    };
  }, []);

  return state;
}

const _trace = new Map();

export async function fetchTrace(tradeId, { signal, force = false } = {}) {
  if (!force && _trace.has(tradeId)) return _trace.get(tradeId);
  const v2 = import.meta.env.VITE_V2_FEED === "1";
  const url = v2
    ? `${API_BASE}/v2/trace?token=founder&trade_id=${encodeURIComponent(tradeId)}`
    : `${API_BASE}/paper/trace?trade_id=${encodeURIComponent(tradeId)}`;
  const json = await getJson(url, signal);
  if (json?.closed) _trace.set(tradeId, json); // an open trade's trace keeps changing: never cache it
  return json;
}

export function fetchDay(day, { signal } = {}) {
  return getJson(`${API_BASE}/paper/history?day=${encodeURIComponent(day)}`, signal);
}

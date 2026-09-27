/**
 * V2-13 Desk/Founder feed: GET /v2/snapshot then WS /v2/ws (snapshot + seq deltas).
 * Behind VITE_V2_FEED=1. Falls back to /v2/stream SSE, then /v2/snapshot poll.
 * Browser never talks to Dhan or Redis. PAPER only.
 */
import { useEffect, useState } from "react";
import { API_BASE, useFeed } from "./feed.js";
import { BOARD_POLL_MS } from "./paperBoard.js";

export const V2_FEED_ON = import.meta.env.VITE_V2_FEED === "1";

function applyDelta(snap, msg) {
  if (!snap || !msg) return snap;
  const next = { ...snap, as_of: msg.as_of || snap.as_of };
  if (msg.op === "snapshot" && msg.channel === "positions" && msg.data?.items) {
    next.positions = msg.data.items;
  }
  if (msg.op === "delta" && msg.channel === "positions" && msg.envelope?.payload) {
    const row = msg.envelope.payload;
    const pid = row.position_id;
    const list = [...(next.positions || [])];
    const i = list.findIndex((p) => p.position_id === pid);
    if (msg.envelope.event_type === "POSITION_CLOSED") {
      next.positions = list.filter((p) => p.position_id !== pid);
    } else if (i >= 0) list[i] = { ...list[i], ...row };
    else list.push(row);
    if (msg.envelope.event_type !== "POSITION_CLOSED") next.positions = list;
  }
  return next;
}

export function useV2Feed() {
  const [state, setState] = useState({ snap: null, conn: "connecting", latencyMs: null });

  useEffect(() => {
    let ws = null;
    let es = null;
    let timer = null;
    let stopped = false;
    const ac = new AbortController();
    let lastSeq = {};

    const accept = (snap, conn, t0) =>
      setState({ snap, conn, latencyMs: t0 == null ? null : Math.round(performance.now() - t0) });

    function onMsg(msg, conn, t0) {
      if (msg.op === "delta" && lastSeq[msg.channel] != null && msg.seq !== lastSeq[msg.channel] + 1) {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ op: "resync", channel: msg.channel }));
        }
        return;
      }
      if (typeof msg.seq === "number") lastSeq[msg.channel] = msg.seq;
      setState((s) => ({
        snap: msg.op === "snapshot" && msg.channel == null ? msg : applyDelta(s.snap, msg),
        conn,
        latencyMs: t0 == null ? null : Math.round(performance.now() - t0),
      }));
    }

    async function boot() {
      const t0 = performance.now();
      try {
        const res = await fetch(`${API_BASE}/v2/snapshot?role=founder&t=${Date.now()}`, {
          signal: ac.signal,
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        accept(await res.json(), "polling", t0);
      } catch (err) {
        if (err?.name === "AbortError") return;
        setState((s) => ({ ...s, conn: "offline" }));
        if (!stopped) timer = setTimeout(boot, BOARD_POLL_MS);
        return;
      }
      if (stopped) return;
      const url = `${API_BASE.replace(/^http/, "ws") || (location.protocol === "https:" ? "wss://" : "ws://") + location.host}/v2/ws?role=founder&channels=positions,decisions,health,market:NIFTY`;
      try {
        ws = new WebSocket(url);
        ws.onmessage = (e) => onMsg(JSON.parse(e.data), "live", performance.now());
        ws.onerror = () => {
          if (ws) ws.close();
          ws = null;
          openSse();
        };
      } catch {
        openSse();
      }
    }

    function openSse() {
      if (typeof EventSource === "undefined") {
        timer = setTimeout(boot, BOARD_POLL_MS);
        return;
      }
      es = new EventSource(`${API_BASE}/v2/stream`);
      es.onmessage = (e) => accept(JSON.parse(e.data), "live", performance.now());
      es.onerror = () => {
        es.close();
        es = null;
        setState((s) => ({ ...s, conn: "polling" }));
        if (!stopped) timer = setTimeout(boot, BOARD_POLL_MS);
      };
    }

    boot();
    return () => {
      stopped = true;
      ac.abort();
      if (ws) ws.close();
      if (es) es.close();
      clearTimeout(timer);
    };
  }, []);

  return state;
}

/** Compile-time switch: Vite inlines VITE_V2_FEED so only one hook is used. */
export function useDeskFeed() {
  return V2_FEED_ON ? useV2Feed() : useFeed();
}

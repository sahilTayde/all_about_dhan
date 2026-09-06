/**
 * Paper-desk data loader.
 *
 * Never call Dhan / DhanHQ from the browser. This module either:
 *   - loads local mock JSON (default), or
 *   - GETs ${VITE_API_URL}/paper/signal when that env is set (future FastAPI).
 *
 * TODO(api): wire sentiment, todaysBook, customer copy, and lifecycle.outcome from GET /paper/signal.
 * TODO(desk_intel): map packages/desk-intel MARKET_SIGNAL into sentiment later — not indicator names.
 * TODO(auth): attach a paper-user session header when auth lands.
 * TODO(signals): support a list of concurrent signals, not one-per-underlying.
 */

const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export function apiMode() {
  return API_URL ? "remote" : "mock";
}

export async function fetchPaperDesk() {
  const url = API_URL ? `${API_URL}/paper/signal` : "/mock/signal.json";
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Could not load paper signal (${res.status} from ${url})`);
  }
  return res.json();
}

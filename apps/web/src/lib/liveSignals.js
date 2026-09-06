/**
 * Paper live signals. Browser never talks to Dhan — only this API WebSocket.
 * /ws/signals?live=1 is server-side Dhan feed → BUY CE/PE/HOLD copy.
 */

const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function wsUrl() {
  if (!API_URL) return "";
  const u = new URL(API_URL);
  const proto = u.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${u.host}/ws/signals?live=1`;
}

export function subscribePaperSignals(onPayload) {
  const url = wsUrl();
  if (!url) {
    return () => {};
  }
  let closed = false;
  let socket;
  try {
    socket = new WebSocket(url);
  } catch {
    return () => {};
  }
  socket.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data && data.kind === "paper_signal") onPayload(data);
    } catch {
      /* ignore */
    }
  };
  return () => {
    closed = true;
    if (socket && socket.readyState <= 1) socket.close();
    void closed;
  };
}

/** Founder emergency controls API (apps/api /founder/controls). PAPER only; nothing here places orders. */

function url(path) {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return `${base}/founder/controls${path}`;
}

function newId() {
  if (globalThis.crypto?.randomUUID) return `ui-${globalThis.crypto.randomUUID()}`;
  return `ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

async function readError(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* not JSON */
  }
  const d = body?.detail;
  if (d && typeof d === "object" && !Array.isArray(d)) return { message: d.status_reason || d.reason || `HTTP ${res.status}`, ack: d };
  if (Array.isArray(d)) return { message: d.map((x) => `${(x.loc || []).slice(-1)[0]}: ${x.msg}`).join("; ") };
  return { message: d || `HTTP ${res.status}` };
}

export async function fetchControls({ signal } = {}) {
  const res = await fetch(`${url("")}?t=${Date.now()}`, { signal, cache: "no-store" });
  if (!res.ok) throw new Error((await readError(res)).message);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(url(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await readError(res);
    const e = new Error(err.message);
    e.ack = err.ack;
    e.status = res.status;
    throw e;
  }
  return res.json();
}

/** One command. A network failure is retried once with the same command_id (the API dedups it). */
export async function sendControl(path, body) {
  const payload = { command_id: newId(), ...body };
  try {
    return await post(`/${path}`, payload);
  } catch (err) {
    if (err.status) throw err;
    return post(`/${path}`, payload);
  }
}

export async function confirmToken(kind, tradeId) {
  const j = await post("/confirm", { kind, trade_id: tradeId || null });
  return j.confirm_token;
}

/** "09:15-09:30, 14:45-15:30" -> [{start, end}] (throws on a bad entry). */
export function parseWindows(text) {
  const parts = String(text || "")
    .split(/[,;\n]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return parts.map((p) => {
    const m = p.match(/^(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})$/);
    if (!m) throw new Error(`"${p}" is not HH:MM-HH:MM`);
    const pad = (h) => String(h).padStart(2, "0");
    return { start: `${pad(m[1])}:${m[2]}`, end: `${pad(m[3])}:${m[4]}` };
  });
}

export function windowsText(wins) {
  return (wins || []).map((w) => `${w.start}-${w.end}`).join(", ");
}

export function describeArgs(kind, args) {
  const a = args || {};
  switch (kind) {
    case "PAUSE":
      return a.minutes ? `${a.minutes} min` : "resume";
    case "BLOCK_WINDOWS":
      return windowsText(a.windows) || "clear all";
    case "CUT_LOSS":
    case "GO_T2":
      return a.trade_id;
    case "SET_LOTS":
      return a.lots == null ? "clear (engine default)" : `${a.lots} lots`;
    case "INDEX":
      return `${a.underlying} ${a.enabled ? "ON" : "OFF"}`;
    case "MIN_CAPITAL":
      return a.amount_inr == null ? "clear" : `₹${Number(a.amount_inr).toLocaleString("en-IN")}`;
    case "ADD_FUNDS":
      return `+₹${Number(a.amount_inr).toLocaleString("en-IN")}`;
    default:
      return "";
  }
}

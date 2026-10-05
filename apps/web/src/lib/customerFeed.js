/**
 * Customer `/` loader. Tries compact `/v2/customer/signals`, then
 * `/v2/snapshot?channels=signals:public`, then the safe mock feed (MOCK).
 *
 * Never: Dhan, founder token, founder channels, LLM.
 * Auth: Bearer VITE_CUSTOMER_JWT or localhost paper label `token=customer`.
 */

import { API_BASE } from "./feed.js";
import { CUSTOMER_CHANNEL, deskFromMock, deskFromV2Public, isCustomerV2Snapshot } from "./customerPortal.js";

function customerHeaders() {
  const jwt = String(import.meta.env.VITE_CUSTOMER_JWT || "").trim();
  if (!jwt) return {};
  return { Authorization: `Bearer ${jwt}` };
}

function authQuery() {
  const jwt = String(import.meta.env.VITE_CUSTOMER_JWT || "").trim();
  const qs = new URLSearchParams();
  // packages/auth: customer role only. Never token=founder.
  if (!jwt) qs.set("token", "customer");
  return qs;
}

function compactSignalsUrl() {
  const qs = authQuery();
  const base = API_BASE || "";
  const q = qs.toString();
  return `${base}/v2/customer/signals${q ? `?${q}` : ""}`;
}

function snapshotUrl() {
  const qs = authQuery();
  qs.set("channels", CUSTOMER_CHANNEL);
  const base = API_BASE || "";
  return `${base}/v2/snapshot?${qs}`;
}

const V2_BUDGET_MS = 450;

async function tryOne(url, signal, budgetMs) {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), budgetMs);
  const onAbort = () => ac.abort();
  signal?.addEventListener("abort", onAbort);
  try {
    const res = await fetch(url, {
      headers: customerHeaders(),
      cache: "no-store",
      signal: ac.signal,
    });
    if (!res.ok) return null;
    const body = await res.json();
    if (!isCustomerV2Snapshot(body)) return null;
    return deskFromV2Public(body);
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

async function trySignalsPublic(signal) {
  // Compact tail first (C5-05). Fall back to /v2/snapshot, then mock.
  return (
    (await tryOne(compactSignalsUrl(), signal, V2_BUDGET_MS)) ||
    (await tryOne(snapshotUrl(), signal, V2_BUDGET_MS))
  );
}

async function loadMock(signal) {
  const res = await fetch("/mock/signal.json", { cache: "no-store", signal });
  if (!res.ok) {
    throw new Error(`Could not load mock customer feed (${res.status})`);
  }
  return deskFromMock(await res.json());
}

export async function fetchCustomerDesk(signal) {
  const v2 = await trySignalsPublic(signal);
  if (v2) return v2;
  return loadMock(signal);
}

/**
 * Customer `/` loader. Tries V2 `signals:public` with a customer claim,
 * then falls back to the safe mock feed (labeled MOCK).
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

function snapshotUrl() {
  const jwt = String(import.meta.env.VITE_CUSTOMER_JWT || "").trim();
  const qs = new URLSearchParams({ channels: CUSTOMER_CHANNEL });
  // packages/auth: customer role only. Never token=founder.
  if (!jwt) qs.set("token", "customer");
  const base = API_BASE || "";
  return `${base}/v2/snapshot?${qs}`;
}

const V2_BUDGET_MS = 450;

async function trySignalsPublic(signal) {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), V2_BUDGET_MS);
  const onAbort = () => ac.abort();
  signal?.addEventListener("abort", onAbort);
  try {
    const res = await fetch(snapshotUrl(), {
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

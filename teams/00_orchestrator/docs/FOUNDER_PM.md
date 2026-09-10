# Founder PM canvas (`/pm`)

**Department:** D4  
**Boss:** 00 Project Manager  
**Layer:** `HYPOTHESIS` (spec) + **PARTIAL UI**. Route **`/pm`**. Polls `GET /founder/status` (no secrets). Start Vite + API when the founder asks.  
**Counsel:** Gemini+OpenAI **ALIGNED** — one site, founder tab separate from customer `/`. Scale review: [`COUNSEL_SCALE_2026-09-09.md`](COUNSEL_SCALE_2026-09-09.md).

The founder talks to **this boss only** during market hours. The PM pulls status from D1–D5 bosses. Chat is backup.

---

## What the page must show (plain words + color)

| Color | Meaning |
|-------|---------|
| Green | Service up / job finished / ticket feasible |
| Amber | Waiting, MOCK, `DATA_INSUFFICIENT`, paper-only |
| Red | Critical: key 401, 429 rate limit, Dhan pull fail, API rejects, expired token |
| Grey | Intentionally stopped (e.g. `paper_ops_STOPPED.flag`) |

Blocks:

1. **Next action** (one sentence).  
2. **Who is working** — department, agent/chair, task, idle vs active.  
3. **Services** — Vite, API, paper loop, nightly last run, RAG last rebuild.  
4. **Keys / vendors** — OpenAI, Gemini, Dhan, YouTube: present/missing/HTTP class only. **Never print secrets.**  
5. **Signals** — current WATCH / EARLY / CONFIRMED / IN-PROGRESS / HOLD / `DEALER_KILLED` (copy, not a fill).  
6. **Honesty** — gate unset; P/L MOCK; KEEP_ALL; no promote.
7. **Speed** — cached API latency, WebSocket heartbeat, payload age.
8. **Data/RAG freshness** — warehouse last write, RAG last rebuild, nightly last success.
9. **Live counsel** — OpenAI/Gemini ok/split/timeout, token budget used, last risk-review reason.

Customer ticket detail stays on `/`. Infra + next action stay on `/pm`.

---

## Inputs the PM must collect

| From | Ask |
|------|-----|
| D1 07 | What shipped, what is down, warehouse/RAG age |
| D2 Dean | What the faculty changed or blocked |
| D3 09 | Doc next-action + auditor last result |
| D5 05 | Live ticket + last dealer kill + mistake |
| 06 | Last backtest: FAIL / `DATA_INSUFFICIENT` / `BACKTEST_REQUIRED` |

---

## Minimum SLO cards

| Card | Green | Amber | Red |
|------|-------|-------|-----|
| API | health up, cached signal p95 under target | slow / mock only | down |
| Dhan | auth ok, chain fresh | fixture / delayed | 401 / 429 / pull fail |
| LLM counsel | keys ok or intentionally off | one provider down | both down during requested counsel |
| LLM token budget | under session cap | nearing cap | cap exhausted and counsel requested |
| RAG | rebuilt after latest docs | stale but usable | missing index |
| Nightly | latest report ready | not due | missed before pre-market |
| Portal | payload fresh | stale banner | build/API failure |

Targets live in [`PRODUCT_ARCHITECTURE_STANDARDS.md`](../../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md). If not measured, show `UNKNOWN`, not green.

---

## Not this page

Live order buttons. Win rates. Indicator soup. Restart instructions that fight `do not restart npm until asked`.

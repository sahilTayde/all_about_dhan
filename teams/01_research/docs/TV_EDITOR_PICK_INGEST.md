# TV Editor Pick ingest — next 1000 pines

**Team:** 01 research (librarian) → 04 names MIX → 06 queues.  
**Date:** 2026-09-14  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. No live orders. `win_rate=null`.  
**KEEP_ALL:** teacher `STRAT-001`–`014` never reused, never deleted. **New IDs = `MIX-TV-EP-NNN` only.** Never `STRAT-015+`.

Inventory (this snapshot): [`refernece_tradingview/editors_picks/`](../../../refernece_tradingview/editors_picks/). Schema: [`ingest_schema.json`](../../../refernece_tradingview/editors_picks/ingest_schema.json). MIX pointer: [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) §22.

---

## Drop-in factory (do not write 1000 essays)

```text
1. Point at a public TV URL (listing or /script/<slug>/).
2. Assign next MIX-TV-EP-NNN (zero-pad 3+). Never a STRAT id. Listing snapshot used 001–023; 024–025 are factory calibrators; **next listing pine is 026**.
3. Tag origin WEB-DERIVED + TV-EDITOR-PICK (or TV-COMMUNITY if not an Editors’ Pick).
4. Store row: title, author, url, license/visibility, long/short, asset guess, default TF, inputs (name+default).
5. Rule SUMMARY only. Do NOT commit Pine source.
6. Status flags: INGESTED → RULES_EXTRACTED (if public source) → PORT_PENDING → BACKTEST_QUEUED.
   After a scored run: TESTED_FAIL or TESTED_PARK. ALWAYS keep NEVER_DISCARD.
7. Append catalog.json + catalog.csv + one line on INDEX.md. Pointer in MIX_CATALOG. Stop.
```

Listing pagination: unfiltered `/scripts/editors-picks/page-N/` SSR works (~24 cards/page). `?script_type=strategies` SSR is **page-1 only**; `/page-N/?script_type=strategies` **repeats page 1** (JS). If WebFetch 409, use curl. Strategy Tester tables are **per-chart** → `DATA_INSUFFICIENT`.

---

## Naming

| Field | Rule |
|-------|------|
| `mix_id` | `MIX-TV-EP-001` … increment. Gap-free. |
| `ep_id` | `EP-NNN` same number (factory / 06 loader). |
| Origin | `WEB-DERIVED` + `TV-EDITOR-PICK` — never `DHAN-DERIVED` |
| Adapter | `stub` until a **public textbook** port exists. Do not paste Pine into Python. |
| Customer default | always `false`. `MIX-DEFAULT-BUY` unchanged. |

---

## 01 research-analyst checklist (ports that can actually be tested)

Every EP row starts as **spot/futures-on-TV**. Our book is **NIFTY / BANKNIFTY / SENSEX CE/PE buy**. Before 04/06 spend cycles:

1. **Underlying:** TV chart close ≠ OPTIDX premium. If the pine reads `close` on BTC/grains/ES, say so. Port must declare INDEX vs FUTIDX vs **OPTIDX premium**.
2. **Session:** TV exchange TZ ≠ `Asia/Kolkata`. Map or `DATA_INSUFFICIENT`. No fake NSE boxes.
3. **Expiry:** TV stocks/crypto have none. Index options: weekly/monthly from **contract master**, flatten **15:15 IST** unless a named MIX says otherwise (009). Do not invent Dhan expiry fields.
4. **Costs:** TV tester commission ≠ India brokerage+STT+slippage. 06 scores **after-cost**; unknown costs stay UNKNOWN — no promote.
5. **Long/short:** Many EP scripts are two-way or short-only (e.g. ag selling). Phase-1 UI is **buy CE/PE**. Short-underlying → HOLD or `MIX-SELL-*` park, not a buy ticket.
6. **Templates / CSV / 3Commas / Kelly / report generators:** keep the row; mark **infra / education**, not an entry recipe.
7. **Martingale / grid / pyramiding:** KEEP_ALL test row; flag path-dependent size as **not** customer default.
8. **Inputs:** copy names+defaults from public `input.*` only. Cap grid size. Do not dump 200-line Pine.
9. **Reports:** do not scrape a user’s Strategy Report as our edge. Quote TV marketing metrics as **unvalidated display**.
10. **Fail stays:** `TESTED_FAIL` is a result, not a delete.

---

## HANDOFF (01)

**Accepted:** 23 current Editors’ Picks **strategy** badges cataloged as `MIX-TV-EP-001`–`023`. 760 EP slugs classified (656 indicator / 50 library / 23 strategy). Open-source inputs extracted; Pine not stored.

**Rejected:** `STRAT-015+`. Deleting a pine because it is a template, grain, BTC, or FAIL. Pasting full Pine into git. Win-rate claims. Live orders. Relabeling TV EP as `DHAN-DERIVED`.

**UNKNOWN:** Historical EP strategies **removed** from the current Editors’ list; JS-only extra strategy pages (none linked in SSR); per-chart tester reports; NSE portability until 03/06 score OPTIDX+costs.

Next: 04 keeps MIX pointer; 06 may queue `BACKTEST_QUEUED` stubs; 09 notes ≠ pass.

# QUANT_SELF_REVIEW_LOOP — nightly / paper review of our own research

**Team:** 06_backtesting (owns gate + loop) · 02_phd_math (REVIEW) · 04_quant (hypothesis authors) · 05 (`desk_intel nightly`)  
**Status:** `HYPOTHESIS` / spec · **UNVALIDATED** · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Sibling law:** [`RETUNE_GATE.md`](RETUNE_GATE.md)  
**PhD KB:** [`book_kb/topics/parameter_fit_retune_gate.md`](../../02_phd_math/docs/book_kb/topics/parameter_fit_retune_gate.md)

Education ≠ advice. **No live orders.** This file is **not** a backtest and contains **no** P/L.

---

## Why this exists

Agents and paper jobs will re-read **our** MIX-FORM notes, ML-001 fits, TV-EP grids, and dual-tape ledgers. That reread is a **learning packet**. It must not silently become production knobs or a Dhan **Super Order**.

The loop is: **observe → propose → backtest (06) → 09 review → maybe paper**. Never: **observe → write params → live**.

---

## Loop (POST_MARKET + paper EOD)

1. **Ingest facts** — session kind (`NORMAL` / `NEWS_DAY` / `EXPIRY`), paper ledger, dual-tape flags, MIX-FORM / ML-001 artifacts on disk.  
2. **Self-review** — 02/04/06 comment: what broke (quote stale, FOLLOW-GAP, theta, unbound STRAT), what is `DATA_INSUFFICIENT`. Root cause + **one** backtestable change.  
3. **Emit** `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED`.  
4. **Stop.** 06 may later run an engine. Nightly does **not** run that engine as a promote.

Same rules as the paper session tuner (`tv-ep-paper-tune`): extra JSON under `data/recon/` is allowed; **MIX-DEFAULT-BUY production params are not**.

---

## Hard constants (every proposal)

| Field | Value |
|-------|--------|
| `kind` | `RETUNE_PROPOSAL` |
| `status` | `BACKTEST_REQUIRED` (nightly / paper review) |
| `keep_current_strategy` | `true` |
| `production_params_written` | **`false` always** in this loop |
| `tuned` | `false` |
| `backtest_results` | `null` (never invent) |
| `one_day_pnl_is_not_evidence` | `true` |
| `oos_non_event_required` | `true` |
| Live Super Order / `ExecutionClient` | **refused** — this loop must not call place/modify |

06 later statuses (`REJECTED`, `PROMOTE_CANDIDATE`) are **engine-owner** writes after a real OOS+`NORMAL` run — still not a live order, still 04+09 for any spec freeze.

---

## Will / will not

| This loop **will** | This loop **will not** |
|--------------------|------------------------|
| Re-read original `phd_book_kb` + recon JSON | Download books or treat notes as edge |
| Stamp REVIEW handoff language for 02 | Auto-apply Supertrend/MACD/MIX knobs |
| Keep STRAT-001–014 `BACKTEST_BOOK` | Delete teacher ids because a session failed |
| Point 06 at a **named** next test | Place or even **request** a live Super Order |
| Leave IV/greeks null when missing | Invent IV to finish a story |

---

## Who runs what

| Job | Command (existing) | Loop role |
|-----|-------------------|-----------|
| Nightly recon | `python -m desk_intel nightly` / `python -m jobs post-market` | Packet + `RETUNE_PROPOSAL` |
| Paper EOD | `agent_rag` `run_eod_recon` | Same gate fields |
| Paper tuner | `python -m backtest_engine tv-ep-paper-tune` | Local params file only |
| Docs | `python -m docs_auditor` | After HANDOFF / this spec |

---

## HANDOFF block (copy when the loop runs)

```text
From:     06 QUANT_SELF_REVIEW_LOOP
To:       02 REVIEW / 04 / 09
Status:   RETUNE_PROPOSAL BACKTEST_REQUIRED
production_params_written: false
live_super_order: refused
Accepted: <what the packet actually showed>
Rejected: production write; live Super Order; invented IV/greeks
UNKNOWN: <DATA_INSUFFICIENT>
```

---

## Paper EOD 2026-09-17 (LIVE SESSION board) — RETUNE_PROPOSAL

**Kind:** `RETUNE_PROPOSAL` · **status:** `BACKTEST_REQUIRED` · `keep_current_strategy: true` · `production_params_written: false` · `tuned: false` · `one_day_pnl_is_not_evidence: true` · **NO_PROMOTE**. Not a five-pass. Thursday may be SENSEX weekly — treat as **not NORMAL** until 05 tags session.

**Board (as_of 15:33 IST):** filled 175 · unique-ish ~88 (dealer ≈ logit clone) · W net 26 / L 149 · wr net 14.86% / gross 20.57% · net ₹−93745 · **SL-hits 153 / 175**. Open 0.

**Exit mix (raw closed):** `STOP` 153 · `TIME` 14 · `CANCEL_STRIKE_ROLL` 6 · `TARGET` 2. Unique: STOP 77 · TIME 7 · STRIKE_ROLL 3 · TARGET **1**.

**P/L by exit (raw, Groww+STT):** STOP −105582 · TIME +4776 · STRIKE_ROLL −1650 · TARGET +8712 (one SENSEX PE 235→309, cloned on two books).

**What passed:** PE unique wr ~22% vs CE ~5%. TIME exits were the working hold (12/14 TIME rows SUCCESS on the clone board). One TARGET runner proved the lock-shift idea. NIFTY unique wr ~29% less ugly than BN/SENSEX. SIDEWAYS skip 6 (NEW only).

**What failed:** Almost every fill died on **STOP**. Median risk ~₹4.75 vs median target ~₹25 — R:R on paper is fantasy vs 10s MTM. 51/77 unique STOPs had risk under ₹8; 34 had under ₹4. 60 raw tickets had stop ≥ entry (BE trail then noise). BANKNIFTY wr ~3.6% (1/28 per book). SENSEX worst ₹. Logit cloned dealer (Δ only −1248). GREEKS/XR/TV/ML-001 **0 fills**. After 15:30 last-3 prints frozen ER=1.0 fake TREND.

**SL vs target:** Board is an SL factory, not a target book. Target almost never prints because (1) 9-bar TIME wins first on the few that go green, (2) trailed/BE stop is inside 1m premium chop so STOP fires before TARGET, (3) CE fills against a PE ITM-bin.

**One backtestable change (do not write production params):** Hold the **original** path stop until premium is ≥ BE + trail band; do not ratchet SL to a 3–5₹ pocket. Score **unique** tickets only. Ablate: NEW only on last-3 impulse **or** ITM-bin side match (no CE when bin is PE). Optional: skip BANKNIFTY NEW unless last-3 impulse. OOS+`NORMAL` required. KEEP_ALL STRAT-001–014.

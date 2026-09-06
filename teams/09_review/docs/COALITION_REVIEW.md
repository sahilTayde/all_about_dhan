# COALITION_REVIEW — red-team notes (not a five-pass)

**Team:** 09_review  
**Date:** 2026-09-03  
**Status:** `NOTES_ONLY` (partial packets) · **not** a pass  
**Gate:** `RESEARCH_READY_FOR_PROGRAMMING` = **not issued**  
**Ticket:** [`TASK_TRANSCRIPT_COALITION.md`](../../00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md)  
**Algo shape (do not code yet):** [`ALGO_HANDOFF.md`](../../04_quant/docs/ALGO_HANDOFF.md)

This is the coalition red-team sheet. It does **not** replace [`docs/REVIEW.md`](../../../docs/REVIEW.md). A later five-pass still has to run. Mock UI, nightly `BACKTEST_REQUIRED`, and English packets are **not** a programming license.

Education ≠ endorsement. **No win rates.**

---

## Packet status (disk check 2026-09-03, synthesizer pass)

| Packet | Expected path | On disk? | Review |
|--------|---------------|----------|--------|
| OPTIONS_INDEX | `teams/01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md` | **Yes** | `NOTES_ONLY` — see template |
| TA_STRUCTURE | `teams/01_research/docs/handoffs/TA_STRUCTURE_PACKET.md` | **Yes** | `NOTES_ONLY` — see template |
| TA math companion | `teams/02_phd_math/docs/TA_FROM_TRANSCRIPTS.md` | **Yes** | `NOTES_ONLY` — layers hold |
| EQUITY_ETF | `teams/01_research/docs/handoffs/EQUITY_ETF_PACKET.md` | **Yes** | `NOTES_ONLY` — firewall holds; scanners + G31/dEv claim tables 2026-09-03 |
| Equity backlog | `teams/04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md` | **Yes** | `NOTES_ONLY` — EQ-*/ETF-*/SO-* slots; not STRAT-015+ |

All three extract packets are on disk. This sheet is still **notes only**. Algo agents still do **not** code.

---

## Red-team questions (ask on every packet)

Answer **yes / no / UNKNOWN** with a path + line pointer. **Yes** (failure) → packet stays `FAILED REVIEW` or is sent back. Any yes blocks `RESEARCH_READY_FOR_PROGRAMMING`.

### Hallucinated Dhan quotes

1. Is every quote (or close paraphrase) backed by `video_id` + timestamp on an **English** file under `data/transcripts/normalized_en/` (or a cited Hindi `SOURCE_FACT` that the English file confirms)?  
2. Did we invent a Dhan recommendation, ScanX “edge,” or HQ REST field that is not in [`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md)?  
3. Did we silently “clean” an `[UNCERTAIN_TRANSCRIPT]` number into a confident param?  
4. Did we treat a disabled `EXTERNAL_RESEARCH` channel as `@DhanHQ`?

Maps to [`REVIEW.md`](../../../docs/REVIEW.md) PASS 1 and red-team 1–2, 18–19.

### Stock concept on index

5. Did we apply cash-stock VWAP, stock scanner, or NIFTY-100 equity rules to **NIFTY/BANKNIFTY/SENSEX options** without tagging `PROJECT-DERIVED`?  
6. Did equity/ETF facts leak into `STRAT-001`–`014` or into `market: [NIFTY, BANKNIFTY, SENSEX]`?  
7. Did we assume American exercise / stock delivery on **European cash-settled** index options?  
8. Did we reuse NSE chain/lot/expiry code for **SENSEX (BSE)**?

Maps to red-team 4–5, 7; market notes [`TRANSCRIPT_MARKET_NOTES.md`](../../03_phd_market/docs/TRANSCRIPT_MARKET_NOTES.md).

### Lagging TA as entry

9. Is Supertrend / MACD / `RSI_14` written as the **entry**, rather than confirm-or-kill after impulse + chain + news ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md))?  
10. Does the packet claim a 1-minute EARLY lead is measurable or a fill?  
11. On `NEWS_DAY` / `EXPIRY`, does it still “wait for the cross” instead of default **no-trade**?  
12. Does it assume an HQ **series** API for Supertrend / session VWAP / EMA9?

Maps to red-team 6, 14; persona [`PERSONA.md`](../../00_orchestrator/docs/PERSONA.md); missed-PE [`MISSED_TRADE_POSTMORTEM.md`](MISSED_TRADE_POSTMORTEM.md).

### Always-on (do not skip)

13. Future information / unclosed bar as a fill?  
14. Current lot size used historically?  
15. Costs, bid/ask, or touch fills ignored?  
16. Fourteen IDs counted as fourteen independent edges?  
17. Nightly or transcript hint treated as a live retune (violates [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md))?  
18. Can another researcher **not** reproduce the quote from disk?

---

## Review template (fill when packets exist)

Copy a block per packet. Leave unused blocks as `WAITING_FOR_PACKETS`.

```text
Packet:     OPTIONS_INDEX | TA_STRUCTURE | EQUITY_ETF
Path:
Reviewed:   YYYY-MM-DD
Reviewer:   09_review
Layer check: SOURCE_FACT / VALIDATION / HYPOTHESIS still separate?  yes/no
Origin tags: DHAN-DERIVED vs PROJECT-DERIVED honest?  yes/no
Q1–Q4 quotes:     pass / fail / UNKNOWN
Q5–Q8 stock→index: pass / fail / UNKNOWN
Q9–Q12 lagging TA: pass / fail / UNKNOWN
Q13–Q18 other:     pass / fail / UNKNOWN
Gaps:
-
Verdict:    WAITING_FOR_PACKETS | NOTES_ONLY | SENT_BACK | FAILED REVIEW
            (never RESEARCH_READY_FOR_PROGRAMMING from this sheet)
```

### OPTIONS_INDEX

```text
Packet:     OPTIONS_INDEX
Path:       teams/01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md
            + HAUSZx-hYdY.en.md, _exmJYgFwFA.md, DzT_681GThA.md, 8h9SYvQWKMA.md
Reviewed:   2026-09-03
Reviewer:   09_review (synthesizer)
Layer check: SOURCE_FACT primary; Layer C pointers labelled UNVALIDATED?  yes
Origin tags: HAUS NIFTY-100 called not index-only; EXM 5% OTM sell is stock example;
             DzT demo = Reliance; volume-delta ≠ Greek delta?  yes
Q1–Q4 quotes:     pass (video_id + ts; 93/7 and screen numbers UNCERTAIN; no invented REST)
Q5–Q8 stock→index: pass on labeling; fail-risk if 04 transfers EXM-C12/C13 to NIFTY
                   without PROJECT-DERIVED
Q9–Q12 lagging TA: n/a as entry recipe here (TA packet owns that); HAUS dual-TF is
                   filter+entry on child TF — same caveat as TA sheet
Q13–Q18 other:     lots/expiry not frozen; OF history DATA_INSUFFICIENT; no win rates
Verdict:    NOTES_ONLY
```

**OPTIONS gaps (content):**

- English is `youtube_translate` of Hindi — do not freeze HAUS Thursday list, lot 65/75, or pvm “555 to 6” delta.  
- `conviction = delta` (HAUS-EN-17) stays opinion; 02 already `unsupported` as identity.  
- Highest-OI = wall (EXM-C09) is a **heuristic**, not a theorem.  
- STRAT-010 / DzT+YUXJv: HQ footprint history still `DATA_INSUFFICIENT`.  
- 8h9 Pine webhook → order: `VERIFY BEFORE IMPLEMENTATION`, not a strategy.  
- Selling corpus (`_exm`, 6el9, gA5 bull put) stays **WAITING** — Phase-1 buy-first.

### TA_STRUCTURE

```text
Packet:     TA_STRUCTURE (+ TA_FROM_TRANSCRIPTS)
Path:       teams/01_research/docs/handoffs/TA_STRUCTURE_PACKET.md
            teams/02_phd_math/docs/TA_FROM_TRANSCRIPTS.md
Reviewed:   2026-09-03
Reviewer:   09_review (synthesizer)
Layer check: SOURCE_FACT / VALIDATION / HYPOTHESIS still separate?  yes
Origin tags: DHAN-DERIVED vs PROJECT-DERIVED honest?  yes (stock scanners tagged STOCK;
             HAUS dual-TF called NIFTY-100, not index-only; transfer table says do not
             use that universe as Phase-1)
Q1–Q4 quotes:     pass (video_id + ts; [UNCERTAIN_TRANSCRIPT] kept; no invented REST)
Q5–Q8 stock→index: pass on labeling; fail-risk if 04 copies scanner bands onto NIFTY
Q9–Q12 lagging TA: pass with a caveat — packet states 5m ST/MACD confirm-or-kill is
                   *desk spec*, not a quote; HAUS uses child-TF MACD as *entry filter*
                   (different HYPOTHESIS; 02 recorded the split)
Q13–Q18 other:     pass on honesty; no win rates; 3m/2m flagged as resample
Verdict:    NOTES_ONLY
```

**TA gaps (content):**

- Super Scalper EMA lengths still `UNKNOWN` — do not invent.  
- MACD ×3 vs ×4 vs 24/52 are **three recipes**, not one Dhan MACD.  
- Opening skip windows disagree (09:45 / 10:00 / ORB-to-10:00) — search set, not a freeze.  
- `_byuht` Supertrend “7,3” vs repeated 10,3 — `SOURCE_UNCERTAIN`.  
- HAUS MACD-as-entry vs staging confirm-or-kill: if 04 merges them silently, **Q9 fails**.  
- OPTIONS_INDEX missing → strike/ITM mapping on pvm/HAUS stays incomplete.

### EQUITY_ETF

```text
Packet:     EQUITY_ETF
Path:       teams/01_research/docs/handoffs/EQUITY_ETF_PACKET.md
Reviewed:   2026-09-03
Reviewer:   09_review (synthesizer)
Layer check: SOURCE_FACT only (no fake VALIDATION)?  yes
Origin tags: ScanX = product, not backtest?  yes
Q1–Q4 quotes:     pass on EN files cited; STOCK_ONLY/ETF titles correctly
                   DATA_INSUFFICIENT (no EN companion)
Q5–Q8 stock→index: pass — firewall + skip list; must not bleed into STRAT-001–014
Q9–Q12 lagging TA: n/a as index entry; scanners *are* lagging stacks on cash —
                   keep them off the index book
Q13–Q18 other:     spoken “90% chance” / “0.6% after costs” flagged as not a study
Verdict:    NOTES_ONLY
```

**Equity gaps (content):**

- Backlog [`EQUITY_ETF_BACKLOG.md`](../../04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md) on disk (`EQ-*` / `ETF-*` / `SO-*` including `EQ-014` / `SO-003`, `UNVALIDATED`). Still not a spec freeze.  
- All 9 catalog `STOCK_ONLY` + stock-options series + ETF strategy titles: **no English transcript**.  
- `2YBmiyVmNNw`: still `DATA_INSUFFICIENT` for a recipe. G31 / dEv now have claim tables — **still UNVALIDATED**.  
- Supertrend params on Alpha / IMB: `UNKNOWN`.  
- ScanX “unusual volume” token: `UNKNOWN`.

---

## Gap list (synthesizer)

| ID | Gap | Owner |
|----|-----|-------|
| C-00 | OPTIONS_INDEX landed — still `youtube_translate` numbers; expiry/lot dated | 02 / 03 |
| C-01 | Equity EN second pass landed (`EQ-014` / `SO-003`) — still `UNVALIDATED`; no EN on catalog STOCK_ONLY/ETF titles | 01 / 04 |
| C-02 | 14 STRATs remain DRAFT; coalition must not add IDs | 04 |
| C-03 | Official lot + F&O 15:40 circulars still not in repo | 03 |
| C-04 | No backtest engine — any numeric “proof” would be invented | 06 — blocked |
| C-05 | Do not issue `RESEARCH_READY_FOR_PROGRAMMING` from this coalition | 09 |
| C-06 | Super Scalper EMA lengths + MACD scale conflict + ORB window set | 01 / 02 / 04 — do not freeze |
| C-07 | HAUS MACD-as-entry vs 5m confirm-or-kill must stay two hypotheses | 04 |
| C-08 | ENGINE_MIX freeze ([`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md)) + 09 notes ([`ENGINE_MIX_REVIEW.md`](ENGINE_MIX_REVIEW.md)) — still `NOTES_ONLY`, not a five-pass; Q4/Q8/Q12/Q19/Q20 FAILED; 007∩009 AND and 003 3m-vs-5m not merged | 04 / 09 |

---

## Verdict

**Notes only. Not a pass.** OPTIONS + TA + equity packets are honest enough to keep as `SOURCE_FACT`. 14 index STRATs stay `UNVALIDATED`. ENGINE_MIX is a named `HYPOTHESIS` club — **not** `RESEARCH_READY_FOR_PROGRAMMING` ([`ENGINE_MIX_REVIEW.md`](ENGINE_MIX_REVIEW.md)). Algo agents may study the **YAML schema** in `ALGO_HANDOFF.md`. They may not implement. Prior scratch list still stands: [`RESEARCH_REVIEW_NOTES.md`](RESEARCH_REVIEW_NOTES.md).

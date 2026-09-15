# Counsel — train 02/04 like pro quant (no pirate books)

**Date:** 2026-09-14  
**Job:** one joint `complete(role=review)` (`trading_agents_india.counsel`) — same package as `counsel-job` / `tv-ep-counsel`.  
**Models:** Gemini `gemini-3.5-flash-lite` + OpenAI `gpt-5.4-nano`  
**Together:** `SPLIT` (wording differs; policy **ALIGNED** on no-PDF + `BACKTEST_REQUIRED`)  
**Layer:** `VALIDATION` (counsel) + desk policy  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Policy:** PAPER. **No live orders.** No win-rate claims. **No book PDF download or ingest.**

Founder asked agents to invent NIFTY/SENSEX option formulas like a pro quant, constantly self-review, and said downloading copyrighted books is fine. **Desk rejects pirate ingest.** Copyright still stands. Training uses existing FTS exam notes + tape + MIX-FORM + ML-001.

Related: [`COUNSEL_LLM.md`](COUNSEL_LLM.md) · standing prompt [`PRO_QUANT_AGENT_PROMPT.md`](../../02_phd_math/docs/PRO_QUANT_AGENT_PROMPT.md) · KB [`book_kb/INDEX.md`](../../02_phd_math/docs/book_kb/INDEX.md) · [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) · nightly loop [`QUANT_SELF_REVIEW_LOOP.md`](../../06_backtesting/docs/QUANT_SELF_REVIEW_LOOP.md)

---

## What we asked (one shot)

(a) Train desk agents without pirate books.  
(b) A great standing prompt for 02/04.  
(c) Autonomous learning that does **not** violate `RETUNE_GATE`, live-order ban, or **zero blocking LLM** on the 30s path.

---

## Panel

Verbatim from the one `complete` shot (keys present). Do not polish into a second counsel.

### Gemini (`ok`)

```text
(a) Use allowed `phd_book_kb` corpus (teams/02_phd_math/docs/book_kb/) via local FTS query; cite validation tags/publisher URLs from workspace.yaml. Run quantitative drills on historical Index LTP/1m + ATM CE/PE dual-tape CSVs. FTS queries target volatility surfaces, jump-diffusion, and local volatility PDEs without PDF ingest.
(b) Spine: "You are a pro quant quant inventing option formulas as HYPOTHESIS. Reference FTS `phd_book_kb` by doc_id. Operate CE/PE BUY-first on DhanHQ (PAPER only). Enforce dual-tape INDEX LTP/1m & ATM checks; HOLD new CE/PE on `PREMIUM_DIVERGENCE` / `MIX-FORM-FOLLOW-GAP`. ML-001 runs KMeans k=4 + IsolationForest post-1m close (never write prod params). All MIX-* are `BACKTEST_REQUIRED`/`NO_PROMOTE`."
(c) Agents self-review via nightly `RETUNE_GATE` emitting `RETUNE_PROPOSAL` (`status=BACKTEST_REQUIRED`, `keep_current_strategy=true`), promoting only after 06 OOS+NORMAL. Never write `workspace.yaml`, candidates, or indicators. Async counsel runs pre/post via `trading_agents_india.counsel` without blocking the ~30s/45s fast path. No live orders.

ACCEPT_WITH_CAVEATS
DATA_INSUFFICIENT: Live fill mechanics and exact ML-001 schema fields are unspecified.
```

Desk note: “jump-diffusion / local-vol PDE” is **not** implementable (no HQ IV series). Keep as `HYPOTHESIS` / `DATA_INSUFFICIENT`.

### OpenAI (`ok`, truncated)

`gpt-5.4-nano` hit counsel `max_completion_tokens` (400) mid-(c). Do not invent the missing close.

```text
a) Train desk agents using **only** `teams/02_phd_math/docs/book_kb/` (tagged `kind=phd_book_kb`) as the **allowed corpus**; do **not** download/ingest PDFs—use **FTS searches** over the KB plus derived “note-to-formula” drills (turn cited text → candidate option formula marked **HYPOTHESIS**). Use FTS queries like: `("dual-tape" OR "INDEX LTP" OR "ATM CE/PE")`, `("MIX-FORM" AND ("FOLLOW-GAP" OR "HOLD"))`, `("ML-001" OR "KMeans k=4" OR "IsolationForest")`, `("RETUNE_GATE" OR "OOS" OR "NORMAL")`.

b) Standing prompt spine (must load): **“PAPER ONLY, DhanHQ-only, CE/PE BUY-first signal company; no live orders; keep STRAT-001–014 as BACKTEST_BOOK; new clubs are MIX-* only; dual-tape=INDEX LTP/1m + ATM CE/PE; PREMIUM_DIVERGENCE / MIX-FORM-FOLLOW-GAP ⇒ HOLD new CE/PE; MIX-FORM-* are HYPOTHESIS + BACKTEST_REQUIRED + NO_PROMOTE; ML-001=KMeans k=4 + IsolationForest overlay after 1m close; never writes production MIX params; RETUNE_GATE nightly BACKTEST_REQUIRED, keep_current_strategy=true; promote only after 06 OOS+NORMAL; counselor is async pre/post only and must not block ~30s/45s path; invent option formulas only as HYPOTHESIS.”**

c) Autonomous learning/self-review/retune: run a **nightly** loop emitting `RETUNE_PROPOSAL status=BACKTEST_REQUIRED` while **never** writing `workspace.yaml/candidates/indicators; keep_current_strategy
```

---

## 00 verdict (what we accepted / rejected)

| Item | Call |
|------|------|
| Pirate / web PDF ingest | **Rejected** (both models + copyright HARD) |
| FTS `phd_book_kb` + dual-tape drills + note→formula homework | **Accepted** as the training corpus (plus existing SOURCE_FACT / HQ book) |
| Standing prompt file | **Accepted** — [`PRO_QUANT_AGENT_PROMPT.md`](../../02_phd_math/docs/PRO_QUANT_AGENT_PROMPT.md) |
| Nightly auto-write of MIX/params | **Rejected** — `keep_current_strategy: true` |
| Blocking LLM on 30s / dual-tape | **Rejected** |
| Async counsel on compact state | **Accepted** (pre/post / material-change jobs only) |
| Invented formulas | **Accepted** only as `HYPOTHESIS` + `BACKTEST_REQUIRED` |
| Jump-diffusion / local-vol PDE as coded edge | **Rejected** (`DATA_INSUFFICIENT` without HQ IV) |
| Win rates / live orders / `STRAT-015+` | **Rejected** |

**UNKNOWN:** walk-forward of MIX-FORM / ML-001 on the next `NORMAL` session; OpenAI (c) cut; live fills (Gemini).

---

## Nightly self-review (how it must work)

This is **autonomous learning** that stays legal with the gates. Same constants as [`QUANT_SELF_REVIEW_LOOP.md`](../../06_backtesting/docs/QUANT_SELF_REVIEW_LOOP.md).

1. **Market hours (fast path):** `dual-tape` + dealer rules + `desk_ml score` after 1m close. **Zero LLM.** FOLLOW-GAP / `PREMIUM_DIVERGENCE` → HOLD new CE/PE. No orders.
2. **POST_MARKET:** `python -m desk_intel nightly` (or `python -m jobs post-market`). Stamps `session_kind`. Writes recon JSON + `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED` and `keep_current_strategy: true`. Hands `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md` as **REVIEW**, not apply.
3. **02 self-review (offline):** load [`PRO_QUANT_AGENT_PROMPT.md`](../../02_phd_math/docs/PRO_QUANT_AGENT_PROMPT.md). FTS-query `phd_book_kb` (`python -m agent_rag query "follow-gap residual"`). Compare dual-tape / MIX-FORM residuals / ML-001 overlay vs the packet. Cite `doc_id`, not chapters. Root cause + **one** backtestable change. Optional **async** counsel job (`REVIEW_NOTES` / `COUNSEL_NEXT`) on a compact facts pack — never on the 30s loop.
4. **04:** if a new expression is needed, name `MIX-FORM-*` or another `MIX-*` (not `STRAT-015+`). Layer = `HYPOTHESIS`. Catalog stub `customer_default: false`.
5. **06:** OOS + `NORMAL` only. Event days stay in `ANALOG_MEMORY`, not the promote score.
6. **09 / Docs Auditor:** last on nightly. No promote from notes.

Re-run this counsel: one `complete(role=review)` when keys exist. If both keys missing, write `DATA_INSUFFICIENT` and keep the prompt file.

---

## HANDOFF

```text
From:     teams/00_orchestrator + counsel panel
To:       02 / 04 / 06 / 09 / founder
Date:     2026-09-14
Status:   REVIEW notes / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Joint counsel together=SPLIT; Gemini ACCEPT_WITH_CAVEATS;
  OpenAI aligned on no-PDF + FTS drills then truncated. Train on FTS
  notes + tape + MIX-FORM + ML-001. Standing prompt for 02/04. Nightly
  REVIEW + BACKTEST_REQUIRED only (QUANT_SELF_REVIEW_LOOP).
Rejected: Book PDF download/ingest; jump-diffusion as coded edge;
  auto-retune; blocking LLM on 30s; live orders; win rates; STRAT-015+.
UNKNOWN: OpenAI (c) truncated; next NORMAL OOS; live fills.
```

# TOPIC_COVERAGE — what 00 may treat as KNOWN vs DATA_INSUFFICIENT

**Team:** 01 research-analyst (Hat C) · 00 reads after 01 finishes  
**Layer:** coverage stamps on `SOURCE_FACT` / `VALIDATION` notes — **not** a promote  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** none. **No** production params. **No** 30s LLM.

**Stamps:** `KNOWN` = notes + named desk hook; 00 may emit `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`. `PARTIAL` = sampled / identity only — hook only, no new formula. `DI` = `DATA_INSUFFICIENT` — 00 must not invent.

**Desk hooks (only these families in this matrix):** `MIX-FORM-*` · dual-tape (`PREMIUM_DIVERGENCE` / `MIX-FORM-FOLLOW-GAP`) · `ML-001` (KMeans+IsolationForest overlay) · `ML-002` (OU on **residual** / MRR metaphor — not IV).

Books = sibling `book_reads/NOTE_*` + matching `book_kb` exam note. YouTube = `@DhanHQ` packets (librarian). Do **not** paste PDF text.

**As of:** 2026-09-15 — founder **DISCARDED** unreadable titles (image / missing / full-book claims). Readable notes stay. Re-stamp when a sibling note lands, then 00 rebuilds RAG.

---

## Matrix (topic × book × status × desk hook)

| Topic | Book / note | Status | Desk hook |
|-------|-------------|--------|-----------|
| Many small tested expressions; one production gate | **101** `ssrn-2701346` via `NOTE_finding_alphas` + `book_kb/01_*` | `PARTIAL` | Existing `MIX-FORM-*` only. No hero MIX. |
| Wiley *Finding Alphas* image PDF | `Finding Alphas_ Quantitative Trading Strategies.pdf` | **`DISCARDED`** | Do not treat as VALIDATION. Keep 101 notes. |
| KEEP_ALL inventory; descriptive catalog ≠ P/L | Kakushadze **151** `NOTE_ssrn_3247865` + `book_kb/02_*` | `KNOWN` | Catalog stay. No Super-Order 151. New ideas = `MIX-*` not `STRAT-015+`. |
| Model is a metaphor; fails at the boundary | Derman **slides** `NOTE_oneil_derman` + `book_kb/03_*` | `KNOWN` | Dual-tape FOLLOW-GAP **HOLD**. Fit-on-one-window ≠ promote (`ML-001` / `ML-002` / MIX-FORM \(k\)). |
| Full *Models.Behaving.Badly* monograph | not on disk | **`DISCARDED`** | Slides stay. Do not claim the book. |
| Macro process / regime; not 1m entry | Gliner **extract** `NOTE_L0002559656` + `book_kb/04_*` | `PARTIAL` | NEWS_DAY **HOLD**. Ch.3–12 stay `DI`. |
| Full Gliner monograph | not on disk | **`DISCARDED`** | Extract + slides-adjacent notes stay. |
| Strike-local risk; one vol number is a lie | **Orrell** (`ssrn-4205729` / `3512481`) via `NOTE_volatility_smile` | `PARTIAL` | `MIX-FORM-STRADDLE-RET` crude proxy **not** IV. HQ IV series `DI`. |
| Wiley *The Volatility Smile* image (Bookey) | `123456.pdf` | **`DISCARDED`** | Keep Orrell notes. Do not invent Wiley body. |
| Object is the tape (stale, impact, next-bar) | Bouchaud prior preview `NOTE_preview_1108639064` + `book_kb/06_*` | `PARTIAL` (prior note only) | Dual-tape + next-bar / 1% RT **proxy**. Not NSE L2. |
| Full TQP / missing preview PDF | TQP file absent | **`DISCARDED`** | Keep prior oral preview note. Not a full-book claim. |
| Leakage / purged CV; unsupervised first | **AFML excerpt** `NOTE_ssrn_3104847` + GIL2476 + `book_kb/07_*` | `PARTIAL` | `ML-001` overlay HOLD. CPCV **not coded** → robust-OOS claim `DI`. |
| Index vs premium residual | `book_kb/topics/price_change_premium_residual` + smile/Derman notes | `KNOWN` | `MIX-FORM-BETA-RESID`, `MIX-FORM-DIVERGE-Z`, `MIX-FORM-FOLLOW-GAP`, `MIX-FORM-STRADDLE-RET`. Same-session INDEX∩CE∩PE. |
| Dual-tape premium vs spot | Derman + smile + [`MARKET_HOURS_DUAL_TAPE.md`](../../00_orchestrator/docs/MARKET_HOURS_DUAL_TAPE.md) | `KNOWN` (rule) | `PREMIUM_DIVERGENCE` / FOLLOW-GAP → **HOLD** new CE/PE. Paper gather only. |
| Local pattern overlay | AFML + [`ML_001_LOCAL_PATTERN.md`](../../04_quant/docs/ML_001_LOCAL_PATTERN.md) | `PARTIAL` | `ML-001` KMeans+IsolationForest. `DIVERGE` ≠ BUY. Shadow / `NO_PROMOTE`. |
| OU / mean-reversion on residual (MRR metaphor) | Smile + Derman Badly desk map | `DI` | `ML-002` = OU on **ε**, not implied vol. Half-life is **not** a vega trade. No coded production OU. |
| Theta / weekly death on long premium | `book_kb/topics/theta_decay` | `KNOWN` (oral) | Calendar haircut; 15:15 flatten. Not an entry alpha. |
| HQ greeks / IV series | `book_kb/topics/pricing_hq_greeks` + `vega_iv_realized` | `DI` | Null HQ greeks ≠ 0. Do not invent Δ / IV as `SOURCE_FACT`. |
| Dhan product / spoken rules | YouTube `@DhanHQ` packets | `PARTIAL` | Librarian `SOURCE_FACT` only. CAS spoken acronym `DI`. English bind wins. |
| SCORE_SAMPLE / analog memory depth | AFML + `EVENT_MEMORY` | `DI` | NEWS_DAY / EXPIRY out of score. Memory store still thin. |
| Live option-fill history | — | `DI` | Do not invent fills / lots. |

---

## How 00 uses this sheet

1. After 01 finishes notes or this file: run [`RESEARCH_BOSS_LOOP.md`](../../00_orchestrator/docs/RESEARCH_BOSS_LOOP.md) (00 transition).
2. Queue `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` **only** for `KNOWN` (and `PARTIAL` named hooks).
3. Rows stamped `DI` stay `DATA_INSUFFICIENT` on the founder ticket. KEEP_ALL STRAT-001–014 untouched.
4. Never write production params. Never block dual-tape / 30s.

```text
HANDOFF
From:     01 research-analyst TOPIC_COVERAGE
To:       00
Accepted: Matrix stamps; KEEP readable 151 / AFML excerpt / Gliner extract /
  Derman slides / 101 / Orrell. MIX-FORM / dual-tape / ML-001 / ML-002 hooks.
Rejected / DISCARDED: Wiley smile image; Finding Alphas image; missing TQP;
  full Badly monograph; full Gliner. ML-002 as coded edge; STRAT-015+.
UNKNOWN / DI: HQ IV/Δ; CPCV; analog store; fills; ML-002 implementation.
```

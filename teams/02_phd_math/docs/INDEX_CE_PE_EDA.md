# INDEX vs CE vs PE EDA — MIX-FORM-* (PROJECT-DERIVED)

**Team:** 02 PhD math + 01 research  
**Date:** 2026-09-14 (Ganesh Chaturthi — **historical cache only**, no Dhan fetch)  
**Layer:** `VALIDATION` (measured prints) + `HYPOTHESIS` (named formulas)  
**Status:** `UNVALIDATED` / **NO_PROMOTE**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Origin:** `PROJECT-DERIVED` — not DHAN-DERIVED, not a neural net  
**Sibling:** ML-001 KMeans/IsolationForest in `packages/desk-ml` — **not rewritten here**

Canonical path: this file under `teams/02_phd_math/docs/`. Founder alias: [`teams/02_math/docs/INDEX_CE_PE_EDA.md`](../../02_math/docs/INDEX_CE_PE_EDA.md).

Token policy: [`docs/TOKEN_ML_STRATEGY.md`](../../../docs/TOKEN_ML_STRATEGY.md) — local ML overlay is allowed; no LLM on the blocking fast path; no “AI win rate.” MIX-DUAL remains the 1m confluence **filter** ([`MIX-DUAL-INDEX-MASTER.md`](../../04_quant/docs/candidates/MIX-DUAL-INDEX-MASTER.md)), not these formulas.

---

## Why we were not using ML (honest)

ML was **delayed**, not banned.

| Reason | What it meant |
|--------|----------------|
| Gate | Not `RESEARCH_READY_FOR_PROGRAMMING`. 09 five-pass has not passed. |
| No greeks as day-1 identity | HQ rollingoption / our day-1 dealer does not supply a trusted delta/IV series to train on. Inventing IV/delta is forbidden. |
| Day-1 dealer | Deterministic INDEX Δ vs ATM CE Δ vs ATM PE Δ (`desk_divergence`) so HOLD is auditable without a fit. |
| Token budget | LLM is counsel, not KB reread and not live alpha. First models in TOKEN_ML_STRATEGY are **local** (rules → logit/tree → later GBM). |
| Labels | Thin SCORE_SAMPLE / no OOS+`NORMAL` promote path. Thin labels → `DATA_INSUFFICIENT`, not a fitted story. |

We start ML **now** as a **local overlay** (ML-001 + these MIX-FORM features). Overlay may assist HOLD / regime / residual flags. It must not publish a customer ticket, must not override hard stops, and must not quote a win rate.

---

## Data (SOURCE_FACT — on disk)

IST timestamps from Dhan chart epoch (`Asia/Kolkata`). Inner join on **exact** `ts`.

| Series | Path / id | Bars | First IST | Last IST |
|--------|-----------|-----:|-----------|----------|
| NIFTY INDEX 1m | `INDEX_IDX_I_13_1_*` sid **13** | 524154 | 2021-09-06 06:14 | **2026-09-03 14:19** |
| 23500 PE | OPTIDX **47298** | 7185 | 2026-08-18 11:23 | 2026-09-11 15:39 |
| 23400 PE | OPTIDX **47294** | 6606 | 2026-08-19 14:01 | 2026-09-11 15:39 |
| 23350 CE | OPTIDX **47291** | 2578 | 2026-09-03 11:08 | 2026-09-11 15:39 |
| 23500 CE (inferred) | OPTIDX **47297** (between 47296=23450 PE and 47298=23500 PE; not in `itm_strike_universe.json` CE list) | 4614 | 2026-08-27 09:15 | 2026-09-11 15:39 |
| NIFTY ATM tape | `data/recon/premium_tape/NIFTY_ATM_1m_2026-09-09..11.json` | 1146 CE + 1146 PE | 2026-09-09 09:15 | 2026-09-11 15:30 |

**Holiday / gap:** INDEX cache does **not** cover 2026-09-09..11. ATM premium_tape ∩ INDEX = **0** bars → `DATA_INSUFFICIENT` for INDEX–ATM-CE–ATM-PE triples on the tape days.

NIFTY weekly Tuesdays used for regime slice (03: `FROM_CONTRACT`, not frozen): 2026-08-18, 08-25, **09-01**, 09-08, 09-15. Overlap with INDEX+OPTIDX is mainly **Mon 08-31 / Tue 09-01**.

No IV, no delta, no invented 23500 PE (47298 is present).

Replay: `python -m trading_agents_india index-ce-pe-eda` (cache read only).

---

## Measured tables (VALIDATION)

Returns: \(r_t = (P_t - P_{t-1}) / |P_{t-1}|\).  
OLS (no intercept): \(k = \sum r^{\mathrm{opt}} r^{\mathrm{idx}} / \sum (r^{\mathrm{idx}})^2\).  
Divergence rate (PE): share of **index-down** minutes with \(r^{\mathrm{PE}} \le 0\).  
Divergence rate (CE): share of **index-up** minutes with \(r^{\mathrm{CE}} \le 0\).  
These are **contemporaneous print stats**, not P/L and **not a win rate**.

### Primary book: INDEX ∩ 23500 CE (47297) ∩ 23500 PE (47298)

| Metric | Value |
|--------|------:|
| Aligned minutes | 2174 |
| Return bars | 2173 |
| Window (IST) | 2026-08-27 09:15 → 2026-09-03 14:19 |
| \(\mathrm{corr}(r^{\mathrm{idx}}, r^{\mathrm{CE}})\) | **+0.551** |
| \(\mathrm{corr}(r^{\mathrm{idx}}, r^{\mathrm{PE}})\) | **−0.823** |
| \(k_{\mathrm{CE}}\) MIX-FORM-BETA | **+16.68** |
| \(k_{\mathrm{PE}}\) MIX-FORM-BETA | **−73.66** |
| mean PE residual | +0.00014 |
| std PE residual | 0.0164 |
| Index-down minutes | 1024 |
| Index-up minutes | 1000 |
| PE diverge count / rate \| idx down | 305 / **0.298** |
| PE follow rate \| idx down (\(r^{\mathrm{PE}}>10^{-4}\)) | **0.702** |
| CE diverge count / rate \| idx up | 845 / **0.845** |
| CE follow rate \| idx up | **0.153** |
| mean MIX-FORM-STRADDLE-RET | +0.00046 / minute |
| mean \|MIX-FORM-DIVERGE-Z\| (PE, w=30) | 0.749 |

**Pattern:** PE 1m percent returns track the index **inversely and tightly**. CE 1m percent returns are only **moderately** pro-index; on this strike/window most index-up minutes do **not** print a positive CE return (theta + quote stickiness + percent-of-premium scale). Same-strike PE is the cleaner dual-tape “follow” leg in **return space**. This does **not** say “buy PE.”

### Regime slices (same primary book)

| Slice | n | corr idx–CE | corr idx–PE | \(k_{\mathrm{PE}}\) | PE div \| idx↓ | CE div \| idx↑ |
|-------|--:|------------:|------------:|--------------------:|---------------:|---------------:|
| Morning 09:15–10:30 IST | 443 | +0.723 | **−0.922** | −82.48 | 0.271 | 0.773 |
| Expiry-week Mon/Tue (09-01 vintage) | 745 | +0.554 | −0.790 | −62.63 | 0.295 | 0.906 |
| Full overlap | 2173 | +0.551 | −0.823 | −73.66 | 0.298 | 0.845 |

Morning PE coupling is **tighter** (corr −0.922). Expiry-week Mon/Tue CE-follow is **worse** (CE diverge 0.906). Sample is one expiry vintage (week of 2026-09-01), not a SCORE_SAMPLE.

### 23350 CE (47291) vs PE — do not over-read

INDEX overlap is only **2026-09-03 11:08–14:19** (191 return bars). On every aligned minute CE close is **frozen at 670.85** (later 47291 prints move, but **after** INDEX cache ends). \(\mathrm{corr}(r^{\mathrm{idx}}, r^{\mathrm{CE}})\) is **undefined** (zero CE variance). PE still moves: vs 23500 PE corr **−0.880**, PE diverge rate **0.077**; vs 23400 PE corr **−0.847**, PE diverge rate **0.154**. Treat the CE side as `DATA_INSUFFICIENT` for this window.

### ATM premium_tape without INDEX

| Metric | Value |
|--------|------:|
| CE+PE return pairs | 1145 |
| \(\mathrm{corr}(r^{\mathrm{CE}}, r^{\mathrm{PE}})\) | **−0.958** |
| ∩ INDEX | **0** → `DATA_INSUFFICIENT` |

Tape CE and PE are almost perfect inverse of each other on 2026-09-09..11. Cannot score MIX-FORM-BETA vs index until INDEX 1m is fetched through those sessions (post-holiday).

---

## Named formulas (HYPOTHESIS, PROJECT-DERIVED)

Implemented in `packages/trading_agents_india/src/trading_agents_india/index_ce_pe_formulas.py`. Deterministic functions of aligned bars. Feed ML-001 as extra columns; do not replace `desk_divergence`.

### MIX-FORM-BETA-RESID

\[
k = \frac{\sum_t r^{\mathrm{opt}}_t r^{\mathrm{idx}}_t}{\sum_t (r^{\mathrm{idx}}_t)^2}, \qquad
\varepsilon_t = r^{\mathrm{opt}}_t - k\, r^{\mathrm{idx}}_t
\]

Use separate \(k_{\mathrm{CE}}\), \(k_{\mathrm{PE}}\) estimated on the same aligned sample (or a trailing window later). No intercept (spot-beta in return space). **Not** delta.

### MIX-FORM-DIVERGE-Z

\[
z_t = \frac{\varepsilon_t - \bar\varepsilon_{t,w}}{s_{t,w}}, \quad w=30
\]

Trailing mean/std of \(\varepsilon\) including \(t\). Constant residual → `None` (not 0). Large \(|z|\) = premium move not explained by the fitted \(k\).

### MIX-FORM-STRADDLE-RET

\[
s_t = r^{\mathrm{CE}}_t + r^{\mathrm{PE}}_t
\]

Vol-expansion **proxy**. Positive when both premiums rise together. **Not** implied volatility, **not** vega.

### MIX-FORM-FOLLOW-GAP

For \(\epsilon_{\mathrm{idx}}=10^{-5}\), \(\epsilon_{\mathrm{opt}}=10^{-4}\):

- PE diverge: \(r^{\mathrm{idx}} < -\epsilon_{\mathrm{idx}}\) and \(r^{\mathrm{PE}} \le 0\)
- PE follow: \(r^{\mathrm{idx}} < -\epsilon_{\mathrm{idx}}\) and \(r^{\mathrm{PE}} > \epsilon_{\mathrm{opt}}\)
- CE diverge: \(r^{\mathrm{idx}} > \epsilon_{\mathrm{idx}}\) and \(r^{\mathrm{CE}} \le 0\)
- CE follow: \(r^{\mathrm{idx}} > \epsilon_{\mathrm{idx}}\) and \(r^{\mathrm{CE}} > \epsilon_{\mathrm{opt}}\)

Matches dual-tape dealer language without placing an order.

---

## HANDOFF

```text
From:     teams/02_phd_math + 01_research
To:       00 / 04 / 05 / 06 / 09 / ML-001 sibling
Date:     2026-09-14
Status:   VALIDATION numbers + HYPOTHESIS formulas / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted:
- Honest delay of ML: gate + no greeks + deterministic day-1 dealer; ML allowed as local overlay (TOKEN_ML_STRATEGY).
- Cache-only EDA on holiday. Primary book = INDEX 13 ∩ 23500 CE 47297 ∩ 23500 PE 47298 (2173 1m returns).
- Named MIX-FORM-BETA-RESID, MIX-FORM-DIVERGE-Z, MIX-FORM-STRADDLE-RET, MIX-FORM-FOLLOW-GAP.
- PE inverse coupling is the strong measured pattern (corr −0.823 full / −0.922 morning).
- ATM tape CE vs PE corr −0.958 without index.
- KEEP_ALL STRAT-001–014. MIX-DUAL unchanged. packages/desk-ml not rewritten.

Rejected:
- Promoting any rate as a win rate or customer default.
- Invented IV/delta/greeks; fake 23500 PE; live Dhan on a holiday.
- Treating 23350 CE vs INDEX k_ce=0 as a structural CE result (frozen 670.85 print).
- Neural net / LLM as alpha; blocking LLM on the fast path.
- Collapsing MIX-DUAL into these formulas.

UNKNOWN / DATA_INSUFFICIENT:
- INDEX 1m after 2026-09-03 14:19 (blocks ATM-tape triples).
- 47297 strike label is inferred from sid adjacency (23500 CE) — 03 confirm.
- OOS+NORMAL; costs; fills; other expiries; BANKNIFTY/SENSEX.
- Whether CE non-follow is theta vs stale OPTIDX quotes vs moneyness.
```

**Next backtestable change (06):** (1) extend INDEX 1m through 2026-09-11 and recompute ATM-tape MIX-FORM on true triples; (2) walk-forward \(k\) on trailing 30/60 minutes vs full-sample \(k\); (3) after 2026-09-15 expiry, new sid pair — do not freeze 47297/47298.

**04:** optional catalog stub `MIX-FORM-*` (`customer_default: false`, metrics null). Not STRAT-015+.

**Counsel:** openai/gemini **CLI not installed** this run → 02-review skipped (TOKEN_ML_STRATEGY: no blocking LLM). Local math stands.

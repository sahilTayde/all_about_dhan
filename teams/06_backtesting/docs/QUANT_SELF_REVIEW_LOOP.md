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

---

## Paper overlay replay 2026-09-17 (write=false) — RETUNE_PROPOSAL

**Kind:** `RETUNE_PROPOSAL` · **status:** `BACKTEST_REQUIRED` · `keep_current_strategy: true` · `production_params_written: false` · `one_day_pnl_is_not_evidence: true` · **NO_PROMOTE**. Dual-tape JSONL replay only — **did not rewrite** live `ML_PAPER_DASHBOARD.md`.

| | Live board (15:51 IST) | Overlay replay |
|--|--|--|
| Filled | 175 (~88 unique) | 83 (43 unique-ish) |
| STOP | 153 (unique 77) | 25 (unique 13) |
| TARGET | 2 | 0 (T1 confirm; 6 tickets `target_step=1`) |
| TIME | 14 | 4 |
| Other | STRIKE_ROLL 6 | COVER_LONG_UNWIND 54 (unique 28) |
| wr net | 14.86% | 74.7% (not a claim) |
| Net ₹ | −93745 | −15018 |
| STOP P/L | ~−105k | −44069 |
| COVER P/L | — | +27447 (54/54 net-green) |

**SL saved (this tape, not OOS):** raw STOP **128** fewer (153−25); unique STOP **64** fewer (77−13). Many former chop SLs became COVER_LONG_UNWIND scratches/small wins. Fat leftover STOPs (SENSEX) still dominate.

**Loop next (do not write params):** COVER only if `target_step≥1` **or** SIDEWAYS+BE (not every 10s OI dip at BE). Optional BANKNIFTY impulse-only. OOS+`NORMAL`. KEEP_ALL.

---

## Paper overlay loop 2026-09-17 — 3 vs 5 is the wrong question (NO_PROMOTE)

**Kind:** `RETUNE_PROPOSAL` · `BACKTEST_REQUIRED` · `keep_current_strategy: true` · `production_params_written: false` · **NO_PROMOTE**.

Do **not** pick overlay A wr 74.7% vs B wr 52.8%. Both still net red (A −15018, B ~−43k to −50k this recode). Founder tape: spike 3–4 candles → sideways → later volume / cover / sweep.

| 17 Sep write=false | filled | wr net | unique net ₹ |
|--|--|--|--|
| Live board | 175 | 14.9% | −93745 |
| A last3-blind + COVER-at-BE (prior) | 83 | 74.7% | −15018 |
| Confirm-only (B recode) | 44 | 31.8% | −49888 |
| Pause-continue + BN wait | 34 | 23.5% | −44977 |
| Pause-continue + BN+SENSEX wait (**ship**) | 14 | 28.6% | −18104 |
| NIFTY-only ablation | 10 | 40.0% | −9738 |

14 Sep dual-tape timestamps ≠ IST date (DI). 15 Sep 337 ticks, 0 ITM wings. 16 Sep 1 STOP −1116. Counsel ALIGNED ACCEPT_WITH_CAVEATS. OOS+`NORMAL` still required.

---

## 17 Sep overlays — strict TARGET, trail SL (NO_PROMOTE)

**Kind:** `RETUNE_PROPOSAL` · `BACKTEST_REQUIRED` · `apply_target_shift: false` · `production_params_written: false`. write=false dual-tape. All closed `target_step=0`. Live board not overwritten.

| Overlay | filled | wr net | unique net ₹ | exits |
|--|--|--|--|--|
| Live board | 175 | 14.9% | −93745 | STOP 153 · TARGET 2 |
| Pause + BN/SX wait (**ship**) | 12 | 33.3% | −13037 | STOP 4 · TARGET 2 · TIME 2 · FLATTEN 4 |
| Confirm last-3 + BN/SX wait | 24 | 41.7% | −9972 | STOP 10 · TARGET 8 · TIME 2 · FLATTEN 4 |
| Pause or confirm, all names | 44 | 31.8% | −31371 | STOP 26 · TARGET 12 · TIME 2 · FLATTEN 4 |
| NIFTY-only pause (ablation) | 8 | 50.0% | −4671 | STOP 2 · TARGET 2 · TIME 2 · FLATTEN 2 |

Lock-shift parked until founder unparks. Trail SL unchanged.

---

## 17 Sep — NIFTY vs SENSEX premium-point engine (NO_PROMOTE)

Counsel Gemini+OpenAI `ALIGNED` `ACCEPT_WITH_CAVEATS`. BANKNIFTY skipped. Internally **premium points** (ATR + fib 0.382/0.618, R:R 1.2–2.5). Display still ₹.

| Overlay | filled | wr net | unique net ₹ | note |
|--|--|--|--|--|
| Live (3 names) | 175 | 14.9% | −93745 | same ₹ SL/target |
| SENSEX every bin + ATR | 33 | 24% | −56792 | SENSEX 21/25 STOP |
| NIFTY pause + SENSEX pause | 24 | 41.7% | −13206 | SENSEX TARGET 6 |
| **Ship: NIFTY pause + SENSEX last-3/cover, split ATR** | 24 | 50% | **+2696** | NIFTY STOP2/TARGET2; SENSEX STOP8/TARGET8. One day. |

NIFTY med stop ~16.5pt / target ~27pt. SENSEX med stop ~25pt / target ~36pt. **NO_PROMOTE.** OOS+`NORMAL` still required.

---

## 17 Sep live vs old overlays vs point-engine (NO_PROMOTE)

Same dual-tape 2026-09-17. `write=false`. Groww+STT net. Unique books. **One day ≠ promote.**

### Board vs older overlays (shared ₹ SL/target, 3 names)

| | Filled | wr net | Unique net ₹ | NIFTY ₹ | BN ₹ | SENSEX ₹ | Exits |
|--|--|--|--|--|--|--|--|
| **Live board** | 175 | 14.9% | **−93745** | −15192 | −33347 | −45205 | STOP 153 · TARGET 2 · TIME 14 |
| A last-3 blind + COVER-every-BE | 83 | 74.7% | −15018 | — | — | — | STOP 25 · COVER 54 |
| B last-3 confirm (shared ₹) | 44 | ~32% | ~−43k to −50k | — | — | — | more STOP, fewer COVER |
| Strict T + pause + BN/SX wait (shared ₹) | 12 | 33.3% | −13037 | — | — | — | STOP 4 · TARGET 2 |
| Strict T + confirm + BN/SX wait (shared ₹) | 24 | 41.7% | −9972 | — | — | — | STOP 10 · TARGET 8 |

### Point-engine (ATR+fib, strict T, current code)

| Overlay | Names | Filled | wr | Unique net ₹ | NIFTY | SENSEX | BN | What it is |
|--|--|--|--|--|--|--|--|--|
| **Now (ship)** | N+SX | 24 | 50% | **+2697** | −4671 (8: STOP2 TARGET2 TIME2 FLAT2) | **+7368** (16: STOP8 TARGET8) | skip | NIFTY pause; SENSEX last-3/cover; wide SX stop |
| Both pause | N+SX | 24 | 41.7% | −13206 | −4671 | −8535 (STOP10 TARGET6) | skip | Same pause on SENSEX — **hurts SENSEX** |
| Both confirm last-3 | N+SX | 24 | 50% | +2697 | −4671 | +7368 | skip | = ship on this tape (NIFTY pause≡confirm) |
| SENSEX every ITM bin | N+SX | 33 | 24% | −56792 | −4671 | **−52121** (STOP21 TARGET4) | skip | Spray SENSEX |
| NIFTY only pause | N | 8 | 50% | −4671 | −4671 | — | — | Pause vs confirm **identical** |
| NIFTY only confirm | N | 8 | 50% | −4671 | −4671 | — | — | Same |
| SENSEX only last-3/cover | SX | 16 | 50% | **+7368** | — | +7368 | — | **Suits SENSEX this day** |
| SENSEX only pause | SX | 16 | 37.5% | −8535 | — | −8535 | — | Pause does **not** suit SENSEX |
| Ship + T2 lock-shift | N+SX | 28 | 21% | −54276 | −10374 | −43902 | skip | **Do not unpark T2** |
| Add BN freely | 3 | 34 | 41% | −10442 | −4671 | +7368 | **−13139** (10 fills) | BN still red |
| Add BN wait-continuation | 3 | 26 | 46% | −2498 | −4671 | +7368 | −5194 (2 fills, both FLATTEN) | BN still a drag |

**Fit this tape:** SENSEX wants last-3/cover + wide ATR stop, not pause and not every-bin. NIFTY wants the tighter ATR book; pause vs confirm did not change 17 Sep. BANKNIFTY still loses. T2 chase kills both.

---

## 17 Sep NIFTY-only permutations (full tape, epoch off) — RETUNE_PROPOSAL

Founder will **not** trade NIFTY and SENSEX together. Combined unique +2696 was SENSEX +7368 vs NIFTY −4671 (epoch window). **Full tape** NIFTY unique, write=false, Groww+STT, UNIQUE books. **One day ≠ promote.** `production_params_written: false`.

| Overlay | n | wr net | Unique net ₹ | Keep? |
|--|--|--|--|--|
| CE+PE (both wings) | 15 | 26.7% | **−10172** | no — CE bleed |
| PE spray (no strength) | 25 | 52% | −7497 | no |
| PE + strength | 20 | 50% | **−3395** | yes vs both/spray |
| PE + strength + 14:15 cutoff | 12 | 50% | −1059 | yes, small |
| PE + strength + 14:00 / max5 | 10 | 60% | **+739** | yes, small green |
| **PE + strength + max4 / 13:30** | 8 | 75% | **+3299** | **tomorrow ship = max4, not 13:30 clock** |
| skip PE after first PE STOP | 2 | 0% | −1375 | no — kills TARGET |
| OpenAI session-lean after 10:30 + strength + max4 | 9 | 66.7% | −1185 | no vs PE-only (CE still printed) |
| OpenAI two-STOP halt, both wings | 9 | 66.7% | −1678 | no vs PE+max4 |

**18 Sep PAPER (founder):** skip BANKNIFTY + SENSEX. NIFTY `allow_sides=CE+PE`, `nifty_need_strength=true`, `nifty_align_impulse=true`, `nifty_max_filled_per_book=4`, `nifty_skip_ce_after_stop=true`, `apply_target_shift=false`. Dual-tape paper-scalp. **NO_PROMOTE.**

Schema + 17 vs 18 topic table: [`BACKTEST_REPLAY_TAPE.md`](BACKTEST_REPLAY_TAPE.md). INDEX 1m miss → carry last LTP. Each OPEN has `justification`.

---

## Paper overlay 2026-09-18 — CANCEL_STALL (NO_PROMOTE)

**Kind:** `RETUNE_PROPOSAL` · `BACKTEST_REQUIRED` · `production_params_written: false` · **NO_PROMOTE**.

Live 23250 CE 12:13 IST: entry 149.7, target 169.27, path SL 136.65, **max 157.7**, last ~144 by 13:37. Index 12h ER **0.043** / 13h **0.055** (range 18–28 pts). 15m classifier said TREND via `itm_bin` at ER 0.03–0.06. Soft CANCEL_GREEKS/STRIKE sat above path SL so 9m TIME never ran.

| Day | INDEX hour ER (cash) | Unique write=false net (this recode) | Note |
|--|--|--|--|
| 17 Sep 13h | **0.346** (range 90 pts) | −2519 (TARGET PE 153→182 **kept**) | Trend half-day |
| 18 Sep 12–13h | 0.043 / 0.055 | −6952 (STALL PE scratch +231; 9m PE TIME winner not repeated) | Chop |

Do **not** pick this overlay from one-day ₹. Grid: `STALL_HIGH_STALE_SEC`, fade vs 9m TIME on PE 12:01. OOS+`NORMAL`. KEEP_ALL.

---

## Paper overlay 2026-09-18 — FIX-FIRST profit book (NO_PROMOTE)

**Kind:** `RETUNE_PROPOSAL` · `BACKTEST_REQUIRED` · `production_params_written: false` · **NO_PROMOTE**.

Chop uses INDEX ER < 0.35 (not itm_bin TREND). Counsel ALIGNED AWC. Dual-tape left running.

| Day | INDEX 1m (jsonl) | MIX-DEFAULT-BUY write=false (this recode) |
|--|--|--|
| 17 Sep | from ~12h; 13h ER 0.305 range 78 max_1m 17 | TARGET CE SUCCESS + STALL; PE still UNWIND on this slice |
| 18 Sep | 12h ER 0.043 max_1m 10; 14h ER 0.492 | 3× STALL green, 1× chop UNWIND; tgt 149.7→159.7 |

70% day wr is founder bar after costs, not this board. Lots 30–40 need more capital than ₹1.425L/book. OOS+`NORMAL`. KEEP_ALL.

**Signal desk (2026-09-19):** same drill now emits `signal_desk` — dealer vs logit clone vs XR vs observe. Next recodes are **side quality**, not STALL/hold. 17/18: logit cloned dealer; XR was the only green fill book on 18 (n=4, not a default). **NO_PROMOTE.**

**Standing drill:** `python -m desk_ml fix-first` / pre-market **and** post-market hook. Day cards in `data/recon/fix_first_progress.json` (history kept). Skill = TARGET + STALL booking in chop; TREND same-wing ER≥0.35 holds retracement (prior-day). Fill kind = open ER; exit kind stamped too. Hour kind drives booking; itm_bin TREND ignored. 18 Sep TRENDING-at-open STALL is a watch ticket — **do not recode hold** until that path is reviewed with more sessions. Signal generation is a different desk. Do not recode booking mid-chat without founder confirm. Live n_open=0 is usually max-4 after recast, not a new ML-001 deny.


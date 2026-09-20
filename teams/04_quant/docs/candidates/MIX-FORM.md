# MIX-FORM-* — INDEX vs CE vs PE formula family (KEEP_ALL)

**Team:** 04 pointer · 02 VALIDATION · **Status:** `HYPOTHESIS` features / `UNVALIDATED` / **NO_PROMOTE**  
**Origin:** `PROJECT-DERIVED`. Feed **ML-001 / ML-002**. Not a customer ticket. **Not** `STRAT-015+`.  
**Catalog:** [`MIX_CATALOG.md`](../MIX_CATALOG.md) §24. **Math:** [`INDEX_CE_PE_EDA.md`](../../../02_phd_math/docs/INDEX_CE_PE_EDA.md).

| ID | Role |
|----|------|
| `MIX-FORM-BETA-RESID` | Residual of ATM premium vs index move |
| `MIX-FORM-DIVERGE-Z` | z of CE/PE divergence |
| `MIX-FORM-STRADDLE-RET` | ATM CE+PE straddle 1m return |
| `MIX-FORM-FOLLOW-GAP` | **Observer family (KEEP).** Formula: index lean not confirmed by **ITM** premium. Room = observer only. |
| `MIX-FORM-FOLLOWS` | **Analyst vote (KEEP).** Last-tick **ATM** INDEX vs CE/PE FOLLOWS (`judge_tick`). Vote source `follows`. **Not** desk. **Not** observer. **Not** the fill price. |

Do not delete because a window is `DATA_INSUFFICIENT`. IsolationForest / OU labels stay HOLD, not BUY.

---

## Locked SOD (do not redesign unless founder asks)

Rooms stay. Plugin later **in the named hook only**.

**FAST** (zero blocking LLM; ALLOW may fire async `allow-review`):

1. **Analyst room** (independent packets, not capital): MIX-FORM-FOLLOWS (`follows`), MIX-ML-LOGIT, MIX-ML-LOGIT-XR, MIX-ML-GREEKS, ML-001/002/ML-1 silent unless they already have a side (no KMeans CE/PE), MIX-TV-EP-024 lab, STRAT-001–014 KEEP_ALL (silent DI does not vote).
2. Boss **`picker_majority`** only (8-7 / soup / INDEX 1m against = HOLD). Not a fill.
3. Observer **`FOLLOW_GAP_ITM_1M`** only — ALLOW / VETO / PASS on the **picker wing**.
4. Desk **`MIX-DEFAULT-BUY`** — one working ticket, **ITM LTP** fill + overlay SL/T1. Lab never OPEN. `resolve_fill_intents` is `--sod-off` only.

**REVIEW:** desk `overlay_to_boss`; optional ML overlay / async LLM (`allow-review` / `exit-review` / `risk-review` / `partial-book-review`); boss wait/trail/cut. LLM does not invent CE/PE and does not wait the open.

LAB books **vote as analysts**. SOD capital is one MIX-DEFAULT-BUY fill. Spoken CE/PE is logged MATCH / DISSENT / SPOKEN_PICKER_HOLD / SILENT even when picker HOLD, observer VETO, or desk ignores (`model_signals` on `ML_PAPER_DASHBOARD`). `--sod-off` is pytest A/B of `resolve_fill_intents` only — not the Monday path.

`last_step` trace: `follows` → `picker` → `observer` → `desk`.

### Founder plugin map (change later without moving rooms)

| Want | Change only |
|------|-------------|
| New analyst / STRAT vote | `picker.collect_analyst_votes` / `extra` votes. KEEP_ALL. No `STRAT-015+`. |
| Majority rule | `picker_majority` only |
| Confirm / kill premium | Observer `FOLLOW_GAP_ITM_1M` only |
| Fill price / SL / T1 / stall | Desk booking overlay only |
| After-fill / ALLOW advice | `overlay_to_boss` / `llm_review` (`allow-review` async, not a block) |
| Track analysts vs picker | `picker.track_model_signals` (incl. STRAT spoken) → dashboard `model_signals`. Still one desk fill. |

**NO_PROMOTE.** Gate **not** `RESEARCH_READY_FOR_PROGRAMMING`.

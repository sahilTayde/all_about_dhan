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

**FAST** (zero blocking LLM; LLM never on ALLOW):

1. Analysts vote: **MIX-FORM-FOLLOWS**, logit, XR, greeks, STRAT-001–014 KEEP_ALL (silent DI does not vote), ML-001/002 silent HOLD.
2. Boss **`picker_majority`** only (8-7 / soup / INDEX 1m against = HOLD).
3. Observer **`FOLLOW_GAP_ITM_1M`** only — ALLOW / VETO / PASS on closed 1m INDEX vs same-strike **ITM**.
4. Desk **`MIX-DEFAULT-BUY`** — one working ticket, **ITM LTP** fill + overlay SL/T1. Missing ITM → `DATA_INSUFFICIENT` / skip NEW. Do not fill ATM as if ITM.

**REVIEW:** desk `overlay_to_boss`; optional ML overlay / async LLM (`exit-review` / `risk-review` / `partial-book-review`); boss wait/trail/cut.

LAB books (`MIX-ML-LOGIT` / XR / greeks) observe-or-skip (`SOD_LAB_OBSERVE`). `--sod-off` is pytest A/B of the old parallel FILL engine only — not the Monday path.

`last_step` trace: `follows` → `picker` → `observer` → `desk`.

### Founder plugin map (change later without moving rooms)

| Want | Change only |
|------|-------------|
| New analyst / STRAT vote | `picker.collect_analyst_votes` / `extra` votes. KEEP_ALL. No `STRAT-015+`. |
| Majority rule | `picker_majority` only |
| Confirm / kill premium | Observer `FOLLOW_GAP_ITM_1M` only |
| Fill price / SL / T1 / stall | Desk booking overlay only |
| After-fill advice | `overlay_to_boss` / `llm_review` (not the open path) |

**NO_PROMOTE.** Gate **not** `RESEARCH_READY_FOR_PROGRAMMING`.

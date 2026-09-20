# MIX-FORM-* — INDEX vs CE vs PE formula family (KEEP_ALL)

**Team:** 04 pointer · 02 VALIDATION · **Status:** `HYPOTHESIS` features / `UNVALIDATED` / **NO_PROMOTE**  
**Origin:** `PROJECT-DERIVED`. Feed **ML-001 / ML-002**. Not a customer ticket. **Not** `STRAT-015+`.  
**Catalog:** [`MIX_CATALOG.md`](../MIX_CATALOG.md) §24. **Math:** [`INDEX_CE_PE_EDA.md`](../../../02_phd_math/docs/INDEX_CE_PE_EDA.md).

| ID | Role |
|----|------|
| `MIX-FORM-BETA-RESID` | Residual of ATM premium vs index move |
| `MIX-FORM-DIVERGE-Z` | z of CE/PE divergence |
| `MIX-FORM-STRADDLE-RET` | ATM CE+PE straddle 1m return |
| `MIX-FORM-FOLLOW-GAP` | **Observer family (KEEP).** Formula: index lean not confirmed by premium. |

**SOD (rooms, PAPER, not ML family):** fast path = analysts **vote** (STRAT-001–014 KEEP_ALL + dealer/logit/XR/greeks; ML-001/002 silent HOLD) → boss **`picker_majority`** (8-7 or soup = HOLD; INDEX 1m against = HOLD) → **one** observer review on that wing (`FOLLOW_GAP_ITM_1M`) → desk books **one** working ticket (`sod_one_ticket`). VETO = do not send to desk. PASS = ATM/missing ITM/strike roll/no 1m — do not assume. LAB fill books observe-or-skip. LLM counsel is review-path only (exit/risk/partial-book), never on ALLOW/open. Booking overlay unchanged. **NO_PROMOTE.** Flag A/B: `sod_one_ticket` / `picker_majority` vs OLD parallel `FILL_ELIGIBLE`.

Do not delete because a window is `DATA_INSUFFICIENT`. IsolationForest / OU labels stay HOLD, not BUY.

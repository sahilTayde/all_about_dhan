# SL/TP math VALIDATION notes

**Team:** 02_phd_math  
**Date:** 2026-09-06  
**Layer:** `VALIDATION`  
**Cites:** [`SL_TP_CLASSIC_METHODS.md`](../../01_research/docs/SL_TP_CLASSIC_METHODS.md), [`SL_TP_EXTERNAL_HARVEST.md`](../../01_research/docs/SL_TP_EXTERNAL_HARVEST.md)

| Recipe | Verdict | Notes |
|--------|---------|-------|
| ATR(14)×k from entry + R=2 target | **supported** (computable) | Wilder ATR already in `indicators._wilder_atr`. Grid k; do not freeze from one IS run. |
| Chandelier (22,3) trail | **supported** | Needs highest-high-since-entry ratchet in sim. |
| STRAT-003 ST flip exit | **partially_supported** | ST line computable; spoken “103” WEAK. Exit ≠ fixed points. |
| STRAT-002 20–30% premium | **supported** on OPTIDX LTP; **unsupported** on INDEX proxy alone | |
| IQCapital GEX walls as NIFTY stops | **UNSUPPORTED / DATA_INSUFFICIENT** | No NIFTY dealer-GEX series in workspace. |
| Fixed `STOP_PTS` 30/60/100 | **unsupported** as strategy | Desk placeholder only. |

```text
HANDOFF From:02 To:04/06 Accepted: ATR+R2 well-defined. Rejected: silent STOP_PTS as math. UNKNOWN: GEX India.
```

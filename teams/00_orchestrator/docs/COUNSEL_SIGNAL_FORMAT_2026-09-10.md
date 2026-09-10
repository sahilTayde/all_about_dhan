# Counsel loops — DESK_SIGNAL_JSON v1 (2026-09-10)

**Panel:** Gemini flash-lite + OpenAI nano via `trading_agents_india.counsel.complete_panel`.
**Subject:** turn the founder's Gemini session format ([`GEMINI_SIGNAL_LEARNING.md`](../../05_analysis/docs/gemini_signal/GEMINI_SIGNAL_LEARNING.md)) into a desk paper-signal JSON contract.
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. Counsel reviewed a schema; it generated **no** market signal.
Raw round outputs: `data/recon/COUNSEL_SIGNAL_FORMAT_r{1..4}_*.json` (gitignored recon).

| Round | Question | Together | Kept from it |
|---|---|---|---|
| 1 | Critique draft schema/mapping | **ALIGNED** AGREE_WITH_CAVEATS ×2 | lifecycle `signal_id`+`supersedes_signal_id`; `EXPIRED` status; `supertrend` field; option `iv`/`oi_change` nulls; `premium_ohlc_present`; ISO-8601 +05:30 timestamps; trend enum; evidence-alignment note in `compliance` |
| 2 | Invalidation pass (attack the spec) | ONE_ONLY (Gemini HTTP 0) | OpenAI precedence ordering: veto ⇒ NO_TRADE/VETOED first; BUY_* needs non-empty invalidation + future validity else downgrade to WAIT + `DOWNGRADED_MISSING_INVALIDATION`; WAIT ⇒ WATCHING |
| 3 | Final confirm + deletions | ONE_ONLY (Gemini HTTP 503) | confidence ⇒ null under a data-quality floor; biggest honesty risk named: implying actionable premium/levels when premium tape is not persisted (⇒ BUY_* also gated on `premium_ohlc_present`) |
| 4 | Arbitrate deletions (order_flow / technical_confirmation) | **ALIGNED** AGREE_WITH_CAVEATS ×2 | KEEP `order_flow {status: UNAVAILABLE}` (skill §28 honesty artifact, no fake delta fields); KEEP `technical_confirmation` but as enums ABOVE/BELOW/RECLAIM/REJECT/FLAT/UNKNOWN + optional level; execution-plan text stays frontend-only in v1; null-confidence floor enforced in code (floor 40) |

**00 rulings on splits:** OpenAI's round-3 "delete order_flow/technical_confirmation" was
overruled in round 4 with both models agreeing to the keep-with-constraints version.
OpenAI's floor suggestion of 42 was rounded to 40 — arbitrary either way, coded as a constant.

**Shipped:** `trading_agents_india/signal_schema.py` (`build_signal_json`, `apply_expiry`,
`human_summary`) + `tests/test_signal_schema.py` (7 passing). Spec: [`DESK_SIGNAL_JSON.md`](../../05_analysis/docs/DESK_SIGNAL_JSON.md).

**Not shipped / honest gaps:** position-aware execution-plan coaching (needs paper-ledger
position join — v2); real entry/stop/targets (need persisted 1m option-premium OHLC — same
blocker as `MIX-DUAL-INDEX-MASTER`); order-flow delta (no Dhan surface, stays UNAVAILABLE).

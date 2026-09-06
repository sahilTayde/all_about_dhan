# docs/RESEARCH.md — research charter

## Scope

- **Default YouTube source:** official Dhan channel [https://www.youtube.com/@DhanHQ](https://www.youtube.com/@DhanHQ) while that row is enabled `TIER_1` in [`config/workspace.yaml`](../config/workspace.yaml). Customers switch channel by changing a URL/`enabled` flag there. Non-Dhan channels are `EXTERNAL_RESEARCH`.
- First markets: NIFTY, BANKNIFTY, SENSEX **index options**. Stock-only videos may be catalogued and tagged `STOCK_ONLY`; they are out of Phase-1 strategy construction unless the idea clearly transfers to index options.
- Education is not proof. Popularity ranks **which video to read first**, not strategy quality.

Long-form Stage 1–N plan: [`teams/01_research/youtube/PLAN.md`](../teams/01_research/youtube/PLAN.md). Ecosystem URL classes: [`teams/01_research/docs/DHAN_ECOSYSTEM.md`](../teams/01_research/docs/DHAN_ECOSYSTEM.md). Awareness (not legal advice): [`COMPLIANCE.md`](COMPLIANCE.md).

---

## SOURCE HIERARCHY (addendum)

Workspace policy for **strategy-related sources**. Does not replace PLAN.md’s exchange/regulator/textbook tiers, which remain for independent `VALIDATION` only.

1. **Tier 1 — official Dhan `@DhanHQ` transcripts** (default). Playlists/videos on [https://www.youtube.com/@DhanHQ](https://www.youtube.com/@DhanHQ) ([playlists](https://www.youtube.com/@DhanHQ/playlists)). Sole **Dhan-video** transcript source while `implementation.indicators` is `dhan_only`. Live channel list: [`config/workspace.yaml`](../config/workspace.yaml).
2. **Tier 2 — Dhan official product / docs.** ScanX, charts (`tv.dhan.co`), Options Trader, DhanHQ API (`dhanhq.co/docs`). Secondary references for how a Dhan tool works. **Cannot replace** Tier 1 transcripts. Indicator **API vs chart-only** catalog: [`teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md).
3. **Tier 3 — user-approved `EXTERNAL_RESEARCH` videos** (other channels in workspace.yaml, PhD / market research). Allowed for strategy *ideas* only when `enabled: true`. Must be tagged `EXTERNAL_RESEARCH`. Must **not** silently replace Dhan transcripts. Production indicators remain **Dhan-only** unless `implementation.indicators` says otherwise.
4. **Never evidence:** social, app-store/download, DEXT installers, Ticker, TradingView-connect, contact, community (`madefortrade.in`), MTF/forms. Never treat those as claims.

---

## Three-layer knowledge (never collapse)

Copied from the Codex plan; every extracted concept uses all three:

**LAYER A — `SOURCE_FACT`**  
What Dhan actually said (video id, URL, timestamp, quote or close paraphrase). No cleanup that changes meaning.

**LAYER B — `VALIDATION`**  
Independent check against exchange docs, DhanHQ API docs, and authoritative technical references. Record supported / partially supported / context-dependent / unsupported. Do not rewrite the claim to make it look correct.

**LAYER C — `HYPOTHESIS`**  
Our testable statement for index options. Mark `UNVALIDATED` until backtests (and review) complete. Never claim profitability here.

---

## Status labels (use only these)

From Codex Appendix C:

```text
DISCOVERED
TRANSCRIPT_PENDING
TRANSCRIPT_VERIFIED
EXTRACTED
INDEPENDENTLY_VALIDATED
HYPOTHESIS
BACKTEST_PENDING
BACKTESTED
OOS_VALIDATED
WALK_FORWARD_VALIDATED
ROBUSTNESS_VALIDATED
PAPER_TRADING
PRODUCTION_CANDIDATE
PRODUCTION
DEGRADED
REJECTED
RETIRED
DATA_INSUFFICIENT
SOURCE_UNCERTAIN
```

Review failure uses `FAILED REVIEW` (see [`REVIEW.md`](REVIEW.md)). Missing evidence: `UNKNOWN` or `DATA_INSUFFICIENT` — do not guess.

---

## Pipeline (research teams)

1. **01_research** — catalog, filter, transcripts, `SOURCE_FACT` extraction.
2. **02_phd_math** + **03_phd_market** — `VALIDATION`.
3. **04_quant** — `HYPOTHESIS` + strategy spec.
4. **06_backtesting** + **05_analysis** — tests and scorecards.
5. **09_review** — five-pass + red-team. Only then `RESEARCH_READY_FOR_PROGRAMMING` to **07_coding**.

Handoffs: [`HANDOFF.md`](HANDOFF.md).

---

## Current status

YouTube Data API key validated. Catalog: **2,034** `@DhanHQ` videos. Transcripts: **33** `TRANSCRIPT_VERIFIED` (see STATUS for UNAVAILABLE/PENDING after 429). First SOURCE_FACT DRAFT exists (`teams/01_research/docs/handoffs/`); not all 33 extracted. Master plan v0.1 DRAFT in `teams/04_quant/docs/MASTER_STRATEGY_PLAN.md` — `UNVALIDATED`, not a coding green light. Run report: [`teams/01_research/youtube/docs/RUN_REPORT.md`](../teams/01_research/youtube/docs/RUN_REPORT.md).

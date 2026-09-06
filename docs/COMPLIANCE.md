# docs/COMPLIANCE.md — research and production awareness

This is **process awareness** for all_about_dhan, not legal advice, not investment advice, and not a SEBI opinion.

---

## Education is not advice

Official `@DhanHQ` videos, Dhan product UIs, and the Indicator newsletter are **education and product surfaces**. They are not a recommendation to trade, not proof of edge, and not a substitute for independent validation, backtests, and review.

Never present this project, a signal, or a UI as:

- investment or portfolio advice,
- a guaranteed return or guaranteed profit,
- a system that eliminates risk.

Status labels and three-layer records (`SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`) exist so education is not silently recast as advice. See [`RESEARCH.md`](RESEARCH.md).

---

## Provenance (required)

Every Dhan-derived claim, indicator, or rule keeps:

- source URL,
- `video_id` (YouTube),
- timestamps (start–end),
- retrieval time,
- layer label (`SOURCE_FACT` vs `VALIDATION` vs `HYPOTHESIS`),
- origin tag (`DHAN-DERIVED` vs `EXTERNAL_RESEARCH` vs `PROJECT-DERIVED`).

Do not drop, rewrite, or “clean” provenance. Production work must be reconstructable from this audit trail. Missing evidence: `UNKNOWN`, `DATA_INSUFFICIENT`, or `SOURCE_UNCERTAIN` — do not guess.

---

## Production audit trail (later)

When (if) anything is paper-traded or live:

- retain the research packet that passed review (`RESEARCH_READY_FOR_PROGRAMMING`),
- retain source ids, timestamps, and parameter-as-spoken vs parameter-as-coded,
- retain signal time, whether the user took the trade, and mark-to-market.

A **risk engine** (limits, kill switch, override) is **later** — not Phase 0. Architecture must leave room for it; do not imply it already exists.

---

## SEBI / advisory (pointer only)

Before live management of **external** capital, obtain qualified Indian legal/compliance advice. This repo does not provide that advice.

Awareness list (from the YouTube research plan, §91): SEBI regulations, advisory / portfolio-management requirements, broker/API terms, client authorization, recordkeeping, disclosures, suitability, taxation, data licensing.

Canonical write-up: [`teams/01_research/youtube/PLAN.md`](../teams/01_research/youtube/PLAN.md) §91 *Legal / compliance awareness* and Appendix A (SEBI: https://www.sebi.gov.in/). Do not duplicate or interpret that appendix here.

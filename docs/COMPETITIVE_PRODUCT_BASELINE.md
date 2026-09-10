# Competitive product baseline — signal portal

**Date:** 2026-09-09  
**Founder ask:** study reference products, define what we must match, and make our baseline stronger before coding.  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.**

References reviewed:

- AmiSignals — <https://amisignals.com/Features.htm>
- Stockara — <https://www.stockara.in/about.html> returned 409; fallback snippets from Techjockey, marked `VERIFY`
- Trend Finder — <https://www.trendfinder.reacoms.in/>
- BreakingTrade / SarthoAI — <https://breakingtrade.com/ai-market-analysis>

Dual-model review: [`COMPETITOR_VP_COUNCIL_2026-09-09.md`](../teams/00_orchestrator/docs/COMPETITOR_VP_COUNCIL_2026-09-09.md).

---

## Competitor Feature Baseline

| Product | What they sell | Useful baseline | Do not copy |
|---------|----------------|-----------------|-------------|
| AmiSignals | Signal generation, confirmation, scanners, alerts, risk planning | Clean mobile-friendly interface, AI-assisted quality score, multi-timeframe confirmation, volatility risk manager, risk-reward calculator, option-chain tools | Any implication that a quality score is a win rate |
| Stockara | Stock market software (`VERIFY` from third-party snippets) | Live tick data, algo signals, stock screener, price/volume/news/sentiment alerts, charting, audit trail, reports, web/desktop support | Unverified claims until direct source is available |
| Trend Finder | MT4 buy/sell signal + real-time data | Popup/sound alerts, scanner over many instruments, re-entry signals, backfill timeframes, demo/support/pricing | “100% accurate” claims; unsupported profit testimonials |
| BreakingTrade / SarthoAI | AI market analysis + scanner + assistant | AI chat, ML breakout signals, market profile, 200+ instrument scanner, option screener, Telegram alerts, fast response marketing | Over-broad equity universe for our first product; AI as magic |

---

## What We Must Match

1. **Clear ticket:** entry, stop, target, invalidation, status.
2. **Fast alerting:** in-app sound/toast first; Telegram/webhook later.
3. **Scanner / watchlist:** at least NIFTY, BANKNIFTY, SENSEX; no 200-stock scope until index-option core works.
4. **Risk manager:** volatility-aware stop/target sanity, not fixed fantasy levels.
5. **Options-chain context:** OI change, PCR, ATM CE/PE, IV/skew when available.
6. **AI assistant category:** customer can ask simple questions later; day-1 LLM is internal dealer counsel.
7. **Reports:** daily signal book, mistakes, model/counsel disagreements, data gaps.
8. **Supportability:** founder `/pm` shows health before customers complain.

---

## What We Must Not Copy

- “100% accurate” or profit-guarantee language.
- Broker execution buttons before the gate.
- Wide stock/crypto/FX scope before index options are reliable.
- Raw indicator soup on the customer portal.
- AI hallucinated trades.
- Unverified tick/backfill claims.
- A static signal that stays live after reversal or stale tape.

---

## Our Edge One Step Ahead

**Narrower but smarter:** DhanHQ-only NIFTY / BANKNIFTY / SENSEX index-options CE/PE buy-first signals.

The edge is not “we have more indicators.” The edge is:

1. **Dealer intelligence:** a live desk agent can HOLD, kill, or advise partial-booking when OI/price/news changes.
2. **Mistake learning:** every bad ticket creates a labeled mistake for nightly review.
3. **Local ML first:** models learn from features/outcomes without burning LLM tokens.
4. **Controlled LLM live counsel:** Gemini/OpenAI review compact live-state facts during market, but do not execute or invent trades.
5. **Audit trail:** every signal links to data snapshot, feature version, model version, counsel verdict, and reason code.
6. **Founder PM:** service/key/rate-limit health visible on `/pm`.

---

## Live LLM Counsel Design

This updates the previous “zero LLM fast path” rule:

- **Still true:** no LLM blocks the fast signal path.
- **Allowed:** an asynchronous **LLM risk counsel loop** can review compact live-state snapshots and advise HOLD / reduce-risk / exit-review / partial-booking suggestion.
- **Not allowed:** LLM cannot place orders, cannot create a fresh CE/PE from vibes, cannot override deterministic risk hard stops, cannot claim fills.

Example:

```text
Input to counsel:
underlying=NIFTY
ticket=BUY CE, entry=150, stop=126, target=192
snapshot=spot velocity, option LTP path, OI delta, PCR delta, news tags, time_to_expiry

Allowed output:
RISK_REVIEW: OI reversal + premium momentum fading. Consider partial profit / exit review.

Not allowed:
SELL 5 lots now.
```

Token controls:

- Trigger only on material changes: OI delta, premium velocity, news shock, stale-tape risk, near stop/target, counsel disagreement.
- Send 1 compact JSON state, not raw chain.
- Cache by `(ticket_id, state_hash, counsel_prompt_version, model)`.
- Budget per market session; if exhausted, use deterministic HOLD/kill rules.

---

## ML Learning Loop

| Stage | What learns | Data required | Output |
|-------|-------------|---------------|--------|
| ML-0 | Rules | ticket + data age + premium path | feasibility / stale / kill |
| ML-1 | Classifier | bars, chain, stage, outcome | hold-vs-trade bucket |
| ML-2 | Regime model | session tags, news, expiry, volatility | normal / event / expiry / chop |
| ML-3 | Exit assistant | favorable/adverse excursion, OI delta, premium velocity | partial-book / exit-review alert |
| ML-4 | LLM distillation | large labeled counsel + outcome corpus | explanation assistant only |

Nightly:

1. Save all signals and state changes.
2. Label mistakes.
3. Rebuild RAG/SQL features.
4. Run backtests and ablations.
5. Ask faculty: root cause + next test.
6. Ask counsel only on compact reports.
7. Emit `BACKTEST_REQUIRED`; no auto-retune.

---

## Customer Portal Baseline

Customer `/`:

- Command center: current CALL / PUT / HOLD.
- Ticket: strike, entry, stop, target, invalidation, TTL/stale timer.
- Dealer note: trend + 3m chain + cited news.
- Risk counsel feed: short live messages such as “premium momentum fading; review profit.”
- Alert settings: sound/toast now; Telegram/webhook later.
- Today’s book: paper/shadow/mock labeled clearly.
- Mistake transparency: after close, plain-English lesson, not excuse.

Founder `/pm`:

- Active agents/departments.
- Services up/down.
- Dhan/OpenAI/Gemini key/rate limit.
- Data freshness.
- RAG/nightly/auditor status.
- Next action.

Research `/desk`:

- Indicator internals, factor checklist, model features, counsel payloads, backtest diagnostics.

---

## First Build Tickets

1. **DATA-001 Warehouse schema:** append-only market events, chain snapshots, feature rows, signals, ticket events, outcomes, research sources.
2. **DEALER-001 Feasibility/state machine:** `FEASIBILITY_REJECTED`, `DEALER_KILLED`, stale TTL by stage, exit/kill priority.
3. **PM-001 Founder canvas:** `/pm` cards for service/key/rate-limit/data freshness + next action.
4. **LLM-001 Live counsel loop:** asynchronous Gemini/OpenAI risk review on compact state snapshots with token budget.
5. **UI-001 Customer command center:** beautiful mobile-first ticket + risk counsel feed + alert controls.
6. **ML-001 Local baseline:** feature table + deterministic model/rules for hold-vs-trade and exit-review shadow labels.


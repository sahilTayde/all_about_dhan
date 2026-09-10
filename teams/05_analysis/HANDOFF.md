# Handoff log — Team 05 Analysis

## As of now (2026-09-09) — Dealer fast-path standards

```text
From:     teams/05_analysis
To:       00 / 07 / 09
Date:     2026-09-09
Status:   SPEC / NOT_CODED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: dealer feasibility and stale kill are deterministic/local; counsel is
  advisory and cached; exit/kill/expire beats entry; customer copy stays simple.
Rejected: LLM-generated CE/PE; keeping dead IN-PROGRESS; raw indicator soup on /;
  fake fills.
UNKNOWN: no code yet for reason codes or TTL by stage.

Artifacts: docs/FRONT_DESK.md, docs/CUSTOMER_PORTAL_UX.md
```

## As of now (2026-09-09) — D5 Front desk dealer spec

```text
From:     teams/05_analysis
To:       00 / 07 / 09 / founder
Date:     2026-09-09
Status:   SPEC / UNVALIDATED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Dealer boss; FEASIBILITY_REJECTED on fantasy SL/target (150/96/250 lesson);
  counsel reviews our ticket; mistake book → nightly faculty; / vs /pm split.
Rejected: Live orders; invented fills; indicator soup on customer /.
UNKNOWN: rules not coded.

Artifacts: docs/FRONT_DESK.md, SKILL.md
```

Newest first.

---

## As of now (2026-09-08) — MIX-PCR-EXTREME-HOLD + lean ticket talk

```text
From:     teams/05_analysis
To:       00 / 03 / 04 / 09
Date:     2026-09-08
Status:   overlay note / UNVALIDATED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: extreme PCR / PCR-without-price = HOLD ticket (CUSTOMER_TALK),
  not alpha, not catalog delete; ATM LTP for Entry/SL/TP else empty;
  EARLY valid; no indicator soup on `/`.
Rejected: PCR numeric laws; mixing INDEX pts into premium SL/TP; promote.
UNKNOWN: live 3m snapshot Δ vs ATM wall still HYPOTHESIS.
```

Newest first.

---

## As of now (2026-09-08) — CLUB-GR off customer confidence

```text
From:     teams/05_analysis
To:       07 / 04 / 00
Date:     2026-09-08
Status:   CUSTOMER_TICKET working-path
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: `/` playbooks = MIX-DEFAULT-BUY + Okala-IN notify.
  MIX-CLUB-GR PARKED (KEEP_ALL). Confidence does not add club agreement.
Rejected: Gap+expansion as a second customer playbook; win rates.
```

Newest first.

---

## As of now (2026-09-06) — customer ticket + confidence box

Suggested CE/PE + stop/target + right-rail **agreement** confidence. Customer decides. Not a win rate. Not a fill.

Newest first.

---

```text
From:     teams/05_analysis
To:       07 / 04 / 00 / 09
Date:     2026-09-06
Status:   CUSTOMER_TICKET draft / paper UI / UNVALIDATED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
CUSTOMER_TICKET.md + ConfidenceBox on `/`. Score capped; fairness line required.
Eligible playbooks in plain words. TookTrade = customer decide.

Artifacts:
- teams/05_analysis/docs/CUSTOMER_TICKET.md
- apps/web/src/components/ConfidenceBox.jsx
```

---

## As of now (2026-09-03)

Paper `/ws/signals` does **not** include the 3m chain or news hold yet — 05 fuse still required before a customer CONFIRMED is honest. Chain **3m**. Analog empty. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/05_analysis
To:       teams/04_quant, 03_phd_market, 06_backtesting, 09_review (00 informed)
Date:     2026-09-03
Status:   DRAFT customer-talk spec / HYPOTHESIS / UNVALIDATED / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     talk+hold overlay — not a new STRAT; no live Dhan; no npm

Summary:
CUSTOMER_TALK.md: agent reviews trend + 3m chain + cited RSS, then talks
on customer `/` (no MACD/RSI/STRAT IDs). NEWS_DAY / MACRO_EVENT **holds
the ticket** (no EARLY/CONFIRMED). Teacher STRATs stay in the backtest
catalog. Schema `vetoes[]` / stage VETOED map to spec `holds[]` /
`session_tags[]` and customer HOLD. Analog: “We tagged days like this as
NEWS_DAY; we do not use them to claim a win rate; if memory exists,
describe path. Today memory empty.” CAS 15:15–15:40: Closing Auction
Session in plain words, UNVALIDATED. Cite 04 MIX_CATALOG, 03
CAS_STRATEGIES, 06 EVENT_MEMORY — those three files are WAITING.

Accepted: news+chain+trend as review, not entry STRAT; hold ≠ delete.
Rejected: headline alpha; invented analog P/L; PCR laws; HTML scrape.

Artifacts:
- teams/05_analysis/docs/CUSTOMER_TALK.md
- teams/05_analysis/docs/SIGNAL_FUSION.md (hold ≠ catalog delete pointer)

What the next team must do:
- 04: write MIX_CATALOG.md when ready; keep 14 IDs; a 05 HOLD is not a drop.
- 03: write cas/CAS_STRATEGIES.md when ready; keep CAS UNVALIDATED.
- 06: write EVENT_MEMORY.md as path memory only — empty is honest; no P/L.

What the next team must not do:
- Invent win rates or analog P/L. Delete STRATs on NEWS_DAY. Scrape HTML.
- Put MACD/RSI/STRAT IDs on customer `/`. Call live Dhan. Start npm.

Blockers / UNKNOWN / DATA_INSUFFICIENT:
- MIX_CATALOG.md, CAS_STRATEGIES.md, EVENT_MEMORY.md not on disk;
  live chain DHAN_*; analog memory empty; Moneycontrol RSS VERIFY IF STABLE.

Review: n/a — notes to 09, not a five-pass
```

---

```text
From:     teams/05_analysis
To:       teams/04_quant, 03_phd_market, 09_review (00 informed)
Date:     2026-09-03
Status:   DRAFT overlay spec / HYPOTHESIS / UNVALIDATED / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     overlay only — not a new STRAT; no live Dhan; no npm

Summary:
SIGNAL_FUSION.md: news RSS/calendar → NEWS_DAY; 3m chain last snapshot
(OI, PCR, ATM CE–PE Δ); CAS daily book UNVALIDATED. Attach to 04 staging:
WATCH = chain+news mixing; EARLY blocked on NEWS_DAY/EXPIRY (expiry is
03/nightly tag — do not retune); CONFIRMED requires 04 primary, 05 may
only VETO; VETOED = news shock, STRAT-008 mixed-index, ST vs VWAP disagree
when 003 is primary. Sentiment 10m/15m/30m/1h still MOCK. Live chain TODO
until DHAN_*. Not headline alpha. No PCR numeric “Dhan law.” No win rates.

Accepted: overlay on existing 14 IDs; _exm OI walls as heuristic / selling
class / Phase-1 buy-first.
Rejected: PCR-extreme entry; Moneycontrol HTML scrape; 1m full-chain;
auto-retune; STRAT-015+; 05 promoting CONFIRMED.

Artifacts:
- teams/05_analysis/docs/SIGNAL_FUSION.md
- teams/05_analysis/docs/DESK_INTELLIGENCE.md
- packages/desk-intel/src/desk_intel/schema.py (reference only)
- config/workspace.yaml desk_intel.poll.chain_interval: 3m (unchanged)

What the next team must do:
- 04: bind 05 vetoes at WATCH/EARLY; keep CONFIRMED as 5m ST/MACD primary.
- 03: keep PCR definitions VALIDATION; keep EXPIRY tag ownership; no PCR law.
- 09: red-team overlay-as-alpha, mock sentiment-as-edge, 05 CONFIRMED promote.

What the next team must not do:
- Invent PCR thresholds or win rates. Scrape HTML. Poll full chain every 1m.
- Auto-retune from nightly. Call live Dhan. Start npm. Add STRAT-015+.

Blockers / UNKNOWN / DATA_INSUFFICIENT:
- Live POST /optionchain needs DHAN_*; quote OI VERIFY FROM DOCS;
  Moneycontrol RSS VERIFY IF STABLE; surprise_vs_consensus UNKNOWN;
  F&O close 15:30 vs 15:40 VERIFY; CAS book UNVALIDATED; 14 STRATs UNVALIDATED.

Review: n/a — notes to 09, not a five-pass
```

---

```text
From:     teams/00_orchestrator
To:       teams/05_analysis (+ 04_quant, 03_phd_market)
Date:     2026-09-01
Status:   DONE (3m chain + last snapshot; docs honesty) / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     dry-run schema — no live Dhan scrape

Summary:
Customer poll is 3m full chain (was 15m). Last snapshot remembered so OI/PCR/ATM
CE–PE Δ feeds signals. 1m ATM±N still optional. Sentiment 10m/15m/30m/1h is mock
schema. Do not invent STRATs or win rates. IN-PROGRESS after CONFIRMED.

Artifacts:
- config/workspace.yaml desk_intel.poll.chain_interval: 3m
- teams/00_orchestrator/docs/TASK_CUSTOMER_DESK.md
- teams/05_analysis/docs/DESK_INTELLIGENCE.md
- packages/desk-intel last.json + vs-last deltas

What the next team must do:
- Run python -m desk_intel poll-chain --interval 3m --offline
- Keep 1m full-chain off by default.

What the next team must not do:
- Place orders. Invent win rates. Poll full chain every 1m as default.
- Treat mock sentiment windows as measured edge.

Blockers: live chain still needs DHAN_*; quote OI VERIFY FROM DOCS.

Review: n/a
```

---

```text
From:     teams/00_orchestrator
To:       teams/05_analysis (+ 02_phd_math, 06, 08)
Date:     2026-09-01
Status:   DONE (PRE/POST jobs skeleton) / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     paper+shadow only — no orders

Summary:
Morning CLI now also gathers GIFT/SGX/pre-open/global VERIFY tape. Nightly recon
stamps outcomes; PhD handoff NIGHTLY_YYYY-MM-DD.md. Shadow = paper ledger.

Artifacts:
- teams/00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md
- packages/desk-intel premarket/outcomes/ledger/nightly
- python -m desk_intel nightly --offline
- python -m jobs post-market --offline

What the next team must do:
- Run dry commands. Edit yaml if RSS 404s. Do not scrape GIFT HTML as the only path.

What the next team must not do:
- Place orders. Invent Dhan GIFT REST. Treat recon param hints as validated.

Blockers: live chain DHAN_*; GIFT public quote unverified; F&O close UNKNOWN.

Review: n/a
```

---

```text
From:     teams/00_orchestrator
To:       teams/05_analysis (+ dhan-client, 03_phd_market)
Date:     2026-09-01
Status:   DRAFT skeleton / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     n/a — overlay only, no strategy coding

Summary:
Desk intelligence package: news RSS + Dhan option chain → MARKET_SIGNAL bias.
15m full chain default; 1m ATM±N quote path. No orders. Education ≠ advice.

Artifacts:
- teams/00_orchestrator/docs/TASK_DESK_INTELLIGENCE.md
- teams/00_orchestrator/docs/PERSONA_DESK.md
- teams/05_analysis/docs/DESK_INTELLIGENCE.md
- packages/desk-intel/
- config/workspace.yaml sources.news[] + desk_intel.poll

What the next team must do:
- Run python -m desk_intel morning --offline and edit yaml news URLs if RSS 404s.
- 03: keep CHAIN_METRICS honest (VALIDATION vs HYPOTHESIS).
- Later: optional GET /paper/signal wiring from paper_signal.py adapter.

What the next team must not do:
- Place orders. Claim guaranteed CE/PE. HTML-scrape Moneycontrol as the only news path.
- Poll full option chain every 1m as default.

Blockers: live chain needs DHAN_* + Data API; Moneycontrol RSS VERIFY IF STABLE;
quote OI field VERIFY FROM DOCS; surprise-vs-consensus UNKNOWN on RSS.

Review: n/a
```

# Company departments — founder org (2026-09-09)

**Product class:** India index-options **signal company** (Stratzy / Algoji / GoCharting Quantman *class*). Working name still **all_about_dhan**. Broker **DhanHQ only**. First book: NIFTY / BANKNIFTY / SENSEX CE/PE **buy** tickets.

**00 ruling after Gemini + OpenAI counsel** ([`COUNSEL_ORG_2026-09-09.md`](../teams/00_orchestrator/docs/COUNSEL_ORG_2026-09-09.md), [`COUNSEL_SCALE_2026-09-09.md`](../teams/00_orchestrator/docs/COUNSEL_SCALE_2026-09-09.md), [`COUNSEL_SKILLS_2026-09-09.md`](../teams/00_orchestrator/docs/COUNSEL_SKILLS_2026-09-09.md)): both said **AGREE_WITH_CAVEATS** / aligned. We **do not delete or renumber** teams `00`–`09`. We **overlay five departments**. Gate stays **not** `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.** Dashboard P/L stays **MOCK** until a real book exists. Counsel does **not** invent buy/sell.

**How to read this file:** founder + PM first. Team IDs stay the engineering backbone. Founder requirement trace: [`FOUNDER_REQUIREMENTS_TRACE.md`](FOUNDER_REQUIREMENTS_TRACE.md).

---

## Now / Why / Next

| | |
|--|--|
| **Now** | We have a research factory (`00`–`09`), a mock customer desk, and written standards for fast architecture, token control, ML, and UX. We do **not** yet have a founder health canvas, a warehouse schema, vector RAG, local ML, or a dealer feasibility gate. |
| **Why overlay, not rebuild** | Counsel: renumbering breaks provenance, auditor paths, and the SDLC gate. The 00–09 roster is the **pipeline**. Departments are **who the founder talks to** and **who reviews whom**. |
| **Next** | Build the platform in this order: warehouse/event schema → dealer `FEASIBILITY_REJECTED` → `/pm` health canvas → customer UX refresh → local ML baseline. Do **not** restart npm until the founder asks. |

---

## The picture (simple)

```text
Founder
   └── talks daily to  D4 Project Manager  (canvas /pm)
                         │
         ┌───────────────┼───────────────┬────────────────┬────────────────┐
         v               v               v                v                v
      D1 Engineering   D2 Analyst      D3 Docs         D4 itself        D5 Front desk
      boss 07          faculty boss    boss 09         (00 ops)         dealer boss 05
         │               │               │                                │
      07 08 RAG SQL    01 02 03        Docs Auditor                     customer /
      ML nightly       04 05 06        + scribe                         + counsel
      backtest code    chairs                                           + mistake book
```

Teams `00`–`09` still do the work. A **department boss** reviews that work and, when the change is material, runs **Gemini + OpenAI counsel** (`COUNSEL_PROVIDER=both`). Neither model places an order.

Product engineering standard: [`PRODUCT_ARCHITECTURE_STANDARDS.md`](PRODUCT_ARCHITECTURE_STANDARDS.md). Token/ML standard: [`TOKEN_ML_STRATEGY.md`](TOKEN_ML_STRATEGY.md). Customer UX standard: [`CUSTOMER_PORTAL_UX.md`](CUSTOMER_PORTAL_UX.md).

---

## Department roster

| Dept | Name | Boss (talks to PM) | Teams | Customer-facing? |
|------|------|--------------------|-------|------------------|
| **D1** | Engineering | **07 Engineering Boss** | 07 coding, 08 QA, plus *code* in `packages/` / `apps/` | No (except they ship the site) |
| **D2** | Analyst faculty | **Faculty Dean** (00 chair; 04 vice-chair) | 01 librarian, 02 math+stats, 03 market, 04 quant+algo, 05 fusion, 06 score | No (ideas only) |
| **D3** | Documentation | **09 Docs Boss** | 09 Docs Auditor + documentation agent | Founder docs |
| **D4** | Project management + monitoring | **00 PM** | 00 orchestrator ops | **Founder `/pm` only** |
| **D5** | Front desk (dealer + portal) | **05 Dealer Boss** | 05 talk + 07 `/` | **Yes — customer `/`** |

**Founder daily talk:** **D4 PM only.** Other bosses file status into the PM canvas. Chat threads are backup, not the market-hours surface.

Internal research view stays **`/desk`**. Do **not** dump indicator soup on `/`. Do **not** put infra errors on the customer first screen (tab `/pm` for that). Gemini suggested merging portal into `/desk` — **rejected**. Customer `/` vs research `/desk` vs founder `/pm` stay three views, **one site**.

---

## D1 — Engineering (coding)

**Boss:** 07. **Reviewers:** 08 (tests), 09 (docs drift). Material merges: counsel job `REVIEW_NOTES`.

### What D1 must build (product, not a toy)

| Section | Section boss | Does | Must not |
|---------|--------------|------|----------|
| **C1 API / Dhan** | dhan-client owner | Quotes, 3m chain, charts, SafeMode | Live `place_order`; invent REST fields |
| **C2 Warehouse** | data owner | SQLite **now**: append-only market events, bars, chain snapshots, features, signals, ticket events, outcomes, research provenance | Git-add `*.sqlite`; MySQL/Postgres until volume/concurrency proves need |
| **C3 RAG** | 01+07 | Ingest **API KB + book notes + STRAT/MIX** into `agent_rag` (FTS5 now). Optional local embeddings/sqlite-vec later | Re-read whole books in an LLM every ticket |
| **C4 Local models** | 04+07 | Offline rules + tabular classifiers (regime / hold-vs-trade / feasibility assist) so market-hours flow burns **zero LLM tokens** | Claim a win rate; auto-promote; fine-tune an LLM before labeled data |
| **C5 Backtest engine** | 06+07 | Historical runs, costs, OOS, analog memory | Nightly auto-retune; invented fills |
| **C6 Nightly factory** | 00+07 | Pull → review → **update docs** → update RAG/SQL → **propose** code → **run backtest** → auditor last | Write production MIX params; skip `BACKTEST_REQUIRED` |
| **C7 Portals** | 07 | Customer `/`, research `/desk`, founder `/pm` | Restart npm unasked; Dhan keys in the browser |
| **C8 QA** | 08 | Fixtures, paper checks, key/health probes | Treat mock P/L as a gate |

**Junior / founder coding review:** all coding notes live under [`teams/07_coding/docs/`](../teams/07_coding/docs/) plus this file. Section bosses write a short “what changed / what to click / what is still MOCK.”

**SQLite vs MySQL (counsel ALIGNED):** warehouse is **SQLite now** (`data/knowledge/` + recon JSON). MySQL is a later scale ticket, not a day-1 rewrite.

**RAG vs vectors (counsel ALIGNED):** **FTS5 now**. Embeddings / sqlite-vec when FTS misses API+book questions. API docs + book extracts go into the same store with `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS` tags.

**Tokens:** retrieval = local. Tokens = pre-market, post-market, dealer sanity, faculty “what to change,” and counsel on our call — not “read Natenberg again.” **No LLM calls on the market-hours fast path.**

---

## D2 — Analyst faculty (PhD chairs)

**Boss:** Faculty Dean (00). **Vice:** 04 Quant. Chairs **review each other**. They do **not** delete `STRAT-001`–`014` (`KEEP_ALL`).

| Chair | Home | Job | If a book fails they must |
|-------|------|-----|---------------------------|
| **PhD Math** | 02 | Greeks, IV, indicator identities, HQ vs compute | Grid the *formula* (e.g. 3m vs 5m), not a silent “fix” |
| **PhD Statistics** | 02 (role, not a new team folder) | Sample size, OOS, costs, multiple-test, SCORE_SAMPLE vs analog | Say *which* window/cost/filter to try next — or `DATA_INSUFFICIENT` |
| **PhD Market** | 03 | Clocks, lots, CAS, chain as positioning, India microstructure | Name the exchange rule that blocks the idea |
| **PhD Quant** | 04 | MIX/STRAT catalog, staged signals WATCH→EARLY→CONFIRMED→**IN-PROGRESS** | New `MIX-*` with origin tag — **no STRAT-015+** |
| **PhD Algo** | 04 (role) | Parameter / regime proposals the engine can actually run | Write the **next ablation**, not only FAIL |
| **Librarian** | 01 | @DhanHQ facts, English bind | No strategies from a video alone |
| **Fusion** | 05 | News + **3m** chain → hold vs talk | News is a **ticket hold**, not alpha and not a catalog delete |
| **Score lab** | 06 | Backtest + `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` | No promote; no nightly param write |

Skills: each chair’s `SKILL.md` in that team folder. Books: `config/workspace.yaml` `sources.books[]` (`use: VALIDATION`, not edge). A valid analyst output must include root cause, next test, and `UNKNOWN` / `DATA_INSUFFICIENT` when needed.

**Counsel:** Faculty Dean asks Gemini+OpenAI on *material* regime changes. Models **review**; they do not invent tape.

---

## D3 — Documentation agent

**Boss:** 09. **Standing job:** Docs Auditor (`python -m docs_auditor`) after requirement edits **and** nightly.

**Must document (simple English + links):**

- What the product is and what is **pending / working / MOCK**
- How to run the project; who the bosses are; how agents hand off (`docs/HANDOFF.md`)
- Skills and which chair owns them
- Tree: `docs/` `teams/` `apps/` `packages/` `data/`
- Requirements vs this overlay ([`MASTER_REQUIREMENTS.md`](MASTER_REQUIREMENTS.md))
- Founder service list (urls, what is up, why unused)
- **Next action** on every living doc (one line)

**Must not document:** secrets, fake win rates, live-order runbooks, whole-tree dumps.

Charter add-on: [`teams/09_review/SKILL.md`](../teams/09_review/SKILL.md). Five-pass is **still** the strategy gate. Auditor PASS ≠ research-ready.

---

## D4 — Project manager + monitoring

**Boss:** 00 PM. **Founder talks here.**

Canvas spec: [`FOUNDER_PM.md`](../teams/00_orchestrator/docs/FOUNDER_PM.md). Route **`/pm`** (not built yet — **TODO**). Colors + plain words + **next action**.

Must show:

- Which department / agent is **active**, what work, why
- Services: Vite `:5173`, API `:8000`, paper-hours loop, nightly, RAG rebuild
- Critical: OpenAI / Gemini / Dhan **key missing or HTTP 401/429**, rate limit, chain not pulling, API rejects
- Ticket + MIX state (WATCH / EARLY / CONFIRMED / IN-PROGRESS / HOLD / killed)
- What we implemented vs MOCK

Do **not** make the founder read Composer to know the desk is down.

---

## D5 — Front desk (dealer + customer portal)

**Boss:** 05. **Site:** customer `/` (clubbed with `/pm` as **one app, two tabs**). Spec: [`FRONT_DESK.md`](../teams/05_analysis/docs/FRONT_DESK.md).

The dealer is a **trader/dealer system**: gathers from department bosses + **3m** chain + cited news + Gemini/OpenAI **counsel on our ticket** (they do not invent CE/PE). Publishes only a **feasible** ticket.

**Hard lesson (founder):** a NIFTY CE near premium **150**, stop **96**, target **250** that never printed — that ticket must die. State: `FEASIBILITY_REJECTED` / `DEALER_KILLED` with a rule id. **No invented fill. No leftover IN-PROGRESS.** Exit/kill/expire has priority over new entry.

Mistake book → nightly → faculty “what to change.”

Execution stays **signal / paper-shadow**. `ExecutionClient` **refuses** live orders until tokens **and** a founder ask **and** the research gate. Brand = signal company. Internals = no live orders.

---

## Nightly factory (must / must not)

Counsel **ALIGNED** with the existing retune gate ([`RETUNE_GATE.md`](../teams/06_backtesting/docs/RETUNE_GATE.md)).

| Must | Must not |
|------|----------|
| Ingest tape/news/chain snapshots into SQL | Auto-apply MIX/STRAT production params |
| Rebuild / increment RAG | Skip Docs Auditor |
| Update progress docs + next action | Invent P/L or win rates |
| Run backtests that the data supports; else `DATA_INSUFFICIENT` | Promote on FAIL books |
| Emit `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` | Place or enable live orders |
| Open **proposed** code diffs / tickets for 07 boss | Silent rewrite of KEEP_ALL catalogs |
| Faculty propose the **next parameter change** | Delete STRAT-001–014 |

---

## Token budget (standing)

| Spend tokens | Do not spend tokens |
|--------------|---------------------|
| Pre-market synthesis | Re-reading books / API manuals |
| Post-market recon + mistake book | Repeating the same FTS hit |
| Counsel: is **our** call sane? | Generating a CE/PE from vibes |
| Faculty “what to change” | Bulk transcript translation (we already have English files) |

Full policy: [`TOKEN_ML_STRATEGY.md`](TOKEN_ML_STRATEGY.md). Cache counsel by `(job_id, facts_hash, prompt_version, model)`.

---

## Founder service list (as of 2026-09-09)

Do **not** restart these until asked. Empty = expected down.

| Service | URL / command | Status honesty |
|---------|----------------|----------------|
| Customer portal | http://localhost:5173 | MOCK ticket unless paper WS; **stopped** unless founder asked |
| Research `/desk` | http://localhost:5173/desk | Internal; not the product |
| Founder `/pm` | http://localhost:5173/pm | **Not built** (spec only) |
| Cleanup board | http://localhost:5173/cleanup | DhanHQ-only reset canvas |
| API health | http://127.0.0.1:8000/health | Dry-run; orders refused |
| API OpenAPI | http://127.0.0.1:8000/docs | Skeleton |
| Docs Auditor | `python -m docs_auditor` | Checker only |
| Counsel ping | `python -m trading_agents_india` counsel helpers | Keys in `.env` only |
| RAG | `python -m agent_rag status` | FTS5; not vectors |
| Nightly | `python -m desk_intel nightly --offline` | Emits `BACKTEST_REQUIRED` |
| Paper market-hours | stopped 2026-09-08 (`paper_ops_STOPPED.flag`) | Do not restart unasked |

---

## What we accepted / rejected (HANDOFF)

```text
HANDOFF
From:     00 after Gemini+OpenAI (both AGREE_WITH_CAVEATS)
To:       D1–D5 bosses / founder
Accepted: Overlay 5 departments on 00–09; SQLite+FTS5 now; one site three views
          (/, /desk, /pm); founder talks to PM; signal-company language;
          dealer feasibility kill; token budget; nightly updates docs/RAG/SQL
          and PROPOSES code + backtest; PhD Algo+Stats as roles not new team IDs.
Rejected: Delete/renumber 00–09; MySQL or embeddings as day-1; auto-retune;
          merge customer portal into /desk; live orders; win rates;
          STRAT-015+; treating auditor PASS as research-ready.
UNKNOWN:  /pm not coded; warehouse schema not coded; dealer rules not coded;
          sqlite-vec not scheduled.
```

# Dual-model counsel — company departments (2026-09-09)

**UTC:** `2026-09-10T01:20:06Z`
**Policy:** review only. Keys never printed. No live orders. **NO_PROMOTE.**

- Gemini ok=True model=`gemini-3.5-flash-lite` gap=``
- OpenAI ok=True model=`gpt-5.4-nano` gap=``

## Gemini

AGREE_WITH_CAVEATS

Q1: Keep 00-09 teams and overlay 5 departments, or renumber/delete teams? Why?
Keep the existing 00-09 SDLC roster as the core execution backbone because the build scripts, local sqlite workflows, and gatekeeper logic (NOT RESEARCH_READY_FOR_PROGRAMMING) are already mapped to these exact numbers. Overlay the 5 departments on top of 00-09 as organizational swimlanes rather than deleting them. Roster 00-09 represents the atomic engineering pipeline, while the 5 departments dictate governance, faculty oversight, and product delivery. Renumbering now would break import paths and test harnesses without adding structural value.

Q2: Where should PhD Algo and PhD Statistics sit (new folders vs roles under 02/04/06)?
They should sit under the existing 02 (PhD math) and 04 (quant/MIX/STRATs) folders as specialized sub-roles rather than spawning new root directories. 02 absorbs PhD Statistics for regime modeling and probability bounds, while 04 absorbs PhD Algo for execution logic and signal generation. This preserves the 00-09 namespace while granting faculty members distinct files (`faculty_math_stats.py`, `faculty_algo_quant.py`) to propose parameter and regime changes.

Q3: SQLite warehouse now vs MySQL now? Vector embeddings now vs FTS5 + later sqlite-vec?
Stick strictly to SQLite now for both the warehouse (candles, chain, P/L, research provenance) and local search because the workspace rules mandate local SQLite and separate transcripts.sqlite files without heavy external DB overhead. Keep FTS5 for text retrieval and local ML/rules, avoiding premature heavy vector embeddings or MySQL migration until scale and the review gate demand it. SQLite keeps nightly batch portability clean and avoids unnecessary network or container dependencies during paper/shadow phases.

Q4: What must the nightly batch do vs must NOT do (retune gate)?
The nightly batch must ingest daily data, run backtests, execute review + docs audit, update the local SQLite warehouse, and emit a RETUNE_PROPOSAL BACKTEST_REQUIRED report if parameters drift. It must NOT auto-apply retunes, push code changes to production, or bypass the review gate to generate live orders. All parameter modifications remain proposals awaiting human or formal gate sign-off.

Q5: Front desk vs PM canvas: one site two tabs, or two apps?
Implement as one app with two distinct tabs or views: `/desk` for research, dealer intelligence, and the front-desk customer portal, and `/pm` (or the founder health canvas) for service status, error logs, and department coordination. Keeping them in a single FastAPI/Streamlit application reduces deployment surface area while cleanly separating customer-facing ticket review from founder-facing system telemetry.

Q6: Token budget: what is allowed to call LLMs vs must be local RAG/ML?
Local RAG (SQLite FTS5), SQL warehouse lookups, and local ML models must handle all routine KB searches, math validation, and structural sanity checks to conserve tokens. LLM calls (Gemini/OpenAI) are strictly restricted to pre/post-market synthesis, deep qualitative reasoning by faculty, sanity-auditing model logic, and counseling the dealer desk on complex customer tickets. Unrestricted chat or repetitive text processing over raw books is strictly forbidden.

Q7: How should the dealer kill unrealistic SL/target (feasibility rules) without inventing fills?
The dealer desk must enforce mathematical feasibility rules based on current ATM/OTM implied volatility, delta, and realistic index velocity (e.g., rejecting a NIFTY CE strike 150 with a target of 250 when the distance exceeds daily ATR multiples). Instead of inventing paper fills or simulated execution profits, the system flags the ticket as `FEASIBILITY_REJECTED` or `DEALER_KILLED` with an audit trail citing DATA_INSUFFICIENT or risk-parameter violation.

Q8: Product language: call this a signal company (Stratzy class) while keeping no-live-orders until gate — AGREE or not?
AGREE with caveats. Position the brand externally as an institutional-grade signal portal and research factory (in the class of Stratzy, Algoji, or Quantman) to reflect serious product intent. However, internally and technically, execution must remain strictly PAPER/shadow with the ExecutionClient hardcoded to refuse live orders until the gate review formally clears it.

Q9: Name the 5 department bosses and who the founder talks to daily.
The 5 department bosses are: (1) Director of Engineering (07/08), (2) Dean of Analyst Faculty (02/03/04), (3) Chief Documentation Officer (09), (4) Head of Project Management & Monitoring (00/06), and (5) Head of Front Desk & Dealer Intelligence (01/05). The founder talks exclusively and daily to the Head of Project Management & Monitoring (the PM canvas), who aggregates status updates from all other four department bosses.

Q10: Top 3 risks if we implement this org poorly.
1) Organizational bloat and communication overhead between the 5 departments and 00-09 roster, causing analysis paralysis.
2) Token budget exhaustion through uncontrolled LLM queries by agents instead of leveraging local SQLite/FTS5 RAG.
3) Creeping live-order execution slipping past the ExecutionClient gate due to blurred boundaries between the front-desk signal portal and actual brokerage integration.

## OpenAI

AGREE_WITH_CAVEATS

Q1: Keep 00-09 teams and overlay 5 departments, or renumber/delete teams? Why?  
Keep 00-09. Overlay is safer because your roster already encodes gates (e.g., coding, testing, review+Docs Auditor, and the backtest+retune gate) and the system explicitly says “NOT RESEARCH_READY_FOR_PROGRAMMING” + execution is paper/shadow-only. Renumbering risks breaking provenance of what each team did in the 2026-09-06 failed review runs. The 5 departments should be an “org chart view” mapping to existing teams (00 orchestrator, 06 backtest+retune, 07 coding, 09 review+Docs audit, etc.), not a rewrite.

Q2: Where should PhD Algo and PhD Statistics sit (new folders vs roles under 02/04/06)?  
Place **PhD Algo** and **PhD Statistics** under the existing “PhD market+CAS” / “quant/MIX/STRATs” orbit—i.e., keep them as roles within the current 02/03/04/06 analyst workflow, not as new standalone folders. Concretely: assign them to the nightly batch’s **“book validation / parameter/regime revision proposal”** step before backtest runs, consistent with “KEEP_ALL STRAT-001-014 UNVALIDATED” and “Backtests FAIL / DATA_INSUFFICIENT.”

Q3: SQLite warehouse now vs MySQL now? Vector embeddings now vs FTS5 + later sqlite-vec?  
Go **SQLite now** because you already have `packages/agent_rag SQLite FTS5` and separate `transcripts.sqlite`, and the review gate + paper execution needs reliability over scale. For search: keep **FTS5 now** (no embeddings/vector), and only introduce **sqlite-vec later** if you can justify query types that FTS5 can’t support. Avoid MySQL/migration risk until you have sustained, non-failing nightly data volumes.

Q4: What must the nightly batch do vs must NOT do (retune gate)?  
Must do: refresh RAG/SQL research provenance, run the review pipeline that outputs **RETYPE_PROPOSAL BACKTEST_REQUIRED**-style artifacts, and run backtests that are feasible with current data—then stop with **FAIL / DATA_INSUFFICIENT** if you lack required inputs (do not “invent” results). Must NOT do: **auto-retune**. Your nightly emits “BACKTEST_REQUIRED” and you explicitly said “no auto-retune,” so retune actions remain behind the gate / review loop.

Q5: Front desk vs PM canvas: one site two tabs, or two apps?  
One product is fine: use **one site with two tabs** (“Front Desk / Dealer” and “Project Manager Canvas”) so the founder doesn’t manage multiple auth surfaces. But keep them logically distinct by permissions: PM view is internal process/alerts; Front desk is dealer intelligence and must not retain dead tickets (e.g., the founder’s unrealistic NIFTY ticket example) and must be governed by feasibility rules and paper/shadow mode.

Q6: Token budget: what is allowed to call LLMs vs must be local RAG/ML?  
Allowed LLM calls: summarize/counsel, draft doc/notes, route tasks, and “sanity check” interpretations—especially where your “Counsel module can ping Gemini+OpenAI.” Must be local: retrieval of KB from your existing RAG/SQL/local ML, and any repeated reading of books/chunks—use the SQLite/FTS5 warehouse as the source of truth. Keep token spend focused on **pre/post market analysis** and **auditing signal sanity**, not bulk reprocessing.

Q7: How should the dealer kill unrealistic SL/target (feasibility rules) without inventing fills?  
Use deterministic feasibility rules before any “paper execution” simulation:  
- Enforce “SL/target distance” relative bounds by instrument (NIFTY/BANKNIFTY/SENSEX) and option type (CE/PE), and cap target realism (e.g., disallow patterns like strike≈150 with SL=96 and target=250 when that target is structurally implausible).  
- If a ticket violates rules: mark it **invalid/kill** with a reason (rule-id + computed distance), and do **not** generate fills/PNL.  
- Preserve the ticket content but transition it to a “rejected” state so your portal doesn’t keep dead actionable tickets.

Q8: Product language: call this a signal company (Stratzy class) while keeping no-live-orders until gate — AGREE or not?  
AGREE_WITH_CAVEATS. You can brand as a “signal portal / signal company” (Stratzy-class intent) because the founder explicitly wants a real product posture, not a paper toy brand. Caveat: every user-facing claim must clearly reflect **paper/shadow execution until the gate** and must not present any P/L or “win rate” as fact (your workspace says DATA_INSUFFICIENT for backtests so far).

Q9: Name the 5 department bosses and who the founder talks to daily.  
Bosses (map to your roster):  
1) **Engineering/Coding boss** → Team 07 (coding) lead. Founder daily touch: Engineering progress + integration blockers.  
2) **Analyst faculty boss (coordinator)** → Team 02/04 lead (PhD market+CAS / quant/MIX/STRATs umbrella). Founder daily touch: what books/regimes changed or are still blocked (no fabricated outcomes).  
3) **Documentation agent boss** → Team 09 (review+Docs Auditor) lead for process/docs. Founder daily touch: doc health + pending action list.  
4) **Monitoring/PM boss** → Team 06/00 orchestrator-runtime view. Founder daily touch: critical errors (OpenAI/Gemini/Dhan key expiry, rate limits, pull failures).  
5) **Front desk dealer boss** → Team 05 (desk-intel/customer talk) lead. Founder daily touch: incoming ticket quality, feasibility-rule kills, and learning loops.  
Founder talks daily ONLY to the PM canvas, per your requirement—so “daily talk” targets the PM boss, while the others report status into PM.

Q10: Top 3 risks if we implement this org poorly.  
1) **Gate bypass via process drift**: if nightly/agents start “retune” or imply execution outcomes, you’ll violate the “NOT RESEARCH_READY_FOR_PROGRAMMING” + execution client refusing live orders, and your portfolio becomes inconsistent.  
2) **Unverifiable results**: since backtests are currently **FAIL / DATA_INSUFFICIENT**, poor org design may still push forward “promises” (P/L, win rates) that you cannot support.  
3) **Dual truth / provenance break**: if the portal tickets, RAG/SQL warehouse, and transcripts provenance diverge (e.g., deleting or reusing records improperly), you’ll lose the audit trail needed for “review+Docs Auditor” to pass future reviews.

# File creation — agents + juniors

**Why this exists:** extra `.md` files burn tokens. Create only names on this page. Do not invent a second copy.

**Default read (new chat):** `docs/MASTER_REQUIREMENTS.md` → `teams/00_orchestrator/docs/CONTINUE_NEXT_CHAT.md` → `AGENT.md` → this file. Then **one** team `SKILL.md` for the ticket. Do not glob `**/*.md`.

---

## Allowlist (create/update these names only)

| Create | Where | When |
|--------|--------|------|
| `HANDOFF.md` | `teams/00`–`09/` and `docs/HANDOFF.md` (template) | **Already exists.** Append newest-first. Do **not** add `HANDOFF_TOMORROW.md`, `HANDOFF_2.md`, dated copies. |
| `SKILL.md` | `teams/00`–`09/` only | Missing playbook for that team. One file per team. |
| `README.md` | team / package / app | Missing folder intro. Keep short. |
| `PLAN.md` | repo root (board) or `teams/01_research/youtube/PLAN.md` (exists) | **Do not** add another `PLAN.md`. |
| `TASK_<TOPIC>.md` | `teams/00_orchestrator/docs/` | New standing ticket with no existing `TASK_*`. Prefer updating an open ticket. |
| `STRAT-001`–`014` | `teams/04_quant/docs/candidates/` | **Already exist.** Never `STRAT-015+`. |
| `MIX-*` | `teams/04_quant/docs/candidates/` + row in `MIX_CATALOG.md` | New club only. Origin tag required. |
| `CAS-*` | `teams/03_phd_market/cas/` | CAS book only. |
| `EQ-*` / `SO-*` | `teams/04_quant/docs/candidates/` | Equity/stock-options backlog — not the index default. |
| SOURCE_FACT packet | `teams/01_research/docs/handoffs/<videoId>.md` | New verified transcript extract. Packets (`OPTIONS_INDEX_PACKET.md` etc.) stay the rollups. |
| Backtest evidence | `teams/06_backtesting/docs/BACKTEST_<TOPIC>.md` | After a real run. **One** file per topic; overwrite/append. Do not stack `BACKTEST_*_YYYY-MM-DD.md` copies. |
| Review evidence | `teams/09_review/docs/` named charter files | Five-pass / KEEP_ALL / auditor. No `*_NOTES_YYYY-MM-DD.md` dumps. |
| `AUDIT_LATEST.md` | `teams/00_orchestrator/docs/` | Auditor writes this. Humans do not hand-author a second audit file. |
| `NIGHTLY_YYYY-MM-DD.md` | `teams/02_phd_math/docs/handoffs/` | **`desk_intel nightly` only.** Agents do not hand-author extras. Keep the latest; do not stack unused days. |
| `CONTINUE_NEXT_CHAT.md` | `teams/00_orchestrator/docs/` | **One** wake-up. Update in place. |
| `COUNSEL_QUANT_TRAINING.md` | `teams/00_orchestrator/docs/` | Joint Gemini+OpenAI on 02/04 training (no PDF ingest). Edit in place. |
| `PRO_QUANT_AGENT_PROMPT.md` | `teams/02_phd_math/docs/` | Standing prompt 02/04 must load. Edit in place. |
| `book_kb/*.md` + `book_kb/topics/*.md` | `teams/02_phd_math/docs/book_kb/` | Original exam notes only (no PDFs). Edit/add topics in place. |
| `book_reads/NOTE_*.md` + `CLUB_SEVEN_BOOKS.md` | `teams/01_research/docs/book_reads/` | Sibling notes + Research Boss club. Original notes only. **No PDF / chapter text.** |
| `RESEARCH_BOSS_SKILL.md` | `teams/00_orchestrator/docs/` | Standing prompt 00 loads to invoke 01 Research Boss + 00 transition. Edit in place. |
| `RESEARCH_BOSS_LOOP.md` | `teams/01_research/docs/` **and** `teams/00_orchestrator/docs/` | 01 = invent cycle. 00 = after 01: rag rebuild → `TOPIC_COVERAGE` → `RETUNE_PROPOSAL`. Edit in place. Do not add a third loop file. |
| `TOPIC_COVERAGE.md` | `teams/01_research/docs/` | Topic × book × KNOWN/PARTIAL/DI × desk hook. Edit in place. |
| `QUANT_SELF_REVIEW_LOOP.md` | `teams/06_backtesting/docs/` | Nightly/paper self-review → `RETUNE_PROPOSAL` only. Edit in place. |
| `BOOK_MODEL_TUNE.md` | `teams/06_backtesting/docs/` | Cache ML-001 + ML-002 book tune. **One** file; overwrite. Not a promote. |
| `SESSION_PREP_ML.md` | `teams/06_backtesting/docs/` | How to start paper dual-tape + `desk_ml score` at 09:15 IST. FOLLOW-GAP HOLD. Not a promote. |
| Cursor rule `*.mdc` | `.cursor/rules/` | New always-on routing. Keep short. |

Teacher books, `config/workspace.yaml` `sources.books[]`, STRAT/MIX/CAS catalogs, and `docs/` product standards (`COMPLIANCE`, `SECURITY`, `SDLC`, `REVIEW`, `INDEX`, `COMPANY_DEPARTMENTS`, …) are **edit-in-place**.

---

## Do not create

- Extra `CONTINUE_*`, `HANDOFF_TOMORROW`, scratch `NOTES.md`, `research.md`, `dump.md`, `*_council_*.md`, `open_ai_*` session dumps
- Duplicate `MASTER_REQUIREMENTS` / `AGENT` / `FILE_CREATION` anywhere else
- Team folders outside `00`–`09` (no `07_ui`, no `10_*`)
- `STRAT-015+`
- Root `*gemini*`, `*laerning*`, transcripts pasted as `.txt`
- Files under `data/recon/` (gitignored JSON is enough; do not add markdown logs)
- Second copies of `ASTRA_*`, counsel org/scale/skills dated dumps — use `COUNSEL_LLM.md` + `COMPANY_DEPARTMENTS.md`

## Do not read unless the ticket names them

- Whole-tree `**/*.md`
- Team `HANDOFF.md` logs except the owning team
- `teams/01_research/youtube/PLAN.md` (long) unless YouTube collector work
- Dated `BACKTEST_*_YYYY-MM-DD.md` except the path on the **score sheet**
- `AUDIT_LATEST.md` unless you just ran the auditor
- `data/recon/**`, `apps/web/node_modules/**`, `.venv/**`

## Layers

Never collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`. KEEP_ALL: STRAT-001–014 stay `BACKTEST_BOOK`. After requirement/HANDOFF/PLAN/AGENT/this-file edits: `python -m docs_auditor`.

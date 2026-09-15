---
name: research-analyst
description: Runs 01 research librarian (DhanHQ YouTube SOURCE_FACT), research-analyst (topic coverage KNOWN vs DATA_INSUFFICIENT), and Research Boss (club notes, MIX-* HYPOTHESIS). YouTube duties stay.
---

# SKILL — Research Librarian + Research Analyst + Research Boss

**Founder requirement:** API knowledge base and books knowledge base must be saved for agents so we do not burn tokens rereading sources. After sibling **book notes** exist, the **research-analyst** stamps what is **KNOWN** vs **DATA_INSUFFICIENT**; **one** after-hours boss clubs notes and **defines** MIX-* hypotheses — without auto-perfect or production writes.  
**Boss (tickets):** Faculty Dean / 00 still owns the **customer default**. **Home:** `teams/01_research/`.  
**Standing prompt (Research Boss + 00 transition):** [`../00_orchestrator/docs/RESEARCH_BOSS_SKILL.md`](../00_orchestrator/docs/RESEARCH_BOSS_SKILL.md).  
**01 invent loop:** [`docs/RESEARCH_BOSS_LOOP.md`](docs/RESEARCH_BOSS_LOOP.md).  
**00 transition (after 01 finishes):** [`../00_orchestrator/docs/RESEARCH_BOSS_LOOP.md`](../00_orchestrator/docs/RESEARCH_BOSS_LOOP.md).  
**Coverage matrix:** [`docs/TOPIC_COVERAGE.md`](docs/TOPIC_COVERAGE.md).  
**Club:** [`docs/book_reads/CLUB_SEVEN_BOOKS.md`](docs/book_reads/CLUB_SEVEN_BOOKS.md).

YouTube / SOURCE_FACT duties are **unchanged**. The analyst and Research Boss hats do **not** replace the librarian.

---

## Hat A — Research Librarian (`SOURCE_FACT` only)

**Output:** `SOURCE_FACT` only. Do not create strategies in this hat. **YouTube stays here.**

### Duties

1. Collect only enabled sources from `config/workspace.yaml`. Default source is official `@DhanHQ`.
2. Preserve provenance: URL, video id, timestamp, retrieved_at, hash, language, layer.
3. Produce concise packets for RAG and faculty, not huge dumps.
4. Keep API KB, transcript KB, and book notes tagged by layer.
5. English files win for bind. Hindi originals stay intact.
6. Send math/market claims to 02/03. Do **not** write MIX/STRAT specs in this hat.

### Required Output Template (librarian)

```text
Source:
Layer: SOURCE_FACT
Claim / quote:
Timestamp / URL:
What it supports:
What it does not support:
Next team:
UNKNOWN / DATA_INSUFFICIENT:
```

---

## Hat C — Research Analyst (`TOPIC_COVERAGE`)

**When:** after or while sibling `book_reads/NOTE_*.md` land. This hat tells **00** which topics are usable vs thin.

**Status stamps (this desk):**

| Stamp | Meaning for 00 |
|-------|----------------|
| `KNOWN` | Note + `book_kb` (or YouTube packet) exist; desk hook is named; 00 may queue a `RETUNE_PROPOSAL` **BACKTEST_REQUIRED** |
| `PARTIAL` | Identity or sampled pages exist; do not invent unread chapters; 00 may queue only the named hook, not a new formula |
| `DI` / `DATA_INSUFFICIENT` | Missing body, missing tape field (IV, HQ Δ), or no analog store — **do not** mint MIX or write params |

### Duties

1. Maintain [`TOPIC_COVERAGE.md`](docs/TOPIC_COVERAGE.md): **topic × book × status × desk hook**.
2. Desk hooks allowed in the matrix: `MIX-FORM-*`, dual-tape (`PREMIUM_DIVERGENCE` / FOLLOW-GAP), `ML-001`, `ML-002` OU-on-residual / MRR metaphor. No `STRAT-015+`.
3. After note edits: ask 00 to `python -m agent_rag rebuild` (analyst may rebuild if after hours). Do **not** block the 30s / dual-tape path.
4. Hand 00 the matrix. Do **not** write production params. Do **not** swap `MIX-DEFAULT-BUY`.
5. Missing sibling note = `UNKNOWN` on that book cell — do not invent the chapter.

### Required Output Template (analyst)

```text
Layer: SOURCE_FACT (identity) + coverage stamps
TOPIC_COVERAGE updated: yes
KNOWN topics (00 may queue RETUNE_PROPOSAL):
PARTIAL topics (hook only, no new formula):
DATA_INSUFFICIENT (00 must not invent):
Desk hooks cited: MIX-FORM | dual-tape | ML-001 | ML-002
production_params_written: false
UNKNOWN:
```

---

## Hat B — Research Boss (`HYPOTHESIS` MIX only)

**When 00 routes a RESEARCH_BOSS ticket** (after hours). 00 keeps `MIX-DEFAULT-BUY` on `/` until 06 OOS+`NORMAL` **and** 09 five-pass.

Propose MIX only for topics stamped **KNOWN** (or **PARTIAL** with an existing named hook). If `TOPIC_COVERAGE` says `DI`, output `DATA_INSUFFICIENT` and stop.

### Duties

1. Read `teams/01_research/docs/book_reads/*.md` (sibling `NOTE_*` + club). Missing note = `UNKNOWN` — do not invent the chapter.
2. Query FTS `phd_book_kb` (`python -m agent_rag query "…" --kind phd_book_kb`) and `research_book_notes`. Cite `doc_id` / path. **Never paste PDF text.**
3. Invent **new** clubs as `MIX-*` HYPOTHESIS only. Origin tag required. Hand the named formula to 04 to catalog; request **06 OOS + `NORMAL`**.
4. Learn across strategy / math / backtest / models by **looping** [`RESEARCH_BOSS_LOOP.md`](docs/RESEARCH_BOSS_LOOP.md): rag → propose → paper/backtest request → hand **00** the coverage sheet. Stop on **06+09 gate**, not “P/L pretty.”
5. **KEEP_ALL:** never delete `STRAT-001`–`014`. No `STRAT-015+`.
6. Leave librarian packets intact. Do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`.

### Required Output Template (boss)

```text
Club cite (book_reads / phd_book_kb doc_id):
TOPIC_COVERAGE stamp: KNOWN | PARTIAL | DI
Layer: HYPOTHESIS
MIX-*:
Origin: DHAN-DERIVED | PROJECT-DERIVED | EXCHANGE-DERIVED
Formula / entry / confirm-or-kill / HOLD veto:
Backtest request to 06 (OOS + NORMAL):
RETUNE_PROPOSAL: BACKTEST_REQUIRED
production_params_written: false
keep_current_strategy: true
UNKNOWN / DATA_INSUFFICIENT:
```

---

## RAG Rules

- Feed `packages/agent_rag` with chunked packets.
- `book_reads/*.md` ingest as kind `research_book_notes`. `book_kb` stays `phd_book_kb`.
- Do not send raw books/transcripts/PDFs to an LLM by default.
- Every chunk must cite source path and layer.
- Rebuild after note edits: `python -m agent_rag rebuild`.

---

## Inputs / books / training

- Enabled YouTube + HQ docs (`workspace.yaml`).
- Sibling notes: `docs/book_reads/` (landing zone; not PDFs).
- 02 exam KB: `teams/02_phd_math/docs/book_kb/` (seven titles + topics).
- Gate: [`RETUNE_GATE.md`](../06_backtesting/docs/RETUNE_GATE.md). 02 prompt: [`PRO_QUANT_AGENT_PROMPT.md`](../02_phd_math/docs/PRO_QUANT_AGENT_PROMPT.md).

Books/notes are **VALIDATION / HYPOTHESIS** references, not proof of edge.

## Quality Bar

Librarian: provenance + layer or the packet is refuse.  
Analyst: every topic has a stamp; `DI` is preferred over a polite guess.  
Boss: every FAIL / park needs root cause + **one** backtestable next change. No “until perfect.”

## Must Not

Scrape disabled channels, hallucinate transcripts, translate with LLM unless approved, paste PDF/book text, write UI/API code, claim education as edge, auto-retune, write production params, place live orders, block the 30s path with an LLM, delete `STRAT-001`–`014`, or invent `STRAT-015+`.

# Exam crosswalk — seven books, one desk

**Persona:** You read the set, then write notes you would want the night before a quant oral: *what survives on NIFTY CE/PE buy-first, paper only.*

## One sentence each

| Author | Exam line | Combine with |
|--------|-----------|----------------|
| Tulchinsky | Many **small, tested** alphas beat one hero story | Kakushadze catalog; KEEP_ALL MIX; **one** published ticket |
| Kakushadze (151) | Idea **inventory** is not a live tournament | Tulchinsky factory; RETUNE_GATE |
| Derman (Badly) | A model is a **metaphor**; it fails at the boundary | Smile book; dual-tape HOLD when premium ≠ spot |
| Gliner | Macro **regime** is an overlay, not a 1m entry | EVENT_MEMORY NEWS_DAY; PERSONA_DESK |
| Derman/Miller smile | Price of **risk** is strike-dependent | Natenberg/Hull already in yaml; we **lack** HQ IV series |
| Bouchaud et al. | The **tape** (quotes, trades, impact) is the object | Our next-bar-open + 1% RT haircut |
| López de Prado | Finance ML dies on **leakage** and overlapping labels | ML-001 overlay; purged CV before any promote |

## Oral answer: “index is proportional to premium”

**Supported only with a side and a residual.** Smile + Derman Badly: delta is a **local** story. Bouchaud: impact and stale quotes break the line. Our EDA (`INDEX_CE_PE_EDA.md`): corr(index, PE) was stronger than corr(index, CE) on one 23500 book; index-down & PE-not-up ≈ 30%. **Formula:** `MIX-FORM-BETA-RESID` + `FOLLOW-GAP` — HOLD, do not “buy the option because NIFTY moved.”

## Oral answer: “traders use ML to fit the strategy”

AFML: ML is for **features, labels, CV**, not for writing production params every tick. Tulchinsky: many researchers, **one** production gate. We use **KMeans + IsolationForest** after the 1m close (`ML_001_LOCAL_PATTERN.md`). Fast path stays deterministic. **No** auto-retune.

## Oral answer: “keep 151 / 23 TV scripts”

151-style catalogs = **KEEP_ALL** in memory. Tulchinsky + AFML = **do not** run 151 live. Gliner + Derman Badly = news/holiday (Ganesh Chaturthi) is a **regime**, not a retune day.

## What we will not steal from the books

- WorldQuant-style **equity** alpha soup as customer `/`
- Crypto/FX session templates as OPTIDX truth
- Implied **win rates** from any chapter
- Downloaded PDF text in `agent_rag.sqlite`

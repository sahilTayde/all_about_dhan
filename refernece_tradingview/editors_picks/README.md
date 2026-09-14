# TradingView Editor Picks catalog (harness input)

**Not** a customer book. **NO_PROMOTE.** No live Dhan orders. Do **not** copy Pine into this repo.

Human index: [`INDEX.md`](INDEX.md). Ingest playbook: [`teams/01_research/docs/TV_EDITOR_PICK_INGEST.md`](../../teams/01_research/docs/TV_EDITOR_PICK_INGEST.md).

Source list: [Editor Picks — strategies](https://www.tradingview.com/scripts/editors-picks/?script_type=strategies).

| File | Role |
|------|------|
| `INDEX.md` | One-page inventory + blockers |
| `catalog.json` | Durable registry (`MIX-TV-EP-001`–`023` listing + `024`–`025` factory calibrators) |
| `catalog.csv` | Spreadsheet view |
| `ingest_schema.json` | Factory field list for the next 1000 pines |
| `catalog.schema.json` | Slot shape for the 06 loader |
| `../stratigies/editor_pick.txt` | Public listing URLs |

Listing rows use `adapter: stub` until a **public-rule** Python port exists. IDs: `MIX-TV-EP-NNN` never `STRAT-015+`. KEEP_ALL `STRAT-001`–`014`.

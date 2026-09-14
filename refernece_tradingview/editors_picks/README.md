# TradingView Editor Picks catalog (harness input)

**Not** a customer book. **NO_PROMOTE.** No live Dhan orders. Do **not** copy Pine into this repo.

Source list: [Editor Picks — strategies](https://www.tradingview.com/scripts/editors-picks/?script_type=strategies).

| File | Role |
|------|------|
| [`INDEX.md`](INDEX.md) | Catalog agent listing notes |
| `ingest_schema.json` / `catalog.schema.json` | Ingest vs factory subset |
| `catalog.json` / `catalog.csv` | `EP-NNN` → `MIX-TV-EP-NNN` |
| `../stratigies/editor_pick.txt` | Public URLs only |

06 factory reads `adapter` (`sma_cross` / `macd_hist` / `stub`). Unknown adapter → stub. Extra ingest fields are ignored.

IDs: `MIX-TV-EP-001`… never `STRAT-015+`. KEEP_ALL `STRAT-001`–`014`.

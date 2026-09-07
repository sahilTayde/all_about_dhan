# CF overnight pause — 2026-09-07

## Status
- **Inventory A:** done (`1a44f2b` — Chart Fanatics overnight triage + sibling queues).
- **ASR / BIND / BT agents:** stopped on Cursor monthly usage limit.
- **Queues remain for resume** (do not delete).

## Resume queue paths
- `data/recon/cf_overnight_queue_openai_bind.json`
- `data/recon/cf_overnight_queue_backtest.json`
- `data/recon/cf_overnight_queue_transcript_retry.json`
- Sibling rollups / per-guest overnight JSON under `data/recon/CF_OVERNIGHT_*_2026-09-07.*`
- Inventory: `data/recon/CF_OVERNIGHT_INVENTORY_2026-09-07.md` (+ `.json`)

## Left-off
Founder continues later after usage limit resets. Checkpoint commit saves CF overnight progress + Okala/simple signal path code/docs before pause.

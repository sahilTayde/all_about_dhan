# UI no signals — review snippet (2026-09-07)

Founder: UI not giving signals → capture evidence for later testing.

**Evidence pack:** [`data/recon/UI_NO_SIGNAL_REVIEW_2026-09-07.md`](../../../data/recon/UI_NO_SIGNAL_REVIEW_2026-09-07.md) + folder `data/recon/ui_no_signal_2026-09-07/`.

**Root causes (short):**
1. HOLD → UI `WAITING FOR NEXT SIGNAL` (desk up; not a Vite outage).
2. Day SIGNAL ledger all HOLD/VETOED — NEWS_DAY / MACRO_EVENT hold ticket + fixture cited news.
3. After 15:00 IST MIX-CLOCK-CAS dead-band; after 15:30 outside shell.
4. Premium LTP unbound → Entry/SL/Target `DATA_INSUFFICIENT`.
5. OpenAI `APIConnectionError` / hung ticks — PAPER `--use-llm --live-chain` restarted (orders refused). Still `non_hold_signals=0`.

**Canvas attention:** `data/recon/paper_attention_bugs.json` updated with “UI no signals — evidence captured”.

PAPER only · NO_PROMOTE · orders refused · gate not set.

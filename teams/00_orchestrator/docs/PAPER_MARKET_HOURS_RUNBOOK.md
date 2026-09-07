# Runbook — market-hours paper agents (IST)

**Status:** PAPER only · **NO_PROMOTE** · not `RESEARCH_READY_FOR_PROGRAMMING`  
**Package:** `packages/trading_agents_india`  
**Review:** [`open_ai_astra_review.md`](open_ai_astra_review.md)

Never print `.env` secrets. Do not restart npm for this path.

---

## Preconditions

```bash
cd /path/to/all_about_dhan
source .venv/bin/activate   # or your venv
pip install -e packages/trading_agents_india
pip install -e "packages/trading_agents_india[openai]"   # if using LLM
pip install -e packages/agent_rag
pip install -e packages/desk-intel
pip install -e packages/dhan-client
```

- `OPENAI_API_KEY` + `OPENAI_MODEL` (e.g. `gpt-6-astra`) in repo-root `.env` for LLM path.
- `DHAN_*` only needed for `--live-chain` / live charts; empty → fixtures.
- **Orders always refused** (PAPER and LIVE mode).

---

## Session clock

| Window (IST, weekdays) | Behavior |
|------------------------|----------|
| 09:00–09:30 | Shell on; **dead-band HOLD** |
| 09:30–15:00 | Active paper leans allowed |
| 15:00–15:30 | Dead-band HOLD (CAS overlay) |
| outside / weekend | Outside shell |

```bash
python -m trading_agents_india clock
```

---

## Start paper loop

### Closed market / dry (recommended when weekend or verifying)

```bash
python -m trading_agents_india market-hours --simulate --max-ticks 2
```

### Open NSE session (data optional)

Market-hours defaults when flags omitted:

- `--use-llm` **on** if `OPENAI_API_KEY` present (override with `--no-llm`)
- `--prefer-desk` **on** (override `--no-prefer-desk`) — soft/pre-market sentiment; **BIG_NEWS only** mid-session veto
- `--gather-news` **off** (pre-market owns news gather; pass `--gather-news` only if founder wants mid-session soft context)
- `--live-chain` **off** (pass explicitly to try Dhan chain/premium)
- tick floor **≥90s** when LLM is on (P0-4)

```bash
python -m trading_agents_india market-hours \
  --max-ticks 8 \
  --tick-seconds 90 \
  --stop-outside-shell \
  --live-chain
```

Rules-only (no OpenAI calls):

```bash
python -m trading_agents_india market-hours --simulate --no-llm --max-ticks 1
```

Single shot (not the poll loop):

```bash
python -m trading_agents_india session --dry-run --use-llm --prefer-desk --gather-news
```

---

## Artifacts

| Artifact | Path |
|----------|------|
| Agent KB | `data/knowledge/trading_agents_india.sqlite` |
| Paper watch | `data/recon/paper_watch/MIX-TA-*/YYYY-MM-DD.jsonl` |
| RAG store | `data/knowledge/agent_rag.sqlite` (never writes `transcripts.sqlite`) |
| Desk mock | `apps/web/public/mock/paper_agents.json` (not a live wire) |

---

## EOD recon (cron-friendly)

Idempotent stub; **does not** auto-retune; `RETUNE_PROPOSAL` stays `BACKTEST_REQUIRED`.

```bash
# After session / post-market
python -m agent_rag eod-recon --offline
# alias:
python -m desk_intel eod-recon --offline

# Optional rollup (still NO_PROMOTE):
python -m agent_rag paper-backtest --day YYYY-MM-DD
```

### Example crontab (IST machine; adjust paths)

```cron
# Weekdays ~15:45 IST — EOD recon stub
15 15 * * 1-5 cd /path/to/all_about_dhan && .venv/bin/python -m agent_rag eod-recon --offline >> /tmp/aad_eod.log 2>&1
```

Do **not** schedule live order jobs.

---

## Live-chain (opt-in data only)

```bash
python -m trading_agents_india market-hours --live-chain --max-ticks 2 --stop-outside-shell
```

- Tries Dhan option chain + OPTIDX / index charts via `dhan-client`.
- Failures → fixtures + `DATA_INSUFFICIENT` gaps.
- **Does not** place, modify, or cancel orders.
- Rate limits: [`packages/dhan-client/docs/RATE_LIMITS.md`](../../../packages/dhan-client/docs/RATE_LIMITS.md).

---

## Hard stops

- No `/alerts/orders`. No promote. No win-rate claims from this runbook.
- KEEP_ALL STRAT-001–014.
- Depth alpha remains PARKED / DI (`hooks/depth.py`).

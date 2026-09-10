# Cheap counsel LLMs (OpenAI + Gemini)

**Date:** 2026-09-09  
**Policy:** PAPER / review / validation only. Never print keys. No live orders.

## What we use (cost-first)

| Job | Provider | Model | Why |
|-----|----------|-------|-----|
| Default counsel, confirm, classify | Gemini | `gemini-3.5-flash-lite` | Cheapest Google id that answered 200 on this key |
| Fallback / OpenAI-shaped JSON | OpenAI | `gpt-5.4-nano` | Already in paper agents (`llm.py`) |
| Harder review (optional) | Gemini | `gemini-3.6-flash` | Set `GEMINI_MODEL` only when lite is not enough |

Do **not** default to Pro / thinking-max models. This desk is general reasoning, not a coding-max bill.

## Env (`.env`, gitignored)

- `OPENAI_API_KEY` + `OPENAI_MODEL=gpt-5.4-nano`
- `GEMINI_KEY` + `GEMINI_MODEL=gemini-3.5-flash-lite`
- `COUNSEL_PROVIDER=both` — **always ask Gemini and OpenAI the same brief** (default)

Cloud: same **names** as secrets. Never paste values into chat.

## How agents call it

```bash
.venv/bin/python -c "from trading_agents_india.counsel import ping, complete; print(ping()['gemini']['ok'], ping()['openai']['ok'])"
```

`complete(prompt, role="review", facts="...")` — pass **cited** web/desk notes in `facts`.  
This module does **not** scrape Google. Latest tape/news = Dhan gather + desk_intel RSS + Cursor web tools, then counsel.

## Job templates (Cursor codes; Gemini/OpenAI reason)

Cursor picks a **job_id**, fills **slots** from gather/docs, then calls Gemini (lite) / OpenAI (nano).

| job_id | Use when | Details to collect |
|--------|----------|-------------------|
| `SIGNAL_REVIEW` | Review **our** call (never generate CE/PE) | our_call, our_why, cited tape, MIX/STRAT, session |
| `VALIDATE_GATHER` | DI / veto storm | what we have vs what the recipe asks |
| `CONFIRM_STAGE` | Want CONFIRMED | current stage, 5m ST/MACD fact, 007/009 clock |
| `REVIEW_NOTES` | Second opinion | what changed, KEEP_ALL, promote claimed? |
| `WEB_FACT_PACK` | Need latest public context | question + already_have → search list only |
| `DHANHQ_BIND` | New @DhanHQ video | video id, spoken TF, buy/sell said, indicators |
| `DHAN_API_REVIEW` | New HQ path / TF / skill script | path or SDK method, claimed fields, desk_use |
| `COUNSEL_NEXT` | Unsure | left_off + gate |

```bash
.venv/bin/python -m trading_agents_india counsel-job --list
.venv/bin/python -m trading_agents_india counsel-job --route "review our HOLD reasoning" --dry
.venv/bin/python -m trading_agents_india counsel-job --job SIGNAL_REVIEW \
  --slot underlying=NIFTY --slot our_call="HOLD WATCH" \
  --slot our_why="PCR without priced wall" \
  --slot cited_tape="INDEX last only; no ATM LTP"
```

Router: `route_job("free text")` in `counsel_jobs.py`. Empty required slots stay `DATA_INSUFFICIENT` — models must not invent tape.

**Together:** `complete()` / `run_job()` return a `panel` (`gemini` + `openai`) and `together` = `ALIGNED` | `SPLIT` | `ONE_ONLY`. Cursor compares; coding stays local unless founder asks to counsel.

## Not claimed

Win rates, fills, Dhan quotes. `DATA_INSUFFICIENT` if facts are missing.

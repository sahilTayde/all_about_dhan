# How the founder's Gemini session worked — desk learning (2026-09-10)

**Layer:** `VALIDATION` on the transcript facts, `HYPOTHESIS` on everything we build from it.
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. PAPER only. NO_PROMOTE. No live orders.

Sources (tracked here):

- [`GEMINI_SKILL.md`](GEMINI_SKILL.md) — the founder's OpenAI-written skill (v1.0) used as Gemini system prompt.
- [`gemini_skill_config.json`](gemini_skill_config.json) — v1.1 production config (threshold 75, 1m–1h TFs).
- [`transcript_2026-09-09_founder_session.txt`](transcript_2026-09-09_founder_session.txt) — full NIFTY 23600 PE session.
- `today_gemini_reply_laerning.txt` at repo root was **empty (0 bytes)** when read — nothing to learn from it yet.

## 1. What Gemini actually did (SOURCE_FACT from transcript)

Gemini did **not** fetch any data. The founder's browser tab (Dhan web charts) showed
everything, and Gemini read the screen each time the founder asked. Per reply it consumed:

| Input | Where it came from |
|---|---|
| Spot LTP, change | Dhan chart header |
| Option 5m OHLC bar of `NIFTY 15 SEP 23600 PE` | premium chart |
| SuperTrend(10,3) value + flip color | founder's chart indicator |
| Session VWAP (spot AND option, each its own) | chart indicator |
| EMA9 (spot AND option, each its own) | chart indicator |
| Dhan RSI(9) + signal line | chart indicator |
| Order-flow delta: per-cluster net delta, cumulative delta, total buy/sell volume | Dhan order-flow pane |
| Founder position (avg 130.00) | founder typed it |

Then it emitted the same 3-part shape every time:

1. **Snapshot narrative** — restated the numbers it could see (no invention).
2. **Strict JSON** — the §68 schema from `GEMINI_SKILL.md` (decision, entry/stop/targets, RR, primary_reason, invalidation, status).
3. **Simple execution plan** — position-aware coaching in plain words.

## 2. Why it felt "perfect" (honest read)

- Almost every reply was **risk coaching, not a fresh signal**: DO_NOT_AVERAGE, EXIT_PE_STOP_LOSS,
  NO_TRADE_PE, STAY_OUT_PUTS, EXIT_ON_PULLBACK. Only one WAIT_FOR_EMA_CONFIRMATION setup, and even
  that demanded a 5m close above a level before entry. The skill optimizes for **avoiding bad trades** —
  and on a day where the founder was holding a losing PE, "don't average, exit into bounces, hard stop
  113.50" was exactly right.
- **Dual-chart confirmation rule** carried every call: spot vs *its own* VWAP/EMA9 **and** the
  option premium vs *its own* VWAP/EMA9 must agree before an entry, and the order-flow delta must not
  contradict. This is the same family as our `MIX-DUAL-INDEX-MASTER` premium+spot gate.
- Every reply had an **invalidation** and a **trigger** ("no PE until spot < 23,518 AND PE reclaims
  125.80 on positive delta"). Signals could never silently stay alive.
- **Position-aware**: once the founder said "my avg is 130", targets became loss-minimisation exits
  and Gemini said so explicitly when the founder caught the 130-entry/128-target oddity.
- Caveat the desk must keep: confidence 88–98 in the transcript is **evidence alignment, not win
  probability** (skill §70), and one good afternoon is **not** a validated edge. No promote from this.

## 3. Gap table — can our stack source the same inputs from DhanHQ?

| Gemini input | Dhan API path | Verdict |
|---|---|---|
| Spot 1m/5m OHLC | `/charts/intraday` (1/5/15/25/60) + WS INDEX | **HAVE** (warehouse) |
| Option premium tape | chain LTP (1/3s per unique) or WS Full on option `security_id` | **PARTIAL** — we poll ATM LTP; no rolling premium OHLC persisted yet (same blocker as MIX-DUAL) |
| Premium VWAP / EMA9 / RSI / SuperTrend | computed by us from premium OHLC | **CAN BUILD** once premium bars persist |
| Spot VWAP | INDEX has no traded volume — skill §19 itself says prefer futures VWAP | FUTIDX VWAP via WS quote/REST; INDEX "VWAP" = PROJECT proxy only |
| Order-flow per-cluster delta / cumulative delta | **no Dhan REST/WS surface for aggressor-side delta**; WS quote gives LTQ, volume, total buy/sell *pending* qty | **DATA_INSUFFICIENT** — nearest is a tick-rule proxy (PROJECT-DERIVED, must be labeled) |
| Dhan RSI(9) values | not an API; chart-only | compute ourselves |
| Founder position | our paper ledger | HAVE |

00 call: we do **not** pretend to have order-flow delta. The JSON carries
`"order_flow": {"status": "UNAVAILABLE"}` exactly as skill §28 requires, until/unless a real surface exists.

## 4. What the desk adopts (paper only)

1. **The output contract** — a desk version of the §68 strict JSON schema
   (`trading_agents_india/signal_schema.py`, `DESK_SIGNAL_JSON v1`), built from `PaperTicket`, so the
   web app renders signals from JSON instead of prose. Nulls for anything unsourced; `data_quality.missing_fields` honest.
2. **The dual-chart rule** as the stated confirmation hierarchy (spot vs own indicators + premium vs own
   indicators) — already the direction of `MIX-DUAL-INDEX-MASTER`.
3. **Invalidation + valid_until on every ticket** — no silently-alive signals.
4. **Two-pass discipline** (§49 trade case vs invalidation case) mapped onto our bull/bear summaries.
5. **NO_TRADE is a first-class product answer** (§59: 5 excellent > 30 mediocre).

What we do **not** adopt: treating the transcript's confidence numbers as probabilities, claiming
order-flow reads we cannot source, or promoting anything without 06 OOS + 09 five-pass.

Counsel review loops on this spec: [`COUNSEL_SIGNAL_FORMAT_2026-09-10.md`](../../../00_orchestrator/docs/COUNSEL_SIGNAL_FORMAT_2026-09-10.md).

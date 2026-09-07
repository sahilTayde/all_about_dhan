# Chart Fanatics — Overnight Inventory & Triage

**As of:** 2026-09-07 (overnight workstream A — inventory/queues only)
**Channel:** `@chart-fanatics` · `UC2GyeAMRDA4cRIiISejML2g`
**Layer:** `SOURCE_FACT` inventory · India-portable = **HYPOTHESIS guess**
**Gates:** PAPER · NO_PROMOTE · no STRAT-015+ · MIX-CF-* only · never print secrets

## Counts

| Bucket | Count |
|--------|------:|
| total | 47 |
| transcript_ok | 18 |
| transcript_fail | 29 |
| existing_bind | 16 |
| existing_mix | 16 |
| skip | 0 |
| queued_transcript_retry | 29 |
| queued_openai_bind | 2 |
| queued_backtest | 16 |

## Queues (sibling handoff)

| Queue file | Count | Owner job |
|------------|------:|-----------|
| `data/recon/cf_overnight_queue_transcript_retry.json` | 29 | ASR (whisper); start `xUyqIjCfZzg` |
| `data/recon/cf_overnight_queue_openai_bind.json` | 2 | OpenAI suggest + BIND (Phase-11 Yush/Marco return) |
| `data/recon/cf_overnight_queue_backtest.json` | 16 | 06 proxy / India adaptation BT (NO_PROMOTE) |

## Skip policy

- **Hard skip only** when terminology cannot map to Indian index options **even with alternatives**.
- Prefer alts: PDH→prev day high · PDL→prev day low · FVG→imbalance/gap · OF/DOM→PARKED (structure proxy only) · US short→PE · gap-up short→gap-fade PE · fear→India VIX/PCR.
- **This pass hard skips: 0.** Psychology (`8HxT9WQ-uD0`) = `process_only` (still ASR-queued at P3), not a strategy skip.
- Do **not** invent BIND content here; siblings own BIND bodies.

## Full table

| # | Views | ID | Title (short) | Transcript | BIND? | MIX? | India-portable guess | Priority | Queue | Skip reason |
|--:|------:|----|---------------|------------|-------|------|----------------------|----------|-------|-------------|
| 1 | 4,028,375 | `tvERE-Beu2U` | Trading LIVE with the #1 Scalper in the WORLD (EXTRE… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 2 | 1,272,415 | `DAnXM7C16h0` | STEAL This EASY Liquidity TRAP Trading Strategy - $5… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 3 | 1,010,712 | `coBMd1vk2Lo` | The SIMPLE $10 Million ICT Blueprint They Don’t Want… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 4 | 950,121 | `AVVM-FyewLg` | STEAL This SIMPLE Trading Strategy from The WORLD's … | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 5 | 808,732 | `VTEQ2fhGLqE` | Making $500,000 Using This SIMPLE Futures Strategy -… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 6 | 703,663 | `ADnslyKOwFE` | STEAL This INSANE Simple 90% Win Rate Trading Strate… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 7 | 684,193 | `HNuRp9Z1bMs` | Worlds BEST NQ Scalper Reveals His A+ Trading Strate… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 8 | 620,547 | `IUo5AwmsE9A` | 12 Years of Trading Knowledge in 2 Hours - Umar Ashr… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 9 | 524,494 | `q_MdVlZ1SH4` | The ONE Trading Indicator That Will EXPOSE The Truth… | ok | yes | yes (2) | yes_with_alts | P1 | backtest | — |
| 10 | 458,084 | `UhkRRqO1gQM` | LIVE TRADING - How He Made $40,000+ Trading using Or… | ok | yes | yes (3) | conditional_of | P2 | backtest | — |
| 11 | 454,365 | `8OX-mcSHWhg` | Worlds BEST Prop Firm Trader Reveals SIMPLE Trading … | ok | yes | yes (3) | yes_with_alts | P1 | backtest | — |
| 12 | 388,031 | `6Bdv-_YUQ0s` | Options Trading for Beginners: Super Simple - 2 Hour… | ok | yes | yes (4) | yes | P1 | backtest | — |
| 13 | 377,903 | `yLuH8YZXORQ` | Trading $6,000 to OVER $10+ Million Using This Strat… | ok | yes | yes (5) | yes_with_alts | P1 | backtest | — |
| 14 | 357,442 | `TvoQr6ObjnU` | Trading LIVE with One of the World's BEST Scalpers (… | ok | yes | yes (4) | conditional_of | P2 | backtest | — |
| 15 | 322,585 | `IB-fyWI5j8w` | TAKE This EASY ICT Trading Strategy For Prop Firms (… | ok | yes | yes (4) | yes_with_alts | P1 | backtest | — |
| 16 | 315,988 | `hvyf6frvCcA` | 74% Win Rate Trader Shares His EXACT OrderFlow Strat… | ok | no | no | yes_with_alts | P0 | openai_bind | — |
| 17 | 301,504 | `T_djSNBmV00` | The ONE Liquidity Trading Pattern That Actually Work… | ok | no | no | yes_with_alts | P0 | openai_bind | — |
| 18 | 280,453 | `xUyqIjCfZzg` | Trading LIVE with TWO World Class Order Flow Scalper… | fail | no | no | conditional_of | P0 | transcript_retry | — |
| 19 | 253,169 | `SMSqQTBxjc0` | The ONLY Break And Retest Trading Strategy You’ll EV… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 20 | 251,710 | `jsUTbjwpFVk` | COPY This Prop Firm Simple Trading Strategy with 65%… | ok | yes | yes (8) | yes_adapted | P1 | backtest | — |
| 21 | 238,062 | `Jx5cJ_qb31U` | COPY This CRAZY Simple 98% Win Rate Trading Strategy | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 22 | 230,085 | `PZDWQgtqt2I` | This SIMPLE ICT Futures Trading Strategy Made Her Ov… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 23 | 224,988 | `_qeFh1ADss8` | $100+ Million Trader: His BEST Trading Strategy (Mar… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 24 | 223,438 | `52ZsDmFHqyY` | If You Only Watch One Trading Strategy Video, Make I… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 25 | 223,222 | `jHsD2-2K_Kk` | How To Trade Real Fair Value Gaps with Extreme Accur… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 26 | 219,399 | `SQEtBHOJW6I` | LIVE Trading with a $1M+ Order Flow Trader (INSANE R… | fail | no | no | conditional_of | P0 | transcript_retry | — |
| 27 | 215,127 | `yZpzG8R3Ayk` | PRO Trader Reveals Super Simple Trading Strategy (Ho… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 28 | 210,733 | `WDdvnd9vLbM` | If You Only Watch One Trading Process Video, Make It… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 29 | 206,323 | `YzYDUEUOZ4k` | COPY This EXACT Entry System to Become a Millionaire… | fail | no | no | yes_with_alts | P0 | transcript_retry | — |
| 30 | 184,576 | `VDK200OHNSo` | Trading $50M At 25 Using One SIMPLE Market Cycle Str… | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 31 | 169,465 | `mDNcx2Dhhms` | STEAL This $100 Million Dollar Trading Strategy (Use… | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 32 | 167,098 | `8HxT9WQ-uD0` | Master The Mental Game of Trading In 60 Minutes (STO… | fail | no | no | process_only | P3 | transcript_retry | — |
| 33 | 162,291 | `UIGZtoGGPH4` | If You Only Watch One ICT Trading Video, Make It Thi… | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 34 | 158,828 | `xl4QHqlBCfk` | STEAL This Trading Champion’s Exact Strategy - Math … | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 35 | 157,881 | `TyHTEtArsS4` | Master ALGO Trading In Less Than 90 Minutes (NO Codi… | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 36 | 156,135 | `nMhywubR2xc` | STEAL This 7 Figure Liquidity HACK for Your Trading … | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 37 | 128,365 | `35cyqDz-ej8` | STEAL This INSANE 1-Minute Market Maker Trading Stra… | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 38 | 116,897 | `_wpg45NdMkM` | 20 Years Of Institutional Trading Knowledge In 70 Mi… | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 39 | 116,054 | `9D9ck-ZI6V0` | Trading Made SIMPLE - Use These 3 Specific Steps To … | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 40 | 110,130 | `70UtrLU6RAg` | Verified $5M+ Trader: LIVE Trading Using His EXACT S… | fail | no | no | yes_with_alts | P1 | transcript_retry | — |
| 41 | 93,733 | `EZ_L7zovyrw` | COPY These 3 Simple Steps To Master The TREND Tradin… | fail | no | no | yes_with_alts | P2 | transcript_retry | — |
| 42 | 87,119 | `4BgkLlwgpvo` | Wall Street's EXACT Formula To Measure FEAR In The M… | fail | no | no | yes_with_alts | P2 | transcript_retry | — |
| 43 | 83,488 | `0_NSmOWVbpA` | If You Only Watch ONE Market Cycle Trading Video, Ma… | fail | no | no | yes_with_alts | P2 | transcript_retry | — |
| 44 | 76,895 | `2Ug0jyDvoek` | Simple ONE Candle Trading Strategy Thats Profited Mi… | fail | no | no | yes_with_alts | P2 | transcript_retry | — |
| 45 | 74,264 | `SInAfwX3X3A` | Copy this Complete In-Depth 85%+ Win Rate Short Trad… | fail | no | no | yes_with_alts | P2 | transcript_retry | — |
| 46 | 66,591 | `KkTTCKr-3Ew` | Pass Prop Firms Using This ICT & Orderflow Futures T… | fail | no | no | yes_with_alts | P2 | transcript_retry | — |
| 47 | 47,942 | `EcTRlLYvhXU` | COPY The BEST Gap Up Short Trading Strategy That Has… | fail | no | no | yes_with_alts | P2 | transcript_retry | — |

## MIX detail (bound videos)

- `tvERE-Beu2U` (Fabio Valentini): `MIX-CF-FABIO-TREND-NY`, `MIX-CF-FABIO-MR-RANGE`
- `DAnXM7C16h0` (Marco): `MIX-CF-MARCO-LIQ-TRAP`, `MIX-CF-MARCO-INT-EXT`
- `coBMd1vk2Lo` (Trader Mayne): `MIX-CF-MAYNE-ICT-HTF`, `MIX-CF-MAYNE-BREAKER`
- `AVVM-FyewLg` (Marci Silfrain): `MIX-CF-MARCI-RIZZY`, `MIX-CF-MARCI-BB-REALITY`
- `VTEQ2fhGLqE` (Tori Trades): `MIX-CF-TORI-TL-BOUNCE`, `MIX-CF-TORI-TL-BREAK`
- `ADnslyKOwFE` (TG Capital): `MIX-CF-TG-TRIDENT`, `MIX-CF-TG-EMA-WAVE`
- `HNuRp9Z1bMs` (Trader Kane): `MIX-CF-KANE-EQ50`, `MIX-CF-KANE-PO3-SMT`
- `IUo5AwmsE9A` (Umar Ashraf): `MIX-CF-UMAR-MORNING-TOP`, `MIX-CF-UMAR-OPENING-DRIVE`
- `q_MdVlZ1SH4` (Forest Knight): `MIX-CF-FOREST-VPE-EDGE`, `MIX-CF-FOREST-POC-RETEST`
- `UhkRRqO1gQM` (Carmine Rosato): `MIX-CF-CARMINE-ABSORB`, `MIX-CF-CARMINE-FAIL-BREAK`, `MIX-CF-CARMINE-OPEN-HOLD`
- `8OX-mcSHWhg` (Jadecap): `MIX-CF-JADECAP-SWING-FAIL`, `MIX-CF-JADECAP-SESSION-LIQ`, `MIX-CF-JADECAP-FVG-DRAW`
- `6Bdv-_YUQ0s` (Usman Ashraf): `MIX-CF-USMAN-OI-STRIKE`, `MIX-CF-USMAN-0DTE-GAMMA`, `MIX-CF-USMAN-WEEKLY-SIZE`, `MIX-CF-USMAN-PRICE-STOP`
- `yLuH8YZXORQ` (Brando / Leaf): `MIX-CF-BRANDO-HTF-RECLAIM`, `MIX-CF-BRANDO-ROUND-BREAK`, `MIX-CF-BRANDO-HTF-BOUNCE`, `MIX-CF-BRANDO-SIZE-ZERO`, `MIX-CF-BRANDO-NEWS-ALIGN`
- `TvoQr6ObjnU` (Andrea Cimi): `MIX-CF-ANDREA-FAIL-AUCTION`, `MIX-CF-ANDREA-ORB-ACCEPT`, `MIX-CF-ANDREA-STOP-FADE`, `MIX-CF-ANDREA-ABSORB`
- `IB-fyWI5j8w` (Omor / NBB): `MIX-CF-OMOR-MMM-FRAME`, `MIX-CF-OMOR-OTE`, `MIX-CF-OMOR-PDH-REVERSAL`, `MIX-CF-OMOR-KZ-ADR`
- `jsUTbjwpFVk` (Okala): `MIX-CF-OKALA-8020-LEVEL`, `MIX-CF-OKALA-FORK`, `MIX-CF-OKALA-H-CROSS`, `MIX-CF-OKALA-REPAIR`, `MIX-CF-OKALA-IN-LEVEL`, `MIX-CF-OKALA-IN-FORK`, `MIX-CF-OKALA-IN-H-CROSS`, `MIX-CF-OKALA-IN-REPAIR`

## OpenAI+BIND queue detail

- `hvyf6frvCcA` · Trader Yush · Orderflow strategy title → structure/imbalance alts; OF precision DI until bind
- `T_djSNBmV00` · Marco (return) · Liquidity pattern → raid/reclaim INDEX; keep separate from MIX-CF-MARCO-* until bind

## Transcript-fail ASR queue (views desc)

1. `xUyqIjCfZzg` (280,453) [P0] — conditional_of: Trading LIVE with TWO World Class Order Flow Scalpers (FT Fa
2. `SMSqQTBxjc0` (253,169) [P0] — yes_with_alts: The ONLY Break And Retest Trading Strategy You’ll EVER Need 
3. `Jx5cJ_qb31U` (238,062) [P0] — yes_with_alts: COPY This CRAZY Simple 98% Win Rate Trading Strategy
4. `PZDWQgtqt2I` (230,085) [P0] — yes_with_alts: This SIMPLE ICT Futures Trading Strategy Made Her Over $100,
5. `_qeFh1ADss8` (224,988) [P0] — yes_with_alts: $100+ Million Trader: His BEST Trading Strategy (Market Wiza
6. `52ZsDmFHqyY` (223,438) [P0] — yes_with_alts: If You Only Watch One Trading Strategy Video, Make It This
7. `jHsD2-2K_Kk` (223,222) [P0] — yes_with_alts: How To Trade Real Fair Value Gaps with Extreme Accuracy - Ca
8. `SQEtBHOJW6I` (219,399) [P0] — conditional_of: LIVE Trading with a $1M+ Order Flow Trader (INSANE RESULTS)
9. `yZpzG8R3Ayk` (215,127) [P0] — yes_with_alts: PRO Trader Reveals Super Simple Trading Strategy (How The Ma
10. `WDdvnd9vLbM` (210,733) [P0] — yes_with_alts: If You Only Watch One Trading Process Video, Make It This
11. `YzYDUEUOZ4k` (206,323) [P0] — yes_with_alts: COPY This EXACT Entry System to Become a Millionaire Trader
12. `VDK200OHNSo` (184,576) [P1] — yes_with_alts: Trading $50M At 25 Using One SIMPLE Market Cycle Strategy (4
13. `mDNcx2Dhhms` (169,465) [P1] — yes_with_alts: STEAL This $100 Million Dollar Trading Strategy (Used by Mar
14. `8HxT9WQ-uD0` (167,098) [P3] — process_only: Master The Mental Game of Trading In 60 Minutes (STOP TILT/F
15. `UIGZtoGGPH4` (162,291) [P1] — yes_with_alts: If You Only Watch One ICT Trading Video, Make It This (LIVE 
16. `xl4QHqlBCfk` (158,828) [P1] — yes_with_alts: STEAL This Trading Champion’s Exact Strategy - Math Based Mo
17. `TyHTEtArsS4` (157,881) [P1] — yes_with_alts: Master ALGO Trading In Less Than 90 Minutes (NO Coding) / $1
18. `nMhywubR2xc` (156,135) [P1] — yes_with_alts: STEAL This 7 Figure Liquidity HACK for Your Trading (Any Ass
19. `35cyqDz-ej8` (128,365) [P1] — yes_with_alts: STEAL This INSANE 1-Minute Market Maker Trading Strategy (75
20. `_wpg45NdMkM` (116,897) [P1] — yes_with_alts: 20 Years Of Institutional Trading Knowledge In 70 Minutes ($
21. `9D9ck-ZI6V0` (116,054) [P1] — yes_with_alts: Trading Made SIMPLE - Use These 3 Specific Steps To Master A
22. `70UtrLU6RAg` (110,130) [P1] — yes_with_alts: Verified $5M+ Trader: LIVE Trading Using His EXACT Strategy
23. `EZ_L7zovyrw` (93,733) [P2] — yes_with_alts: COPY These 3 Simple Steps To Master The TREND Trading Future
24. `4BgkLlwgpvo` (87,119) [P2] — yes_with_alts: Wall Street's EXACT Formula To Measure FEAR In The Markets (
25. `0_NSmOWVbpA` (83,488) [P2] — yes_with_alts: If You Only Watch ONE Market Cycle Trading Video, Make It Th
26. `2Ug0jyDvoek` (76,895) [P2] — yes_with_alts: Simple ONE Candle Trading Strategy Thats Profited Millions (
27. `SInAfwX3X3A` (74,264) [P2] — yes_with_alts: Copy this Complete In-Depth 85%+ Win Rate Short Trading Stra
28. `KkTTCKr-3Ew` (66,591) [P2] — yes_with_alts: Pass Prop Firms Using This ICT & Orderflow Futures Trading S
29. `EcTRlLYvhXU` (47,942) [P2] — yes_with_alts: COPY The BEST Gap Up Short Trading Strategy That Has Made Mi

## HANDOFF

```text
Accepted: Full CF catalog triage (47); queues written; hard_skip=0; alts preferred.
Rejected: Editing sibling BIND bodies; STRAT-015+; clubbing Yush/Marco-return into prior MIX; promoting title WR.
UNKNOWN: True OF/DOM India fields; IST killzone maps; whether any fail-title is crypto-only after ASR.
Next: Sibling ASR from xUyqIjCfZzg; Phase-11 OpenAI+BIND for hvyf6frvCcA + T_djSNBmV00; BT queue = existing MIX-CF-*.
```

## JSON twin

`data/recon/CF_OVERNIGHT_INVENTORY_2026-09-07.json`


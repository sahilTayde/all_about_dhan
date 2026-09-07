# Chart Fanatics — Channel Inventory (Phase 1)

**Retrieved:** 2026-09-07 (Okala ASR + bind); prior inventory stamp 2026-09-06T18:26:37Z  
**Layer:** `SOURCE_FACT` (channel metadata + caption fetch status). Education ≠ edge. **Not** DHAN-DERIVED.  
**Phase:** 1 inventory + 2 Fabio bind + Phase-4–10 binds; Phase-3 captions **0** (429); **Phase-3B–3I ASR** sixteen videos; **Phase-3J ASR+bind** `jsUTbjwpFVk` (Okala). See `PHASE3J_ASR_LOG.md`.

## Channel

| Field | Value |
|-------|-------|
| Name | Chart Fanatics |
| Handle | `@chart-fanatics` |
| Channel ID | `UC2GyeAMRDA4cRIiISejML2g` |
| URL (vanity) | https://www.youtube.com/@chart-fanatics |
| URL (canonical) | https://www.youtube.com/channel/UC2GyeAMRDA4cRIiISejML2g |

## Priority ~3h / ~4M-view LIVE

| Field | Value |
|-------|-------|
| Video ID | `tvERE-Beu2U` |
| Title | Trading LIVE with the #1 Scalper in the WORLD (EXTREME Accuracy) |
| Duration | 3h34m10s (`PT3H34M10S`) |
| Views (API) | 4,028,375 |
| Published | 2025-09-21T14:01:33Z |
| Guest | Fabio Valentini (ASR variants noted in MD) |
| URL | https://www.youtube.com/watch?v=tvERE-Beu2U |
| Transcript | **yes** (`full`) |
| Readable MD | `teams/01_research/docs/chart_fanatics/tvERE-Beu2U_TRANSCRIPT.md` |
| Raw | `data/transcripts/external_chart_fanatics/tvERE-Beu2U.en.txt` (+ `.txt` / `.json`) |


## Phase-3 caption retry (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Gentle serial retry; skip `tvERE-Beu2U` |
| Successes | **0** new caption transcripts |
| Stop | Repeated **HTTP 429** on timedtext / yt-dlp android subs (IpBlocked on transcript-api) |
| Log | [`PHASE3_RETRY_LOG.md`](PHASE3_RETRY_LOG.md) |
| Fetch JSON | `data/transcripts/external_chart_fanatics/_phase3_fetch_results.json` |
| Attempted IDs | `DAnXM7C16h0`, `coBMd1vk2Lo`, `AVVM-FyewLg`, `VTEQ2fhGLqE` (all **fail** captions) |

## Phase-3B ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Top-2 view videos only; audio → faster-whisper (no timedtext hammer) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3B_ASR_LOG.md`](PHASE3B_ASR_LOG.md) |
| IDs | `DAnXM7C16h0` (Marco), `coBMd1vk2Lo` (Trader Mayne) |

## Phase-3C ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Next-2 view fails after 3B; audio → faster-whisper (no timedtext hammer) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3C_ASR_LOG.md`](PHASE3C_ASR_LOG.md) |
| IDs | `AVVM-FyewLg` (Marci Silfrain), `VTEQ2fhGLqE` (Tori Trades) |

## Phase-3D ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Next-2 view fails after 3C; audio → faster-whisper (no timedtext hammer) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3D_ASR_LOG.md`](PHASE3D_ASR_LOG.md) |
| IDs | `ADnslyKOwFE` (TG Capital), `HNuRp9Z1bMs` (Trader Kane) |

## Phase-3E ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Next **2** highest-view fail videos; audio → faster-whisper (no timedtext hammer; **no MIX**) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3E_ASR_LOG.md`](PHASE3E_ASR_LOG.md) |
| IDs | `IUo5AwmsE9A` (Umar Ashraf), `q_MdVlZ1SH4` (Forest Knight) |


## Phase-3F ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Next **2** highest-view fail videos; audio → faster-whisper (no timedtext hammer; **no MIX**) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3F_ASR_LOG.md`](PHASE3F_ASR_LOG.md) |
| IDs | `UhkRRqO1gQM` (Carmine Rosato), `8OX-mcSHWhg` (Jadecap) |



## Phase-3G ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Next **2** highest-view fail videos after 3F; audio → faster-whisper (no timedtext hammer; **no MIX**) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3G_ASR_LOG.md`](PHASE3G_ASR_LOG.md) |
| IDs | `6Bdv-_YUQ0s` (Usman Ashraf), `yLuH8YZXORQ` (Brando / Leaf) |



## Phase-3H ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Next **2** highest-view fail videos after 3G; audio → faster-whisper (no timedtext hammer; **no MIX**) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3H_ASR_LOG.md`](PHASE3H_ASR_LOG.md) |
| IDs | `TvoQr6ObjnU` (Andrea Cimi), `IB-fyWI5j8w` (Omor / NBB Trader) |


## Phase-3I ASR ingest (2026-09-06)

| Field | Value |
|-------|-------|
| Scope | Next **2** highest-view fail videos after 3H; audio → faster-whisper (no timedtext hammer; **no MIX**) |
| Successes | **2** full ASR transcripts |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU |
| Log | [`PHASE3I_ASR_LOG.md`](PHASE3I_ASR_LOG.md) |
| IDs | `hvyf6frvCcA` (Trader Yush), `T_djSNBmV00` (Marco return) |

## Phase-3J ASR + bind (2026-09-07)

| Field | Value |
|-------|-------|
| Scope | Founder ask: retry **`jsUTbjwpFVk`** (prop firm 65% title) → ASR → BIND → `MIX-CF-OKALA-*` |
| Successes | **1** full ASR transcript + BIND + 4 catalog MIX rows |
| Tool | `ASR_WHISPER` / faster-whisper `base` int8 CPU (yt-dlp android fmt 18 → m4a) |
| Log | [`PHASE3J_ASR_LOG.md`](PHASE3J_ASR_LOG.md) |
| Guest | **Okala** (description; ASR O'Cala) |
| MIX | `MIX-CF-OKALA-8020-LEVEL` / `FORK` / `H-CROSS` / `REPAIR` — **catalog only** (no 06 evaluator) |
| Honesty | Title 65% / spoken 70% / mid-low 70s = **claims only** · **NO_PROMOTE** |

## Playlists (yt-dlp `@chart-fanatics/playlists`)

| Playlist ID | Title |
|-------------|-------|
| `PL4FW4rvi8tCGq0AoEbysGuKWHe7ntcFgZ` | Chart Fanatics - Prop Firm Traders |
| `PL4FW4rvi8tCFsRIBBDqDi7rGQcKsq5IXS` | Chart Fanatics - Crypto |
| `PL4FW4rvi8tCFURm-u5PuVFp5Hk1D5oU7L` | Chart Fanatics - Psychology |
| `PL4FW4rvi8tCGI0Oq_jth4LcmHcllh8YPO` | Chart Fanatics - LIVE Trading |
| `PL4FW4rvi8tCGGk9fTRSxiOB83Mjl8Rlia` | Chart Fanatics - Orderflow & Tape Reading |
| `PL4FW4rvi8tCF7PngflRwLwjc5SGnm9OEx` | Chart Fanatics - Scalping |
| `PL4FW4rvi8tCG9C_TFSoWTuCMQaOm9Vj-F` | Chart Fanatics - Day Trading |
| `PL4FW4rvi8tCFbCKiT0ElaxwJcdAb3TCBF` | Chart Fanatics - Short Selling Strategies |
| `PL4FW4rvi8tCESTB0zWaGc-83U87iHJZSh` | Chart Fanatics - Swing Trading |
| `PL4FW4rvi8tCGD2NZ7r1GL_v7dCRvUjl89` | Chart Fanatics - Liquidity |
| `PL4FW4rvi8tCF7vk8ImHO911mHKCHRfKHs` | Chart Fanatics - Forex & CFDs |
| `PL4FW4rvi8tCFn5jijWAVRk4TbWVRNBiMy` | Chart Fanatics - Support & Resistance | Break & Retest |
| `PL4FW4rvi8tCHGq8PObeZ9sicdCSijb8Iz` | Chart Fanatics - ICT Concepts |
| `PL4FW4rvi8tCFLJgH1hPrmbU3NZgFVEiIY` | Chart Fanatics - Options |
| `PL4FW4rvi8tCF5zvVeCiIeV8XK2EkKm35D` | Chart Fanatics - Stocks |
| `PL4FW4rvi8tCGIX3SXiMKlUwN78cbuRZyh` | Chart Fanatics - Futures |

## Caption fetch blockers (this host)

- Prior subagents (`6d38c6f5…`, `1ca7fc0a…`): stopped with “no progress” (mandate too large); timedtext **IP 429** noted on research host.
- This Phase-1 turn: `youtube-transcript-api` → **`IpBlocked`** for all re-fetches; priority kept from existing on-disk full transcript.
- `yt-dlp --write-auto-subs` (android client): subtitle list OK, download **`HTTP 429 Too Many Requests`**. Other clients: reload / unsupported / unavailable.
- `yt-dlp` was missing initially; installed `yt-dlp==2025.10.14` via `pip3 --user`.

## Videos attempted this catalog (47)

Status: `yes` = caption text on disk; `fail` = attempted, no caption body; `partial` unused; skip rows = metadata stub only (capacity / IP block).

| Views | Duration | Status | Video ID | Title | Reason / path |
|------:|----------|--------|----------|-------|---------------|
| 4,028,375 | 3h34m10s | yes | `tvERE-Beu2U` | Trading LIVE with the #1 Scalper in the WORLD (EXTREME Accuracy) | `tvERE-Beu2U_TRANSCRIPT.md` + raw `.en.txt` |
| 1,272,415 | 1h49m37s | yes | `DAnXM7C16h0` | STEAL This EASY Liquidity TRAP Trading Strategy - $500K+ (PERFECT Snip | Phase-3B **ASR** `DAnXM7C16h0_TRANSCRIPT.md` + audio/m4a (captions still 429)|
| 1,010,712 | 1h00m28s | yes | `coBMd1vk2Lo` | The SIMPLE $10 Million ICT Blueprint They Don’t Want You To See (Forex | Phase-3B **ASR** `coBMd1vk2Lo_TRANSCRIPT.md` + audio/m4a (captions still 429)|
| 950,121 | 1h23m30s | yes | `AVVM-FyewLg` | STEAL This SIMPLE Trading Strategy from The WORLD's #2 Futures Trader  | Phase-3C **ASR** `AVVM-FyewLg_TRANSCRIPT.md` + audio/m4a (captions still 429)|
| 808,732 | 1h11m24s | yes | `VTEQ2fhGLqE` | Making $500,000 Using This SIMPLE Futures Strategy - Tori Trades (Simp | Phase-3C **ASR** `VTEQ2fhGLqE_TRANSCRIPT.md` + audio/m4a (captions still 429)|
| 703,663 | 48m16s | yes | `ADnslyKOwFE` | STEAL This INSANE Simple 90% Win Rate Trading Strategy (1:20+ RR) - TG | Phase-3D **ASR** `ADnslyKOwFE_TRANSCRIPT.md` (TG Capital) |
| 684,193 | 1h14m44s | yes | `HNuRp9Z1bMs` | Worlds BEST NQ Scalper Reveals His A+ Trading Strategy | Phase-3D **ASR** `HNuRp9Z1bMs_TRANSCRIPT.md` (Trader Kane) |
| 620,547 | 1h59m05s | yes | `IUo5AwmsE9A` | 12 Years of Trading Knowledge in 2 Hours - Umar Ashraf | Phase-3E **ASR** `IUo5AwmsE9A_TRANSCRIPT.md` + audio/m4a (captions still 429) |
| 524,494 | 1h23m03s | yes | `q_MdVlZ1SH4` | The ONE Trading Indicator That Will EXPOSE The Truth About The Markets | Phase-3E **ASR** `q_MdVlZ1SH4_TRANSCRIPT.md` + audio/m4a (captions still 429) |
| 458,084 | 3h42m20s | yes | `UhkRRqO1gQM` | LIVE TRADING - How He Made $40,000+ Trading using OrderFlow (Full Mast | Phase-3F **ASR** `UhkRRqO1gQM_TRANSCRIPT.md` + audio/m4a (captions still 429) |
| 454,365 | 1h28m23s | yes | `8OX-mcSHWhg` | Worlds BEST Prop Firm Trader Reveals SIMPLE Trading Strategy - Jadecap | Phase-3F **ASR** `8OX-mcSHWhg_TRANSCRIPT.md` + audio/m4a (captions still 429) |
| 388,031 | 1h59m54s | yes | `6Bdv-_YUQ0s` | Options Trading for Beginners: Super Simple - 2 Hour FREE Course | Phase-3G **ASR** `6Bdv-_YUQ0s_TRANSCRIPT.md` + audio/m4a (captions still 429) |
| 377,903 | 1h06m50s | yes | `yLuH8YZXORQ` | Trading $6,000 to OVER $10+ Million Using This Strategy | Phase-3G **ASR** `yLuH8YZXORQ_TRANSCRIPT.md` + audio/m4a (captions still 429) |
| 357,442 | 5h41m15s | yes | `TvoQr6ObjnU` | Trading LIVE with One of the World's BEST Scalpers (PERFECT Sniper Ent | Phase-3H **ASR** `TvoQr6ObjnU_TRANSCRIPT.md` + audio/m4a (captions still 429; guest **Andrea Cimi**, not Fabio) |
| 322,585 | 1h21m53s | yes | `IB-fyWI5j8w` | TAKE This EASY ICT Trading Strategy For Prop Firms (INSANE Entries) | Phase-3H **ASR** `IB-fyWI5j8w_TRANSCRIPT.md` + audio/m4a (captions still 429; guest **Omor / NBB**) |
| 315,988 | 1h33m10s | yes | `hvyf6frvCcA` | 74% Win Rate Trader Shares His EXACT OrderFlow Strategy ($2M+ Payouts) | Phase-3I **ASR** `hvyf6frvCcA_TRANSCRIPT.md` + audio/m4a (captions still 429; guest **Trader Yush**) |
| 301,504 | 1h11m22s | yes | `T_djSNBmV00` | The ONE Liquidity Trading Pattern That Actually Works (Precise Entries | Phase-3I **ASR** `T_djSNBmV00_TRANSCRIPT.md` + audio/m4a (captions still 429; guest **Marco** return) |
| 280,453 | 3h49m38s | fail | `xUyqIjCfZzg` | Trading LIVE with TWO World Class Order Flow Scalpers (FT Fabio Valent | IpBlocked (youtube-transcript-api); yt-dlp subs 429 |
| 253,169 | 1h28m07s | fail | `SMSqQTBxjc0` | The ONLY Break And Retest Trading Strategy You’ll EVER Need (Step By S | IpBlocked (youtube-transcript-api); yt-dlp subs 429 |
| 251,710 | 1h13m14s | yes | `jsUTbjwpFVk` | COPY This Prop Firm Simple Trading Strategy with 65% Win Rate ($5+ Mil | Phase-3J **ASR** `jsUTbjwpFVk_TRANSCRIPT.md` + BIND + `MIX-CF-OKALA-*` (guest **Okala**; title 65%=marketing) |
| 238,062 | 1h12m19s | fail | `Jx5cJ_qb31U` | COPY This CRAZY Simple 98% Win Rate Trading Strategy | IpBlocked (youtube-transcript-api); yt-dlp subs 429 |
| 230,085 | 1h10m18s | fail | `PZDWQgtqt2I` | This SIMPLE ICT Futures Trading Strategy Made Her Over $100,000 - Tanj | IpBlocked (youtube-transcript-api); yt-dlp subs 429 |
| 224,988 | 1h31m11s | fail | `_qeFh1ADss8` | $100+ Million Trader: His BEST Trading Strategy (Market Wizard) | IpBlocked (youtube-transcript-api); yt-dlp subs 429 |
| 223,438 | 1h07m43s | fail | `52ZsDmFHqyY` | If You Only Watch One Trading Strategy Video, Make It This | IpBlocked (youtube-transcript-api); yt-dlp subs 429 |
| 223,222 | 1h14m45s | fail | `jHsD2-2K_Kk` | How To Trade Real Fair Value Gaps with Extreme Accuracy - Carmine Rosa | IpBlocked (youtube-transcript-api); yt-dlp subs 429 |
| 219,399 | 2h51m38s | fail | `SQEtBHOJW6I` | LIVE Trading with a $1M+ Order Flow Trader (INSANE RESULTS) | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 215,127 | 1h20m39s | fail | `yZpzG8R3Ayk` | PRO Trader Reveals Super Simple Trading Strategy (How The Markets Real | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 210,733 | 1h24m45s | fail | `WDdvnd9vLbM` | If You Only Watch One Trading Process Video, Make It This | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 206,323 | 1h06m30s | fail | `YzYDUEUOZ4k` | COPY This EXACT Entry System to Become a Millionaire Trader | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 184,576 | 1h40m26s | fail | `VDK200OHNSo` | Trading $50M At 25 Using One SIMPLE Market Cycle Strategy (4 Stages) - | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 169,465 | 57m14s | fail | `mDNcx2Dhhms` | STEAL This $100 Million Dollar Trading Strategy (Used by Market Wizard | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 167,098 | 1h00m54s | fail | `8HxT9WQ-uD0` | Master The Mental Game of Trading In 60 Minutes (STOP TILT/FOMO) | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 162,291 | 1h13m29s | fail | `UIGZtoGGPH4` | If You Only Watch One ICT Trading Video, Make It This (LIVE Trading) | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 158,828 | 2h42m09s | fail | `xl4QHqlBCfk` | STEAL This Trading Champion’s Exact Strategy - Math Based Models for P | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 157,881 | 1h25m00s | fail | `TyHTEtArsS4` | Master ALGO Trading In Less Than 90 Minutes (NO Coding) / $1M+ Profits | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 156,135 | 1h22m07s | fail | `nMhywubR2xc` | STEAL This 7 Figure Liquidity HACK for Your Trading (Any Asset & Timef | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 128,365 | 2h29m41s | fail | `35cyqDz-ej8` | STEAL This INSANE 1-Minute Market Maker Trading Strategy (75% Win Rate | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 116,897 | 1h11m55s | fail | `_wpg45NdMkM` | 20 Years Of Institutional Trading Knowledge In 70 Minutes ($20M+ AUM) | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 116,054 | 1h06m40s | fail | `9D9ck-ZI6V0` | Trading Made SIMPLE - Use These 3 Specific Steps To Master Any Market | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 110,130 | 2h09m41s | fail | `70UtrLU6RAg` | Verified $5M+ Trader: LIVE Trading Using His EXACT Strategy | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 93,733 | 46m28s | fail | `EZ_L7zovyrw` | COPY These 3 Simple Steps To Master The TREND Trading Futures - Anthon | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 87,119 | 1h38m39s | fail | `4BgkLlwgpvo` | Wall Street's EXACT Formula To Measure FEAR In The Markets (Trade This | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 83,488 | 48m43s | fail | `0_NSmOWVbpA` | If You Only Watch ONE Market Cycle Trading Video, Make It This (500%+  | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 76,895 | 2h05m41s | fail | `2Ug0jyDvoek` | Simple ONE Candle Trading Strategy Thats Profited Millions (80%+ Win R | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 74,264 | 2h17m11s | fail | `SInAfwX3X3A` | Copy this Complete In-Depth 85%+ Win Rate Short Trading Strategy - US  | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 66,591 | 1h45m07s | fail | `KkTTCKr-3Ew` | Pass Prop Firms Using This ICT & Orderflow Futures Trading Strategy ($ | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |
| 47,942 | 1h12m14s | fail | `EcTRlLYvhXU` | COPY The BEST Gap Up Short Trading Strategy That Has Made Millions (Pr | not re-fetched (capacity); stub/IpBlocked from prior — no caption body |

**Counts:** yes=18 · fail=29 · partial=0 · catalogued=47  
**Phase-3:** captions still blocked · **Phase-3B–3J:** 17 promoted to yes via ASR (through Okala `jsUTbjwpFVk`)

### Retry tomorrow (do not drop)

**Locked queue:** [`RETRY_TOMORROW.md`](RETRY_TOMORROW.md) — **29** remaining fail IDs (views-desc) + ASR method. Stub `*_TRANSCRIPT.md` headers ≠ full body. Resume from top (`xUyqIjCfZzg` …). `jsUTbjwpFVk` **removed** (ASR+BIND done).

## Paths

- Readable: `teams/01_research/docs/chart_fanatics/`
- Raw: `data/transcripts/external_chart_fanatics/`
- Fetch log: `data/transcripts/external_chart_fanatics/_phase1_fetch_results.json`
- **Tomorrow retry:** `RETRY_TOMORROW.md`

## HANDOFF

- **Accepted:** Channel ID confirmed; Fabio captions + Phase-3B–3J ASR (**17** ASR + Fabio = **yes=18**); Phase-3J: `jsUTbjwpFVk` (Okala) ASR+BIND+`MIX-CF-OKALA-*` catalog. Inventory yes=18 / fail=29. Fail queue updated in `RETRY_TOMORROW.md`.
- **Rejected:** Claiming remaining guests understood; clubbing CF mixes into STRAT/IQ/prior CF rows; treating ASR as official YouTube captions; treating title 65%/spoken 70% as product WR; wiring Okala into CF×8 evaluator without 06 bind.
- **UNKNOWN / DATA_INSUFFICIENT:** Captions for remaining fail rows (still 429); ASR proper-noun quality; timed VTT; NQ 80/20 → NIFTY digit map.
- **Next:** ASR retry fail=29 per `RETRY_TOMORROW.md`. Phase-11 bind for **Trader Yush** / **Marco** return when asked. Okala = catalog-only until 06 evaluator.


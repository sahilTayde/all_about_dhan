# Stage 1 YouTube run report

Official channel only: [@DhanHQ](https://www.youtube.com/@DhanHQ) / [playlists](https://www.youtube.com/@DhanHQ/playlists).
No secrets. `YOUTUBE_API_KEY` is not recorded here.

## Session 2026-09-01 (cooldown retry)

Ticket: `teams/00_orchestrator/docs/TASK_YOUTUBE_TRANSCRIPT_RETRY.md` — **DONE**.  
Command: `python -m src transcripts --retry-pending --english` (venv; catalog **not** re-fetched). Retrieved ~2026-09-01T19:25Z–20:10Z.

Timedtext still returned **429 on attempt 1–2** for most English `tlang=en` fetches; **attempt 3 after backoff succeeded**. Circuit did not open. No transcripts invented. Hindi `SOURCE_FACT` raw files were not overwritten (language `hi` kept; English lives in `*.en.json` / `normalized_en/`).

| Metric | Count |
|--------|------:|
| Newly TRANSCRIPT_VERIFIED this retry | **12** |
| Remaining 429 / IP-blocked (related) | **0** |
| English companions on disk | **45** (`ENGLISH_VERIFIED`) |
| New YouTube `tlang=en` this run | **44** |
| Native English copied (no extra GET) | **1** (`T9eo_YxAr9U`) |
| ENGLISH_PENDING remaining | **0** |
| Parked (unchanged) | **4** |

Newly verified IDs: `EVk_Wa_1cm0`, `_byuht38r5s`, `4TT8IV5S1_A`, `8h9SYvQWKMA`, `DzT_681GThA`, `_exmJYgFwFA`, `pBQ1oVDVe3M`, `G31RFueZLvk`, `eApl0SfVBBY`, `mPKASwm6Oqk`, `pUg_7sPauQA`, `dEvF8biE02M`.

## Key validation

- Result: **valid** (prior catalog run; this follow-up did not re-validate)
- Channel id: `UCEzHCpvFWoF85UabbzKTkOQ`
- Channel name: Dhan ⚡
- Playlist count (playlists.list, not including uploads): 24

## Discovery (unchanged; catalog was not re-fetched)

- Named playlists enumerated: 24
- Playlists including uploads playlist: 25
- Videos in catalog: 2034

## Popularity and relevance

- HIGH: 1023
- MEDIUM: 197
- LOW: 814
- STOCK_ONLY (kept): 9
- EXCLUDED_STOCK_ONLY (kept, not deleted): 50

## Why timedtext was blocked

Public captions are **not** downloaded via YouTube Data API v3. `captions.list` and `captions.download` require OAuth 2.0 scoped to the **owning channel**. An API key cannot download @DhanHQ caption text. This extractor uses `youtube-transcript-api`, which reads the watch page + Innertube player JSON, then GETs the timedtext URL (optional `tlang=en` for YouTube auto-translate).

After a burst of successful fetches, YouTube started returning **429** (`IpBlocked`) and/or Innertube playability `LOGIN_REQUIRED` with reason "Sign in to confirm you’re not a bot" (`RequestBlocked`). That is bot detection / IP rate-limiting on timedtext — **not** Data API quota (~115 units on the catalog run). Cloud IPs are especially likely to be blocked; a residential IP can still be blocked after too many requests without delay.

Mitigations in this follow-up (no third-party transcript sites, no proxies):

- Browser-like `User-Agent` + `Accept-Language` on the timedtext session
- Pause between videos (`YOUTUBE_TRANSCRIPT_RETRY_PAUSE`, default 4s)
- Exponential backoff on 429 / RequestBlocked (`YOUTUBE_TRANSCRIPT_BACKOFF`, default 20s, 3 attempts)
- Extra cooldown after a blocked video before the next ID
- Stop after 3 consecutive blocks so we do not hammer the endpoint

### Data API captions.list / captions.download probe

- video_id: `qSgKA0-T7Uw`
- captions.list HTTP status: 200
- captions.list reason: n/a
- tracks listed: 1
- track languages: [{'language': 'hi', 'trackKind': 'asr'}]
- captions.download HTTP status: 401
- captions.download reason: required
- Interpretation: `captions.list` **can** succeed with an API key (track metadata only). `captions.download` returns **401** (`API keys are not supported` / OAuth required) and would still be limited to videos this project owns. English text is taken from timedtext / `tlang=en`, not `captions.download`.

## Parked for tomorrow

Pending + IP-blocked IDs that are **not** Phase-1 F&O strategy (options / index / strategy / indicators / price action / Dhan tools for F&O) were parked. Catalog rows were not deleted.

- Parked count: 4
- Folder: `data/transcripts/parked_tomorrow/`

| video_id | title | status | reason |
|---|---|---|---|
| `BTe6ekvvDHk` | Buy Gold & Silver Directly From Exchange on Gold Vault by Dhan / The New Way To Buy The Oldest Asset | TRANSCRIPT_PENDING | Gold Vault product (buy gold/silver on exchange); not NIFTY/SENSEX/BANKNIFTY options, strategy builder, indicators, or price action. |
| `5x6bYmCB0Gw` | Now Live: Super Order on Dhan / Set Entry, Target, & Stop Loss in One Order! / Dhan | TRANSCRIPT_PENDING | Super Order app tutorial (place entry/target/stop in one order). Promo/product walkthrough, not a trading strategy. |
| `2aSkJT-IbqI` | Dhan Ki Bhasha: India Speaks The Language of Money / A Film | TRANSCRIPT_UNAVAILABLE | LOW brand film (Dhan Ki Bhasha). Captions disabled. Not F&O strategy. |
| `-wRCKyORglc` | Happy Muhurat Trading Everyone / Diwali Aarti for every Trader & Investor / #YehDiwaliDhanWali | TRANSCRIPT_UNAVAILABLE | Diwali aarti / Muhurat Trading celebration. Captions disabled. Not options/strategy/indicators. |

## Retry (related pending + IP-blocked)

- Retry targets: 12
- TRANSCRIPT_VERIFIED this retry: 12
- TRANSCRIPT_UNAVAILABLE this retry: 0
- Still pending after retry: 0

### Retry video IDs

`EVk_Wa_1cm0`, `_byuht38r5s`, `4TT8IV5S1_A`, `8h9SYvQWKMA`, `DzT_681GThA`, `_exmJYgFwFA`, `pBQ1oVDVe3M`, `G31RFueZLvk`, `eApl0SfVBBY`, `mPKASwm6Oqk`, `pUg_7sPauQA`, `dEvF8biE02M`

## English captions

Hindi `SOURCE_FACT` files were left intact. English companions were fetched from YouTube only (manual English track if listed, else generated English, else `transcript.translate('en')` which appends `tlang=en`). **No LLM translation.**

- Targets considered: 45
- ENGLISH_VERIFIED: 45
- ENGLISH_UNAVAILABLE: 0
- Native English copied (no extra timedtext): 1
- YouTube translate (`tlang=en`): 44
- Manual English track: 0
- Generated English track: 1

### English file paths

- `data/transcripts/raw/<video_id>.en.json`
- `data/transcripts/normalized_en/<video_id>.md`

## Catalog counts after this follow-up

- TRANSCRIPT_VERIFIED: 45
- TRANSCRIPT_UNAVAILABLE: 2
- TRANSCRIPT_PENDING: 2
- ENGLISH_VERIFIED: 45
- ENGLISH_UNAVAILABLE: 0
- Parked (reason set, rows kept): 4

## Remaining gaps

1. Timedtext still 429s on the **first** English `tlang=en` GET; backoff attempt 3 worked this session. If a future burst trips the 3-block circuit, wait before hammering.
2. Parked (do not extract until un-parked): `BTe6ekvvDHk`, `5x6bYmCB0Gw`, `2aSkJT-IbqI`, `-wRCKyORglc`. Last two have captions **disabled**.
3. SOURCE_FACT still incomplete vs 45 verified files. New IDs need extraction (esp. `_exmJYgFwFA`, `DzT_681GThA`).
4. Do not LLM-translate; YouTube English is on disk.

## Outputs

- `data/youtube/video_catalog.csv`
- `data/youtube/video_catalog.json`
- `data/transcripts/raw/<video_id>.json` (source language)
- `data/transcripts/raw/<video_id>.en.json` (English companion)
- `data/transcripts/normalized/<video_id>.md`
- `data/transcripts/normalized_en/<video_id>.md`
- `data/transcripts/parked_tomorrow/`

## How to re-run

From `teams/01_research/youtube` with the local venv activated:

```bash
python -m src transcripts --retry-pending --english
python -m src transcripts --english --english-cap 40
```

Optional env (repo-root `.env`): `YOUTUBE_TRANSCRIPT_PAUSE`, `YOUTUBE_TRANSCRIPT_RETRY_PAUSE`, `YOUTUBE_TRANSCRIPT_BACKOFF`, `YOUTUBE_TRANSCRIPT_BACKOFF_ATTEMPTS`.

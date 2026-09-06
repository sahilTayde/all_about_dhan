# Chart Fanatics — Phase-3 gentle caption retry log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (fetch status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Caption retry only — **no** MIX/STRAT clubbing, **no** full-channel claim, **no** deep guest binds this turn.

## Mandate

- Skip priority `tvERE-Beu2U` (Phase-2 Fabio already bound).
- Heavy rate limiting; stop after ~8–12 successes **or** repeated HTTP **429** / IP block.
- Prefer highest-view guest / interview / LIVE videos first.

## Methods tried (serial, not parallel)

| Method | Result |
|--------|--------|
| `youtube-transcript-api` | **IpBlocked** (all probes) |
| `yt-dlp` `--write-auto-subs` `player_client=android` | Subtitle list OK → download **HTTP 429** |
| `yt-dlp` ios / tv / mweb | Fail (unavailable / reload / no sub body) — not used in parallel |
| Watch-page HTML scrape → `captionTracks` | **Works** (tracks present) |
| `timedtext` / caption `baseUrl` fetch (with cookies + Referer) | **HTTP 429** “Sorry…” |
| Innertube `youtubei/v1/get_transcript` (WEB + ANDROID + visitorData) | **HTTP 400** `FAILED_PRECONDITION` |
| Fabio path `WebFetch_youtube_watch_transcript_markdown` | **Not available** in this Phase-3 runner (prior Fabio disk only) |

**Sleeps used:** ~45s between yt-dlp queue videos; ~35s between timedtext attempts; ~90s cooldown before innertube probe.

## Attempts this turn (skip Fabio)

| Video ID | Title (short) | Views | Transcript | Notes |
|----------|---------------|------:|------------|-------|
| `DAnXM7C16h0` | Liquidity TRAP strategy | 1,272,415 | **fail** | IpBlocked + android **429**; timedtext **429** |
| `coBMd1vk2Lo` | $10M ICT Blueprint | 1,010,712 | **fail** | IpBlocked + android **429** |
| `AVVM-FyewLg` | World's #2 Futures Trader | 950,121 | **fail** | android **429** (stop streak); timedtext **429** |
| `VTEQ2fhGLqE` | Tori Trades futures | 808,732 | **fail** | timedtext **429**; innertube 400 |

**New full transcripts this turn:** **0**  
**New MD paths:** none (stubs remain `missing`; no new `_TRANSCRIPT.md` bodies)

## Stop reason (honest)

**Repeated HTTP 429** on caption body downloads (yt-dlp android + `timedtext` API) after gentle spacing. Watch HTML still lists tracks, but YouTube rejects subtitle payload fetches from this host IP. Channel is **not** done.

## Artifacts

- Fetch JSON: `data/transcripts/external_chart_fanatics/_phase3_fetch_results.json`
- Inventory: `CHANNEL_INVENTORY.md` (Phase-3 note; counts still yes=1 / fail=46)
- Priority unchanged: `tvERE-Beu2U` only full transcript on disk

## HANDOFF

- **Accepted:** Phase-3 attempted; rate-limit stop; inventory + this log.
- **Rejected:** Claiming remaining guests transcribed; any new MIX rows; mass parallel yt-dlp.
- **UNKNOWN / DATA_INSUFFICIENT:** Captions for all non-Fabio catalog rows until IP/429 clears or alternate non-blocked fetch path (e.g. prior WebFetch) is available.
- **Next (Phase-4):** Per-guest analyze **only** when a new transcript lands. Do not deep-analyze the fail queue. Optional: retry captions later from a non-blocked network.


---

## Follow-up: Phase-3B ASR (same day)

Captions still blocked. Alternate path: **audio → faster-whisper** for top-2 views. See [`PHASE3B_ASR_LOG.md`](PHASE3B_ASR_LOG.md).

- `DAnXM7C16h0` → **full** ASR (Marco)
- `coBMd1vk2Lo` → **full** ASR (Trader Mayne)

Phase-4 may analyze those guests next. No caption unlock claimed.


---

## Follow-up: Phase-3C ASR (same day)

Still no caption unlock. ASR for next-2 views: `AVVM-FyewLg`, `VTEQ2fhGLqE`. See [`PHASE3C_ASR_LOG.md`](PHASE3C_ASR_LOG.md).

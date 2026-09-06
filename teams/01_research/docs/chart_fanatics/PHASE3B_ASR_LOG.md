# Chart Fanatics — Phase-3B ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Alternate ingest when captions are IpBlocked/429 — **audio → local ASR** for 1–2 top videos only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 caption retry got **0** new transcripts (timedtext / yt-dlp subs **HTTP 429**). This pass does **not** hammer timedtext.

## Tooling

| Piece | Detail |
|-------|--------|
| Download | `yt-dlp` 2025.10.14 · `player_client=android` · format 18 progressive → ffmpeg extract AAC/m4a |
| ffmpeg | `imageio-ffmpeg` bundled binary (system ffmpeg absent) |
| ASR | **faster-whisper** · model=`base` · `device=cpu` · `compute_type=int8` · `vad_filter=True` · `beam_size=1` |
| Source tag | `ASR_WHISPER` — **not** YouTube captions |

## Results

| Video ID | Title (short) | Audio | ASR | Duration processed | Chars | Elapsed | Paths |
|----------|---------------|-------|-----|-------------------:|------:|--------:|-------|
| `DAnXM7C16h0` | Liquidity TRAP (Marco) | **ok** m4a 76MiB | **ok** | 6576.8s (~1h49m37s) | 110682 | 249.6s | audio + `.asr.txt` + `DAnXM7C16h0_TRANSCRIPT.md` |
| `coBMd1vk2Lo` | $10M ICT Blueprint | **ok** m4a 56MiB | **ok** | 3627.5s (~1h00m28s) | 59933 | 131.4s | audio + `.asr.txt` + `coBMd1vk2Lo_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Default yt-dlp web client failed (“page needs to be reloaded”); **android** client worked without PO token by falling back to progressive format 18 (video+audio), then audio extract.
- Captions remain blocked on this host — ASR is a workaround, not a caption unlock.
- Did **not** parallel-download; ~60s pause between videos.
- No 429 on media download for these two IDs.

## HANDOFF

- **Accepted:** Two ASR full transcripts (Marco / Trader Mayne); inventory counts updated; Phase-4 may analyze these guests next.
- **Rejected:** Strategy/MIX coding this turn; fabricating text; mass downloads; claiming YouTube captions work.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining 44 fail-catalog rows; ASR proper-noun accuracy.
- **Next:** Phase-4 bind/analyze **Marco** (`DAnXM7C16h0`) and/or **Trader Mayne** (`coBMd1vk2Lo`) from ASR text. Captions still blocked for the rest of the catalog.


---

## Follow-up: Phase-3C ASR (same day)

Next-2 by views after 3B: `AVVM-FyewLg` (Marci Silfrain) + `VTEQ2fhGLqE` (Tori Trades) → **full** ASR. See [`PHASE3C_ASR_LOG.md`](PHASE3C_ASR_LOG.md). Captions still blocked.

# Chart Fanatics — Phase-3C ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Next **2** highest-view fail videos after Phase-3B — **audio → local ASR** only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 captions still **429**. Phase-3B already landed Marco + Trader Mayne. This pass continues the same workaround for the next two by views.

## Tooling

| Piece | Detail |
|-------|--------|
| Download | `yt-dlp` 2025.10.14 · `player_client=android` · format **18** progressive → ffmpeg extract AAC/m4a |
| ffmpeg | `imageio-ffmpeg` bundled binary |
| ASR | **faster-whisper** · model=`base` · `device=cpu` · `compute_type=int8` · `vad_filter=True` · `beam_size=1` |
| Source tag | `ASR_WHISPER` — **not** YouTube captions |

## Results

| Video ID | Title (short) | Guest | Audio | ASR | Duration processed | Chars | Wall ASR | Paths |
|----------|---------------|-------|-------|-----|-------------------:|------:|---------:|-------|
| `AVVM-FyewLg` | WORLD's #2 Futures Trader | **Marci Silfrain** (title; ASR “Marcy Silfrane/Silfrey”) | **ok** m4a ~58MiB | **ok** | 5009.4s (~1h23m29s) | 69669 | 170.6s | audio + `.asr.txt` + `AVVM-FyewLg_TRANSCRIPT.md` |
| `VTEQ2fhGLqE` | SIMPLE Futures Strategy | **Tori Trades** (title; ASR “Tory trades”) | **ok** m4a ~66MiB | **ok** | 4283.7s (~1h11m24s) | 75177 | 180.8s | audio + `.asr.txt` + `VTEQ2fhGLqE_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Serial downloads; ~60s pause between videos.
- Android client fell back to progressive format 18 (PO-token https formats skipped); no media 429 on these IDs.
- AVVM progressive download ~10.5 min wall (203.92MiB); VTEQ ~10s wall (108.73MiB).

## HANDOFF

- **Accepted:** Two ASR full transcripts (Marci Silfrain / Tori Trades); inventory counts updated; Phase-5 may bind these guests next.
- **Rejected:** Strategy/MIX coding this turn; fabricating text; mass downloads; claiming YouTube captions work.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining fail-catalog rows; ASR proper-noun accuracy (esp. Marci spelling).
- **Next:** Phase-5 bind/analyze **Marci Silfrain** (`AVVM-FyewLg`) and/or **Tori Trades** (`VTEQ2fhGLqE`) from ASR text. Captions still blocked for the rest of the catalog.

# Chart Fanatics — Phase-3D ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Next **2** highest-view fail videos after Phase-3C — **audio → local ASR** only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 captions still **429**. Phase-3B/3C already landed Marco, Trader Mayne, Marci Silfrain, Tori Trades. This pass continues the same workaround for the next two by views.

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
| `ADnslyKOwFE` | INSANE Simple 90% Win Rate — TG Capital | **TG Capital** / aka Tyler (title + ASR) | **ok** m4a ~34MiB | **ok** | 2895.3s (~48m15.3s) | 52603 | 122.1s | audio + `.asr.txt` + `ADnslyKOwFE_TRANSCRIPT.md` |
| `HNuRp9Z1bMs` | Worlds BEST NQ Scalper | **Trader Kane** (ASR; founder of the lab) | **ok** m4a ~69MiB | **ok** | 4484.0s (~1h14m44.0s) | 72616 | 179.8s | audio + `.asr.txt` + `HNuRp9Z1bMs_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Serial downloads; ~60s pause between videos.
- Android client fell back to progressive format 18 (PO-token https formats skipped); no media 429 on these IDs.
- ADnsly progressive download ~136MiB / ~7s wall; HNuR ~110MiB / ~10s wall after pause.

## HANDOFF

- **Accepted:** Two ASR full transcripts (TG Capital / Trader Kane); inventory counts updated to yes=7 / fail=40; ready for Phase-6 bind.
- **Rejected:** Strategy/MIX coding this turn; fabricating text; mass downloads; claiming YouTube captions work.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining fail-catalog rows; ASR proper-noun accuracy (Kane / Tyler spellings).
- **Next:** Phase-6 bind/analyze **TG Capital** (`ADnslyKOwFE`) and/or **Trader Kane** (`HNuRp9Z1bMs`) from ASR text. Captions still blocked for the rest of the catalog.

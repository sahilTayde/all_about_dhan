# Chart Fanatics — Phase-3E ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Next **2** highest-view fail videos after Phase-3D — **audio → local ASR** only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 captions still **429**. Phase-3B/3C/3D already landed six ASR videos. This pass continues the same workaround for the next two by views (stub TRANSCRIPT.md only — no prior `ASR_WHISPER`).

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
| `IUo5AwmsE9A` | 12 Years of Trading Knowledge — Umar Ashraf | **Umar Ashraf** (TradeZella; ASR 'Buma Ashraf') | **ok** m4a ~83MiB | **ok** | 7144.1s (~1h59m04.1s) | 127589 | 268.7s | audio + `.asr.txt` + `IUo5AwmsE9A_TRANSCRIPT.md` |
| `q_MdVlZ1SH4` | ONE Trading Indicator / volume profile | **Forest Knight** / aka Forest (ASR) | **ok** m4a ~58MiB | **ok** | 4982.8s (~1h23m02.8s) | 81039 | 202.2s | audio + `.asr.txt` + `q_MdVlZ1SH4_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Serial downloads; ~60s pause between videos.
- Android client fell back to progressive format 18 (PO-token https formats skipped); no media 429 on these IDs.
- IUo5 progressive ~319MiB / ~14s wall; q_Md ~212MiB / ~8s wall after pause.

## HANDOFF

- **Accepted:** Two ASR full transcripts (Umar Ashraf / Forest Knight); inventory counts updated to yes=9 / fail=38; Phase-7 bind+MIX+proxy done.
- **Rejected:** Strategy/MIX coding this turn (ingest-only at Phase-3E); fabricating text; mass downloads; claiming YouTube captions work.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining fail-catalog rows; ASR proper-noun accuracy (Ashraf / Forest Knight spellings; “Buma Ashraf”).
- **Next:** fail=38 still need ASR/caption later when asked. Captions still blocked. Do **not** deep-analyze the fail queue.

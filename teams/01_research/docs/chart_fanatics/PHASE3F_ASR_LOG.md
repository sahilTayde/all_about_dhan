# Chart Fanatics — Phase-3F ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Next **2** highest-view fail videos after Phase-3E — **audio → local ASR** only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 captions still **429**. Phase-3B–3E already landed eight ASR videos. This pass continues the same workaround for the next two by views (stub TRANSCRIPT.md only — no prior `ASR_WHISPER`).

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
| `UhkRRqO1gQM` | LIVE OrderFlow masterclass | **Carmine Rosato** | **ok** m4a ~155MiB | **ok** | 13339.9s (~3h42m19.9s) | 191283 | 447.8s | audio + `.asr.txt` + `UhkRRqO1gQM_TRANSCRIPT.md` |
| `8OX-mcSHWhg` | Prop firm SIMPLE strategy — Jadecap | **Jadecap** | **ok** m4a ~62MiB | **ok** | 5302.6s (~1h28m22.6s) | 93442 | 216.4s | audio + `.asr.txt` + `8OX-mcSHWhg_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Serial downloads; ~60s pause between videos.
- Android client fell back to progressive format 18 (PO-token https formats skipped); no media 429 on these IDs.
- Uhk progressive ~511MiB / ~48s wall; 8OX ~236MiB / ~10s wall after pause.

## HANDOFF

- **Accepted:** Two ASR full transcripts (Carmine Rosato / Jadecap); inventory counts updated to yes=11 / fail=36; **Phase-8 bind+MIX+proxy DONE**.
- **Rejected:** Fabricating text; inventing India DOM/Asia clocks; promoting proxies; clubbing into prior CF/STRAT/IQ.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining fail-catalog rows; ASR proper-noun accuracy; true OF absorb; Asia/London→NSE.
- **Next:** fail=36 still need ASR/caption later when asked. Captions still blocked. Do **not** deep-analyze the fail queue.

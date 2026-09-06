# Chart Fanatics — Phase-3G ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Next **2** highest-view fail videos after Phase-3F — **audio → local ASR** only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 captions still **429**. Phase-3B–3F already landed ten ASR videos. This pass continues the same workaround for the next two by views (stub TRANSCRIPT.md only — no prior `ASR_WHISPER`).

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
| `6Bdv-_YUQ0s` | Options for Beginners — 2h FREE course | **Usman Ashraf** (ASR Osman Astra) | **ok** m4a ~41.8MiB | **ok** | 7193.6s (~1h59m53.6s) | 104243 | 247.6s | audio + `.asr.txt` + `6Bdv-_YUQ0s_TRANSCRIPT.md` |
| `yLuH8YZXORQ` | $6k → $10M+ strategy | **Brando / Leaf** (ASR brand-a-k-a-leaf) | **ok** m4a ~61.8MiB | **ok** | 4010.0s (~1h6m50.0s) | 63970 | 144.1s | audio + `.asr.txt` + `yLuH8YZXORQ_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Serial downloads; ~60s pause between videos.
- Android client progressive format 18; no media 429 on these IDs.
- Whisper model loaded from local HF snapshot (`local_files_only`) after sandbox proxy 403 on hub check.

## HANDOFF

- **Accepted:** Two ASR full transcripts (Usman Ashraf / Brando-Leaf); inventory counts updated to yes=13 / fail=34; Phase-9 bind+MIX later asked separately.
- **Rejected:** Fabricating text; inventing India DOM/Asia clocks; promoting proxies; clubbing into prior CF/STRAT/IQ.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining fail-catalog rows; ASR proper-noun accuracy (Osman Astra ↔ Usman Ashraf; brand-a-k-a-leaf ↔ Brando/Leaf).
- **Next (done when asked):** Phase-9 bind Usman+Brando — see CONTINUE. fail=34 still need ASR/caption later. Captions still blocked. Do **not** deep-analyze the fail queue. Do **not** merge into `MIX-DEFAULT-BUY` / STRAT-001–014.

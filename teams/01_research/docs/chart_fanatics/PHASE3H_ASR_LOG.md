# Chart Fanatics — Phase-3H ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Next **2** highest-view fail videos after Phase-3G — **audio → local ASR** only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 captions still **429**. Phase-3B–3G already landed twelve ASR videos. This pass continues the same workaround for the next two by views (stub TRANSCRIPT.md only — no prior `ASR_WHISPER`).

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
| `TvoQr6ObjnU` | LIVE with world's best scalpers | **Andrea Cimi** (ASR Andrea Chimney; stub wrongly Fabio) | **ok** m4a ~237.7MiB | **ok** | 20474.1s (~5h41m14.1s) | 257758 | 725.4s | audio + `.asr.txt` + `TvoQr6ObjnU_TRANSCRIPT.md` |
| `IB-fyWI5j8w` | EASY ICT for prop firms | **Omor / NBB Trader** (ASR Omore aka MBB) | **ok** m4a ~57.0MiB | **ok** | 4912.3s (~1h21m52.3s) | 79463 | 170.9s | audio + `.asr.txt` + `IB-fyWI5j8w_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Serial downloads; ~60s pause between videos.
- Android client progressive format 18; no media 429 on these IDs.
- Whisper model loaded from local HF snapshot (`local_files_only`) after sandbox proxy 403 on hub check.
- Inventory stub listed `TvoQr6ObjnU` guest as Fabio Valentini; YouTube description + spoken intro = **Andrea Cimi** (Fabio mentioned as mentor / comparison only).

## HANDOFF

- **Accepted:** Two ASR full transcripts (Andrea Cimi / Omor-NBB); inventory counts updated to yes=15 / fail=32; **Phase-10 bind+MIX+proxy DONE** (see CONTINUE).
- **Rejected:** Fabricating text; inventing India DOM/Asia clocks; promoting proxies; clubbing into prior CF/STRAT/IQ/Fabio.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining fail-catalog rows; ASR proper-noun accuracy (Andrea Chimney ↔ Andrea Cimi; Omore/MBB ↔ Omor/NBB).
- **Next:** fail=32 still need ASR/caption later. Captions still blocked. Do **not** deep-analyze the fail queue. Do **not** merge into `MIX-DEFAULT-BUY` / STRAT-001–014 / Fabio.


---

## Follow-up: Phase-3I ASR (same day)

Next-2 by views after 3H: `hvyf6frvCcA` (Trader Yush) + `T_djSNBmV00` (Marco return) → **full** ASR. See [`PHASE3I_ASR_LOG.md`](PHASE3I_ASR_LOG.md). Captions still blocked. No MIX this turn.

# Chart Fanatics — Phase-3I ASR ingest log

**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (ingest status only). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Next **2** highest-view fail videos after Phase-3H — **audio → local ASR** only. **No** MIX/STRAT analysis this turn.

## Why

Phase-3 captions still **429**. Phase-3B–3H already landed fourteen ASR videos (inventory yes=15 with Fabio). This pass continues the same workaround for the next two by views (stub TRANSCRIPT.md only — no prior `ASR_WHISPER`).

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
| `hvyf6frvCcA` | OrderFlow strategy ($2M+ payouts) | **Trader Yush / Yush** (ASR 'trader use' / 'You're') | **ok** m4a ~65MiB | **ok** | 5589.9s (~1h33m09.9s) | 91704 | 219.9s | audio + `.asr.txt` + `hvyf6frvCcA_TRANSCRIPT.md` |
| `T_djSNBmV00` | ONE Liquidity pattern | **Marco** (return; ASR 'Marco Acetum') | **ok** m4a ~50MiB | **ok** | 4281.9s (~1h11m21.9s) | 74511 | 164.2s | audio + `.asr.txt` + `T_djSNBmV00_TRANSCRIPT.md` |

**New full transcripts this turn:** **2** (ASR quality `[ASR]`)

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Serial downloads; ~60s pause between videos.
- Android client progressive format 18; no media 429 on these IDs.
- Whisper model loaded from local HF snapshot (`local_files_only`).
- `T_djSNBmV00` is a **return Marco** episode (prior `DAnXM7C16h0`); Phase-11 bind must not invent new STRAT-015+ or auto-club into `MIX-CF-MARCO-*` without explicit review.
- No MIX this turn.

## HANDOFF

- **Accepted:** Two ASR full transcripts (Trader Yush / Marco return); inventory counts updated to yes=17 / fail=30; CONTINUE ready for **Phase-11 bind** (no MIX coded here).
- **Rejected:** Fabricating text; inventing India DOM/Asia clocks; promoting proxies; clubbing into prior CF/STRAT/IQ/Fabio without bind review; timedtext hammer.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; remaining fail-catalog rows; ASR proper-noun accuracy (Yush ↔ use/You're; Marco Acetum spelling).
- **Next:** Phase-11 bind for **Trader Yush** (`hvyf6frvCcA`) and/or **Marco** return (`T_djSNBmV00`) from ASR text when asked. Do not deep-analyze the fail queue. Captions remain blocked on this host.

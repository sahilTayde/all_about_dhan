# Chart Fanatics — Phase-3J ASR + Okala bind log

**Date:** 2026-09-07  
**Layer:** `SOURCE_FACT` (ingest) + `HYPOTHESIS` (named MIX formalization). Education ≠ edge. **Not** DHAN-DERIVED.  
**Scope:** Founder ask — retry transcript for `jsUTbjwpFVk` **now**, then BIND + `MIX-CF-OKALA-*` if warranted.

## Why

Inventory fail (IpBlocked captions). Preferred path = **audio → local ASR** (same as Phase-3B–3I). Do not timedtext-hammer.

## Tooling

| Piece | Detail |
|-------|--------|
| Download | `yt-dlp` 2025.10.14 · `player_client=android` · format **18** progressive → ffmpeg extract AAC/m4a |
| ffmpeg | `imageio-ffmpeg` bundled binary |
| ASR | **faster-whisper** · model=`base` · `device=cpu` · `compute_type=int8` · `vad_filter=True` · `beam_size=1` · `local_files_only` |
| Source tag | `ASR_WHISPER` — **not** YouTube captions |

## Results

| Video ID | Title (short) | Guest | Audio | ASR | Duration processed | Chars | Wall ASR | Paths |
|----------|---------------|-------|-------|-----|-------------------:|------:|---------:|-------|
| `jsUTbjwpFVk` | Prop firm simple 65% (title) | **Okala** (desc; ASR O'Cala) | **ok** m4a ~51MiB | **ok** | 4393.4s (~1h13m13.4s) | 59301 | 157.8s | audio + `.asr.txt` + `jsUTbjwpFVk_TRANSCRIPT.md` + `jsUTbjwpFVk_BIND.md` |

**New full transcripts this turn:** **1** (ASR quality `[ASR]`)  
**MIX named:** `MIX-CF-OKALA-8020-LEVEL`, `MIX-CF-OKALA-FORK`, `MIX-CF-OKALA-H-CROSS`, `MIX-CF-OKALA-REPAIR` — **catalog only** (`evaluator_bound: false`; not in CF×8 runners).

## Strategy one-liner (HYPOTHESIS formalization of SOURCE_FACT)

NASDAQ **80/20** mean-reversion on **10m + 200s**, always **10-pt SL / ~15 TP1 / BE**, NY-open prefer; entries stack levels with **fork / H+cross / repair** PA. Title **65%** ≠ our WR.

## Notes / blockers

- Captions remain blocked — no timedtext hammering.
- Android progressive media download **ok** (fmt 18); PO-token warning on https formats skipped — progressive still worked.
- Whisper model from local HF snapshot (`local_files_only`).
- Do **not** club into Jadecap/Omor/STRAT. **NO_PROMOTE.**

## HANDOFF

- **Accepted:** Full ASR + BIND + four `MIX-CF-OKALA-*` catalog rows; inventory yes=18 / fail=29; removed from RETRY queue.
- **Rejected:** Fabricating NIFTY digit clocks; wiring fake evaluator; treating 65%/70% as VALIDATION.
- **UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; NQ→NIFTY 80/20 map; repair under 3m remap.
- **Next:** Remaining fail=29 ASR when asked; Phase-11 Yush/Marco bind when asked; 06 Okala evaluator only if founder asks.

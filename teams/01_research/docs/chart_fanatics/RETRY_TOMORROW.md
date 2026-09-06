# Chart Fanatics — RETRY TOMORROW (failed transcript queue)

**Status:** `SOURCE_FACT` inventory · **retry scheduled**  
**As of:** 2026-09-06 (Sunday) → **retry on next session / Monday+**  
**Channel:** `@chart-fanatics` · `UC2GyeAMRDA4cRIiISejML2g`  
**Do not lose this list.** Education ≠ edge. No live orders.

## Counts (locked for tomorrow)

| Bucket | Count | Meaning |
|--------|------:|---------|
| Catalogued | **47** | Channel inventory snapshot |
| Transcript **yes** | **17** | Full body on disk (1 YT caption + 16 ASR) |
| Transcript **fail** (retry) | **30** | Metadata stub only — **no full body** |
| Bind pending (already yes) | **2** | Phase-11: Yush + Marco return — **not** in fail queue |

**Canonical inventory:** [`CHANNEL_INVENTORY.md`](CHANNEL_INVENTORY.md)  
**Wake-up:** [`CONTINUE_NEXT_CHAT.md`](../../00_orchestrator/docs/CONTINUE_NEXT_CHAT.md)

## How to retry (preferred order)

1. **ASR path (proven):** yt-dlp android → progressive audio → faster-whisper `base` int8 → `{id}.asr.txt` + full `{id}_TRANSCRIPT.md` tagged `ASR_WHISPER` / `[ASR]`.  
2. **Captions:** only if HTTP 429 / IpBlocked has cleared — do **not** hammer timedtext.  
3. Batch size: **2–4 videos** per turn; ~60s between downloads.  
4. After each success: flip inventory row `fail` → `yes`; shrink this queue; then bind as new Phase (do **not** club into STRAT-001–014 / prior MIX-CF without review).

## Fail queue — retry tomorrow (views desc)

Stub MD may exist (header only). Treat as **fail** until full ASR/caption body exists under `data/transcripts/external_chart_fanatics/`.

| # | Views | ID | Title (short) | URL |
|--:|------:|----|---------------|-----|
| 1 | 280,453 | `xUyqIjCfZzg` | LIVE OF scalpers (Fabio + Carmine) | https://www.youtube.com/watch?v=xUyqIjCfZzg |
| 2 | 253,169 | `SMSqQTBxjc0` | Break And Retest | https://www.youtube.com/watch?v=SMSqQTBxjc0 |
| 3 | 251,710 | `jsUTbjwpFVk` | Prop firm simple 65% | https://www.youtube.com/watch?v=jsUTbjwpFVk |
| 4 | 238,062 | `Jx5cJ_qb31U` | Crazy simple 98% | https://www.youtube.com/watch?v=Jx5cJ_qb31U |
| 5 | 230,085 | `PZDWQgtqt2I` | ICT futures — Tanja | https://www.youtube.com/watch?v=PZDWQgtqt2I |
| 6 | 224,988 | `_qeFh1ADss8` | $100M+ Market Wizard | https://www.youtube.com/watch?v=_qeFh1ADss8 |
| 7 | 223,438 | `52ZsDmFHqyY` | One strategy video | https://www.youtube.com/watch?v=52ZsDmFHqyY |
| 8 | 223,222 | `jHsD2-2K_Kk` | Real FVG — Carmine | https://www.youtube.com/watch?v=jHsD2-2K_Kk |
| 9 | 219,399 | `SQEtBHOJW6I` | LIVE $1M+ OF trader | https://www.youtube.com/watch?v=SQEtBHOJW6I |
| 10 | 215,127 | `yZpzG8R3Ayk` | PRO simple strategy | https://www.youtube.com/watch?v=yZpzG8R3Ayk |
| 11 | 210,733 | `WDdvnd9vLbM` | One trading process | https://www.youtube.com/watch?v=WDdvnd9vLbM |
| 12 | 206,323 | `YzYDUEUOZ4k` | Exact entry system | https://www.youtube.com/watch?v=YzYDUEUOZ4k |
| 13 | 184,576 | `VDK200OHNSo` | $50M market cycle | https://www.youtube.com/watch?v=VDK200OHNSo |
| 14 | 169,465 | `mDNcx2Dhhms` | $100M strategy | https://www.youtube.com/watch?v=mDNcx2Dhhms |
| 15 | 167,098 | `8HxT9WQ-uD0` | Mental game / tilt | https://www.youtube.com/watch?v=8HxT9WQ-uD0 |
| 16 | 162,291 | `UIGZtoGGPH4` | One ICT LIVE | https://www.youtube.com/watch?v=UIGZtoGGPH4 |
| 17 | 158,828 | `xl4QHqlBCfk` | Champion math models | https://www.youtube.com/watch?v=xl4QHqlBCfk |
| 18 | 157,881 | `TyHTEtArsS4` | Algo trading no code | https://www.youtube.com/watch?v=TyHTEtArsS4 |
| 19 | 156,135 | `nMhywubR2xc` | 7-figure liquidity | https://www.youtube.com/watch?v=nMhywubR2xc |
| 20 | 128,365 | `35cyqDz-ej8` | 1m market maker | https://www.youtube.com/watch?v=35cyqDz-ej8 |
| 21 | 116,897 | `_wpg45NdMkM` | 20y institutional | https://www.youtube.com/watch?v=_wpg45NdMkM |
| 22 | 116,054 | `9D9ck-ZI6V0` | 3 steps any market | https://www.youtube.com/watch?v=9D9ck-ZI6V0 |
| 23 | 110,130 | `70UtrLU6RAg` | $5M+ LIVE exact | https://www.youtube.com/watch?v=70UtrLU6RAg |
| 24 | 93,733 | `EZ_L7zovyrw` | Trend futures — Anthony | https://www.youtube.com/watch?v=EZ_L7zovyrw |
| 25 | 87,119 | `4BgkLlwgpvo` | Fear formula | https://www.youtube.com/watch?v=4BgkLlwgpvo |
| 26 | 83,488 | `0_NSmOWVbpA` | Market cycle video | https://www.youtube.com/watch?v=0_NSmOWVbpA |
| 27 | 76,895 | `2Ug0jyDvoek` | One candle | https://www.youtube.com/watch?v=2Ug0jyDvoek |
| 28 | 74,264 | `SInAfwX3X3A` | Short strategy US | https://www.youtube.com/watch?v=SInAfwX3X3A |
| 29 | 66,591 | `KkTTCKr-3Ew` | ICT + OF prop | https://www.youtube.com/watch?v=KkTTCKr-3Ew |
| 30 | 47,942 | `EcTRlLYvhXU` | Gap up short | https://www.youtube.com/watch?v=EcTRlLYvhXU |

### ID checklist (paste for agents)

```text
xUyqIjCfZzg SMSqQTBxjc0 jsUTbjwpFVk Jx5cJ_qb31U PZDWQgtqt2I
_qeFh1ADss8 52ZsDmFHqyY jHsD2-2K_Kk SQEtBHOJW6I yZpzG8R3Ayk
WDdvnd9vLbM YzYDUEUOZ4k VDK200OHNSo mDNcx2Dhhms 8HxT9WQ-uD0
UIGZtoGGPH4 xl4QHqlBCfk TyHTEtArsS4 nMhywubR2xc 35cyqDz-ej8
_wpg45NdMkM 9D9ck-ZI6V0 70UtrLU6RAg EZ_L7zovyrw 4BgkLlwgpvo
0_NSmOWVbpA 2Ug0jyDvoek SInAfwX3X3A KkTTCKr-3Ew EcTRlLYvhXU
```

## Not in this fail queue (already have full transcript)

Do **not** re-ASR these unless body is corrupt:

Fabio `tvERE-Beu2U` · Marco `DAnXM7C16h0` · Mayne `coBMd1vk2Lo` · Marci `AVVM-FyewLg` · Tori `VTEQ2fhGLqE` · TG `ADnslyKOwFE` · Kane `HNuRp9Z1bMs` · Umar `IUo5AwmsE9A` · Forest `q_MdVlZ1SH4` · Carmine `UhkRRqO1gQM` · Jadecap `8OX-mcSHWhg` · Usman `6Bdv-_YUQ0s` · Brando `yLuH8YZXORQ` · Andrea `TvoQr6ObjnU` · Omor `IB-fyWI5j8w` · Yush `hvyf6frvCcA` · Marco return `T_djSNBmV00`

## Also tomorrow (separate from fail ASR)

- **Phase-11 bind:** Yush + Marco return (transcripts ready).  
- Optional: Monday paper session arming (DEFAULT + CLUB-GR) — founder ask separately.

## HANDOFF

```text
Accepted: Locked fail=30 retry list for tomorrow; ASR preferred; no silent drop.
Rejected: Claiming stubs are full transcripts; caption hammer; clubbing on retry.
UNKNOWN: Whether 429 clears; ASR noun quality on long LIVE videos.
Next: Tomorrow agent — ASR top of queue (start xUyqIjCfZzg …), update inventory, then bind.
```

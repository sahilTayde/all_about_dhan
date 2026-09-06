# TASK — YouTube timedtext retry + English companions

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01  
**Assigned team:** 01_research / youtube  
**Owner path:** `teams/01_research/youtube/`  
**Status:** DONE

---

## Requirement

User returned after ~3 days of timedtext cooldown. Retry captions now that the HTTP 429 / IP block may have reset.

1. Retry **TRANSCRIPT_PENDING** + IP-blocked **related** videos (F&O / strategy / indicators / price action). Do **not** re-run full catalog.
2. Fetch YouTube English (`tlang=en`) for Hindi **TRANSCRIPT_VERIFIED** videos. Keep Hindi `SOURCE_FACT` files intact.
3. Do **not** LLM-translate.
4. Parked / unrelated IDs stay parked (`data/transcripts/parked_tomorrow/`). Catalog rows are not deleted.
5. Never print or log `YOUTUBE_API_KEY`. Load from repo-root `.env` only.
6. If 429 returns: stop after consecutive failures (collector circuit), document, do **not** invent transcripts.

Related pending IDs from last handoff: `8h9SYvQWKMA`, `DzT_681GThA`, `_exmJYgFwFA`.  
Earlier IP-blocked HIGH list: `EVk_Wa_1cm0`, `_byuht38r5s`, `4TT8IV5S1_A`, `pBQ1oVDVe3M`, `G31RFueZLvk`, `eApl0SfVBBY`, `mPKASwm6Oqk`, `pUg_7sPauQA`, `dEvF8biE02M`.

---

## Command

From `teams/01_research/youtube` with venv:

```bash
python -m src transcripts --retry-pending --english
```

Ran 2026-09-01T19:25Z–20:10Z. Catalog was **not** re-fetched. Exit 0. First-try timedtext 429s were common on English `tlang=en`; backoff attempt 3 succeeded. Circuit did not open.

---

## Counts

| Metric | Count |
|--------|------:|
| Newly TRANSCRIPT_VERIFIED this retry | **12** |
| English companions newly stored (`tlang=en`) | **44** |
| ENGLISH_VERIFIED total (incl. native `T9eo_YxAr9U`) | **45** |
| Remaining 429 / IP-blocked (related) | **0** |
| Still TRANSCRIPT_PENDING (related) | **0** |
| Parked (unchanged) | **4** |

**Final status:** DONE

Newly verified: `EVk_Wa_1cm0`, `_byuht38r5s`, `4TT8IV5S1_A`, `8h9SYvQWKMA`, `DzT_681GThA`, `_exmJYgFwFA`, `pBQ1oVDVe3M`, `G31RFueZLvk`, `eApl0SfVBBY`, `mPKASwm6Oqk`, `pUg_7sPauQA`, `dEvF8biE02M`.

Parked still pending/unavailable (not related): `BTe6ekvvDHk`, `5x6bYmCB0Gw` (PENDING); `2aSkJT-IbqI`, `-wRCKyORglc` (captions disabled).

**Notes:**
- Hindi source JSON/markdown left intact (`hi`). English in `data/transcripts/raw/<id>.en.json` and `normalized_en/`.
- Catalog: VERIFIED 45 · UNAVAILABLE 2 (parked disabled) · PENDING 2 (parked product) · DISCOVERED 1985.
- Next (not this ticket): SOURCE_FACT on remaining HIGH/MEDIUM index-options, including the 12 new IDs. No strategies. No live Dhan.

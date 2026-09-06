# Stage 1 YouTube extractor

Public catalog + captions. No Dhan trading APIs. No strategy design.

**Channels:** [`config/workspace.yaml`](../../../../config/workspace.yaml) `sources.youtube[]` (default enabled: `@DhanHQ`). Disabled rows are not scraped.

Secrets: repo-root `.env` only (`YOUTUBE_API_KEY`). This code never prints or writes the key. The yaml lists `${YOUTUBE_API_KEY}` as a *name*; the value stays in `.env`.

## Setup

```bash
cd /Users/sahiltayde/Documents/all_about_dhan/teams/01_research/youtube
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Confirm `YOUTUBE_API_KEY` is set in `/Users/sahiltayde/Documents/all_about_dhan/.env` (gitignored). Do not paste it into chat.

## Commands

Run from `teams/01_research/youtube` so `python -m src` resolves.

```bash
python -m src show-config
python -m src validate-key
python -m src catalog
python -m src retag
python -m src transcripts --cap 40
python -m src topics
python -m src run --cap 40
```

`show-config` loads yaml only (no API). `topics` clusters the existing catalog into per-topic stubs under `teams/04_quant/docs/topics/` (no scrape). `run` is validate-key → catalog (enabled sources) → transcripts for the popular HIGH/MEDIUM set.

Optional `--cap` limits caption fetches (default 40, or `YOUTUBE_TRANSCRIPT_CAP`). PLAN seed videos are included when they appear in the catalog and are not `EXCLUDED_STOCK_ONLY`.

Follow-up (does not re-run catalog):

```bash
python -m src transcripts --retry-pending --english
python -m src transcripts --english --english-cap 40
```

`--retry-pending` parks unrelated pending/IP-blocked IDs and retries the F&O/strategy-related ones with User-Agent, delay, and backoff. `--english` stores YouTube English companions (`tlang=en` auto-translate if no native English track). Hindi source files are not overwritten. No LLM translation.

## Modules

| Module | Role |
|--------|------|
| `config.py` | `config/workspace.yaml` + repo-root `.env`; paths, popularity weights |
| `sanitize.py` | Redact keys from any log/error text |
| `youtube_client.py` | Data API v3 client (pause + retries; quota unit counter) |
| `discovery.py` | Enabled-source playlists + uploads → video records (`source_id` tagged) |
| `topics.py` | Cluster catalog tags → per-topic stub markdown |
| `popularity.py` | `PopularityScore` (log1p min-max views/likes/comments + recency) |
| `relevance.py` | HIGH/MEDIUM/LOW, `STOCK_ONLY` / `EXCLUDED_STOCK_ONLY` (rows kept) |
| `transcripts.py` | Public captions via `youtube-transcript-api` (backoff / User-Agent) |
| `caption_http.py` | Timedtext session, 429/bot-detection backoff |
| `english.py` | YouTube English track or `tlang=en` translate (no LLM) |
| `park.py` | Park unrelated pending/blocked IDs for tomorrow |
| `transcript_qa.py` | Flags; `[UNCERTAIN_TRANSCRIPT]`; never invents captions |
| `catalog_io.py` | `video_catalog.csv` / `.json` |
| `cli.py` | Entrypoint |

## Outputs

- `data/youtube/video_catalog.csv`
- `data/youtube/video_catalog.json`
- `data/transcripts/raw/<video_id>.json`
- `data/transcripts/normalized/<video_id>.md`
- `data/youtube/external_candidates.md` (stub; no fetch of disabled yaml rows)
- `teams/01_research/youtube/docs/RUN_REPORT.md`
- `teams/04_quant/docs/topics/` (per-topic stubs from `python -m src topics`)

Payloads under `data/` are gitignored.

## Env (optional)

Names only; values stay in `.env`:

- `YOUTUBE_API_KEY` (required)
- `YOUTUBE_TRANSCRIPT_CAP`
- `YOUTUBE_POPULARITY_W_VIEWS` `YOUTUBE_POPULARITY_W_LIKES` `YOUTUBE_POPULARITY_W_COMMENTS` `YOUTUBE_POPULARITY_W_RECENCY`
- `YOUTUBE_RECENCY_HALF_LIFE_DAYS`
- `YOUTUBE_REQUEST_PAUSE`
- `YOUTUBE_TRANSCRIPT_PAUSE`
- `YOUTUBE_TRANSCRIPT_RETRY_PAUSE`
- `YOUTUBE_TRANSCRIPT_BACKOFF`
- `YOUTUBE_TRANSCRIPT_BACKOFF_ATTEMPTS`

## Source policy

Live list: `config/workspace.yaml`. Default: official `@DhanHQ` playlists. The uploads playlist is merged so videos not on a named playlist still appear. Non-Dhan enabled sources are tagged `EXTERNAL_RESEARCH`. Disabled example rows are not fetched.

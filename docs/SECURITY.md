# docs/SECURITY.md — tokens and secrets

## Where secrets live

- **Allowed:** local `.env` (gitignored), `secrets/` (gitignored), later a secret manager.
- **Forbidden:** git, chat, Cursor prompts, notebooks checked in, `AGENT.md`, research markdown, screenshots of keys.

Copy [`.env.example`](../.env.example) → `.env` and fill values locally. Example file has **names only**.

**URLs and books** live in [`config/workspace.yaml`](../config/workspace.yaml) (the customer master file). That yaml lists secret *variable names* and may use `${YOUTUBE_API_KEY}` interpolation from `.env`. Do not put key values in the yaml. Optional gitignored overlay: `config/workspace.local.yaml`.

---

## DhanHQ

- Use `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`, and only the refresh fields Dhan currently documents (`DHAN_REFRESH_TOKEN`, `DHAN_CLIENT_SECRET` as needed).
- **Never paste Dhan tokens into chat or an LLM prompt.** If an agent needs to call the API, it reads the environment on the machine — it does not need you to echo the token.
- Access tokens expire; follow Dhan's current refresh/expiry docs in Phase 1. Do not hardcode a token in `packages/dhan-client`.
- Broker is Dhan / DhanHQ **only**. No other broker credentials in this repo.

---

## YouTube

- `YOUTUBE_API_KEY` is a Google YouTube Data API v3 key for **public** catalog (videos, playlists, stats).
- **Where:** repo-root `.env` only — `/Users/sahiltayde/Documents/all_about_dhan/.env` (gitignored). Copy from [`.env.example`](../.env.example) if needed.
- **How to create it:** numbered steps in [`teams/01_research/youtube/README.md`](../teams/01_research/youtube/README.md). Restrict the key to YouTube Data API v3.
- **Never** commit the key, paste it into chat/Cursor/LLM prompts, or put it in markdown, notebooks, or screenshots.
- Public captions via `youtube-transcript-api` usually need **no** extra key. If captions fail, we may ask for a logged-in cookie later — do not volunteer cookies until then.
- Channel scope: enabled rows in [`config/workspace.yaml`](../config/workspace.yaml). Default is official [`@DhanHQ`](https://www.youtube.com/@DhanHQ) (`TIER_1`). Non-Dhan rows are `EXTERNAL_RESEARCH` and stay disabled until the customer enables them.

---

## Data payloads

Catalogs and transcripts under `data/` are gitignored. Do not commit dumps that include account-specific API responses or tokens.

---

## Agents

- Do not print env values, `.env` contents, or files under `secrets/`.
- If a secret was pasted into a transcript or log, treat it as leaked: rotate, do not commit the log.

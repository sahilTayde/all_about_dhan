# YouTube Data API v3 key

**Customer master file (URLs / books / which channel):** [`config/workspace.yaml`](../../../config/workspace.yaml). Change a URL and `enabled` there to switch source. Keys stay in `.env`.

Default enabled channel: [https://www.youtube.com/@DhanHQ](https://www.youtube.com/@DhanHQ) (`TIER_1`). Disabled examples (Zerodha, etc.) are **not** scraped until `enabled: true`. Non-Dhan rows are `EXTERNAL_RESEARCH`.

**Paste the key only in the repo-root `.env` file. Never paste it in chat, Cursor, git, or this README.**

Day-to-day extraction contract: [`ANALYSIS.md`](ANALYSIS.md). Full spec: [`PLAN.md`](PLAN.md). Collector: [`src/README.md`](src/README.md).

---

## Where the key goes

| Item | Value |
|------|--------|
| File | `/Users/sahiltayde/Documents/all_about_dhan/.env` (repo root, gitignored) |
| Variable | `YOUTUBE_API_KEY` |
| Template | copy [`.env.example`](../../../.env.example) → `.env` if `.env` does not exist yet |

After you save `.env`, tell an agent only that the key is in `.env`. Do not send the value.

Rules: [`docs/SECURITY.md`](../../../docs/SECURITY.md).

---

## Create the key (do this yourself)

1. Open [Google Cloud Console](https://console.cloud.google.com/) and sign in.
2. Create a project (or select an existing one) in the project picker at the top.
3. Enable **YouTube Data API v3**: [APIs & Services → Library → YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com) → **Enable**.
4. Open [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials) → **Create credentials** → **API key**.
5. Restrict the key: open the new key → **API restrictions** → restrict to **YouTube Data API v3** → **Save**. (Optional later: IP / app restriction. Do not put the key in client-side web code.)
6. In a terminal at the repo root, if you do not already have `.env`:

   ```bash
   cd /Users/sahiltayde/Documents/all_about_dhan
   cp .env.example .env
   ```

7. Open `/Users/sahiltayde/Documents/all_about_dhan/.env` in an editor and set:

   ```bash
   YOUTUBE_API_KEY=paste_the_key_here
   ```

   Save the file. Do not commit `.env`. Do not paste that line into chat.

8. In chat, say only: the YouTube key is in repo-root `.env`. Confirm enabled channels via `config/workspace.yaml` (default `@DhanHQ`). Do not paste the key.

# Dhan ecosystem — URL classification

This file classifies official Dhan surfaces for **all_about_dhan**. It is not a strategy source.

**Rule:** promo, download, community, social, contact, and lead forms are **not** strategy evidence. Charts, ScanX, Options Trader, and the Indicator newsletter are **Tier 2 secondary references** — they cannot replace official `@DhanHQ` transcripts. Production indicators remain Dhan-only (`SOURCE_FACT` from `@DhanHQ` + independent `VALIDATION`) unless `config/workspace.yaml` `implementation.indicators` is not `dhan_only`.

Live YouTube handles/URLs: [`config/workspace.yaml`](../../../config/workspace.yaml) — **that is the file customers change**. This document still classifies Dhan *ecosystem* URLs. Canonical hierarchy: [`docs/RESEARCH.md`](../../../docs/RESEARCH.md) (addendum). Day-to-day extraction: [`../youtube/ANALYSIS.md`](../youtube/ANALYSIS.md). Do **not** treat this file as permission to scrape YouTube.

---

## Classes

| Class | Use |
|-------|-----|
| `TIER_1` | Official `@DhanHQ` playlists/videos only. Sole source for Dhan-video transcript extraction. |
| `TIER_2_SECONDARY` | Official Dhan product or docs. May inform *how a Dhan tool works*. Never a silent substitute for a transcript. Never a profitability claim. |
| `NOT_EVIDENCE` | Marketing, downloads, community, social, contact, forms. Do not cite as strategy rules, indicator params, or “Dhan recommends.” |

User-approved `EXTERNAL_RESEARCH` videos (Tier 3) are listed in [`config/workspace.yaml`](../../../config/workspace.yaml) and stay `enabled: false` until the customer turns them on. When enabled they must be tagged `EXTERNAL_RESEARCH`; ideas only; they must not replace `@DhanHQ` transcripts as Dhan production `SOURCE_FACT`.

---

## Tier 1 — transcripts (pointer only)

| URL | Class | Notes |
|-----|-------|--------|
| https://www.youtube.com/@DhanHQ | `TIER_1` | Official channel. |
| https://www.youtube.com/@DhanHQ/playlists | `TIER_1` | Playlist index for catalog discovery. |

No other YouTube channel is Tier 1.

---

## Tier 2 — official product / docs (secondary)

Cannot replace `@DhanHQ` transcripts. Do not scrape these as if they were education transcripts.

| Surface | URL | Class | Notes |
|---------|-----|-------|--------|
| DhanHQ API docs | https://dhanhq.co/docs/v2/ | `TIER_2_SECONDARY` | Existing official API starting point (also live-market-feed, historical-data, option-chain, **conditional-trigger**, Python SDK under the same docs family). Use for endpoints, auth, data shapes — not for strategy rules. **Indicator names** live in Annexure + Conditional Trigger only; charts are OHLC. Clubbed catalog: [`DHAN_OFFICIAL_INDICATORS.md`](DHAN_OFFICIAL_INDICATORS.md). |
| API portal | https://dhanhq.co/ | `TIER_2_SECONDARY` | Product/docs home for DhanHQ APIs. |
| ScanX (product) | https://scanx.trade/ | `TIER_2_SECONDARY` | Screener / live-market product. Secondary reference for *what ScanX shows*, not for entry/exit rules. |
| ScanX shortlink | https://bit.ly/scanxtrade | `NOT_EVIDENCE` | Marketing redirect. Cite `scanx.trade` if the product is in scope; never cite the shortlink as evidence. |
| ScanX marketing page | https://dhan.co/scanx-stock-screener/ | `NOT_EVIDENCE` | Promo copy. |
| Charts (TradingView-in-Dhan) | https://tv.dhan.co/ | `TIER_2_SECONDARY` | Live charting surface. Secondary for indicator *availability* on Dhan charts; spoken params still come from transcripts. |
| Charts marketing | https://dhan.co/tradingview/ | `NOT_EVIDENCE` | Promo for tv.dhan.co. |
| Options Trader (live product) | Options Trader app / Options Trader Web (logged-in F&O UI) | `TIER_2_SECONDARY` | Chain, builder, F&O UI. Secondary for *what the product shows*. Not a transcript. |
| Options Trader marketing | https://dhan.co/options-trader/ · https://dhan.co/options-trader-web/ | `NOT_EVIDENCE` | Promo + download/QR. Do not cite marketing copy as rules. |
| Indicator newsletter | https://thetradingnewsletter.substack.com/ | `TIER_2_SECONDARY` | “Indicator by Dhan.” Education-adjacent; secondary only. Education ≠ advice. Cannot replace `@DhanHQ` transcripts. Tag claims `NEWSLETTER` if extracted later. |

---

## Not strategy evidence

Never treat these as claims, rules, parameters, or expert endorsement.

### Marketing / home / contact

| URL | Class | Notes |
|-----|-------|--------|
| https://dhan.co/ | `NOT_EVIDENCE` | Brand/marketing home. |
| https://dhan.co/contact/ | `NOT_EVIDENCE` | Support/contact. |
| https://forms.gle/VQ57zffKpEiqentf7 | `NOT_EVIDENCE` | MTF sheet form. Marketing lead-gen. Ignore for strategies. |

### Downloads / stores / installers

| URL | Class | Notes |
|-----|-------|--------|
| https://dhan.co/trading-app/ | `NOT_EVIDENCE` | App download marketing. |
| https://play.google.com/store/apps/details?id=com.dhan.live | `NOT_EVIDENCE` | Play Store listing. |
| https://apps.apple.com/us/app/dhan-share-market-trading-app/id1575318726 | `NOT_EVIDENCE` | iOS App Store listing. |
| Options Trader store / QR / invite links | `NOT_EVIDENCE` | Any “download Options Trader” link. The **running product** is Tier 2 secondary; the installer is not. |
| https://web.dhan.co/ | `NOT_EVIDENCE` *for strategies* | Web trading login/UI. Not a transcript source. Do not scrape account UI for rules. |
| https://dext.dhan.co/ | `NOT_EVIDENCE` | DEXT T3 browser terminal (product/install path). Not strategy evidence. |
| https://dhan.co/dext-t3-trading-terminal/ | `NOT_EVIDENCE` | DEXT T3 marketing. |
| https://terminal-dext.dhan.co/Dext.dmg | `NOT_EVIDENCE` | macOS installer. |
| https://terminal-dext.dhan.co/Dext.exe | `NOT_EVIDENCE` | Windows installer. |
| https://dhan.co/ticker/ | `NOT_EVIDENCE` | Desktop ticker product/download. Watchlist UI, not education. |

### Broker connect (not education)

| URL | Class | Notes |
|-----|-------|--------|
| Connect Dhan → TradingView (tradingview.com broker integration) | `NOT_EVIDENCE` | Order-routing integration. Not a strategy source. Marketing: https://dhan.co/tradingview/ |

### Community / social

| URL | Class | Notes |
|-----|-------|--------|
| https://madefortrade.in/ | `NOT_EVIDENCE` | Community forum. User posts and staff replies are not `@DhanHQ` transcripts. |
| https://x.com/DhanHQ · https://twitter.com/DhanHQ | `NOT_EVIDENCE` | X/Twitter `@DhanHQ`. |
| https://www.instagram.com/dhanhq/ | `NOT_EVIDENCE` | Instagram. |
| https://www.linkedin.com/company/dhanhq | `NOT_EVIDENCE` | LinkedIn. |
| https://www.facebook.com/DhanHQ | `NOT_EVIDENCE` | Facebook. |
| https://t.me/JoinDhan | `NOT_EVIDENCE` | Official Telegram. Social posts are not claims. |

---

## What agents must not do

- Do not scrape YouTube from this document.
- Do not invent transcripts from titles, social posts, app-store copy, or newsletter headlines.
- Do not implement a scraper here (owned elsewhere).
- Do not promote downloads, MTF, or community as research outputs.
- If a product UI and a `@DhanHQ` transcript disagree: keep both layers (`SOURCE_FACT` vs product observation); do not overwrite the transcript.

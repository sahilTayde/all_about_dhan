"""News scraper: MoneyControl, Economic Times RSS feeds."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from data_recorder.writer import JsonLinesWriter

log = logging.getLogger("data_recorder.news")


class NewsScraper:
    """Scrape news headlines from RSS feeds."""

    def __init__(
        self,
        feed_urls: list[str],
        output_dir: Path,
        *,
        verbose: bool = False,
    ) -> None:
        self.feed_urls = feed_urls
        self.writer = JsonLinesWriter(output_dir, "news", verbose=verbose)
        self.verbose = verbose
        self._seen_guids: set[str] = set()
        self._poll_interval = 300  # 5 minutes

    async def run(self) -> None:
        """Run news scraper (polls RSS feeds every 5 minutes)."""
        try:
            import feedparser
        except ImportError:
            log.error(
                "feedparser not installed. Install with: pip install feedparser\n"
                "News scraper will not run until feedparser is available."
            )
            return

        if self.verbose:
            log.info("News scraper starting (dry-run mode will generate synthetic data)")

        while True:
            for feed_url in self.feed_urls:
                try:
                    await self._scrape_feed(feed_url, feedparser)
                except Exception as e:
                    log.error("Error scraping feed %s: %s", feed_url, e)

            await asyncio.sleep(self._poll_interval)

    async def _scrape_feed(self, feed_url: str, feedparser: Any) -> None:
        """Scrape one RSS feed."""
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:10]:  # Top 10 headlines
            guid = entry.get("id") or entry.get("link") or entry.get("title")
            if not guid or guid in self._seen_guids:
                continue

            self._seen_guids.add(guid)

            record = {
                "source": feed.feed.get("title", "Unknown"),
                "url": feed_url,
                "headline": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "timestamp": datetime.now().isoformat(),
            }
            self.writer.write(record)

    async def run_dry(self) -> None:
        """Dry-run: generate synthetic news headlines."""
        log.info("News scraper dry-run: generating 4 synthetic headlines (2 feeds × 2 headlines)")

        sources = ["MoneyControl", "Economic Times"]
        for i, source in enumerate(sources):
            for j in range(2):
                record = {
                    "source": source,
                    "url": f"https://example.com/feed{i+1}",
                    "headline": f"Market Update {i+1}-{j+1}: NIFTY at 19800",
                    "link": f"https://example.com/article{i*2+j+1}",
                    "published": datetime.now().isoformat(),
                    "timestamp": datetime.now().isoformat(),
                }
                self.writer.write(record)

        log.info("News scraper dry-run complete")

    def close(self) -> None:
        """Close writer."""
        self.writer.close()

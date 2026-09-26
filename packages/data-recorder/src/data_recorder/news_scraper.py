"""News scraper (RSS feeds from MoneyControl, Economic Times)."""

from datetime import datetime
from typing import Dict, Any
import hashlib
import time

from .writer import DailyJSONLWriter
from .config import RecorderConfig


class NewsScraper:
    """
    Scrapes news headlines from RSS feeds.
    
    In production: Uses feedparser library (lightweight RSS parser).
    In dry-run: Generates synthetic headlines.
    """
    
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.writer = DailyJSONLWriter(config.base_path, "news")
        self.feeds = config.news_feeds
    
    def start(self) -> None:
        """Run once (scrape all feeds, write headlines)."""
        if self.config.dry_run:
            self._dry_run_mode()
        else:
            self._production_mode()
    
    def _production_mode(self) -> None:
        """Production mode stub."""
        raise NotImplementedError(
            "Production mode requires feedparser library. "
            "To implement: "
            "1. pip install feedparser "
            "2. For each feed in self.feeds: "
            "   import feedparser "
            "   feed_data = feedparser.parse(feed['url']) "
            "   for entry in feed_data.entries: "
            "       headline = { "
            "           'news_id': hash(entry.link), "
            "           'timestamp': entry.published_parsed (convert to ISO), "
            "           'source': feed['name'], "
            "           'headline': entry.title, "
            "           'url': entry.link, "
            "           'sentiment': None,  # To be computed later (keyword heuristic or LLM) "
            "           'relevance': None,  # To be tagged later "
            "           'event_tags': None "
            "       } "
            "       self.writer.write(headline) "
        )
    
    def _dry_run_mode(self) -> None:
        if self.config.verbose:
            print(f"[NewsScraper] Dry-run mode: generating {len(self.feeds) * 2} synthetic headlines...")
        
        timestamp = datetime.now()
        
        for feed in self.feeds:
            for i in range(2):  # 2 headlines per feed
                headline_text = f"{feed['name']} headline {i+1}: Market {['rallies', 'falls'][i]} on global cues"
                news_id = hashlib.md5((feed['url'] + headline_text).encode()).hexdigest()[:16]
                
                headline = {
                    "news_id": news_id,
                    "timestamp": timestamp.isoformat(),
                    "source": feed['name'],
                    "headline": headline_text,
                    "url": f"{feed['url']}/article/{i+1}",
                    "sentiment": None,  # To be computed in nightly ETL (keyword heuristic or LLM)
                    "relevance": None,
                    "event_tags": None
                }
                self.writer.write(headline)
                time.sleep(0.05)
        
        if self.config.verbose:
            print(f"[NewsScraper] Dry-run complete. {self.writer.records_written} headlines written.")
    
    def stop(self) -> None:
        self.writer.close()
        if self.config.verbose:
            print(f"[NewsScraper] Stopped. Total headlines: {self.writer.records_written}")

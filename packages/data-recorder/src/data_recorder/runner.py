"""Main runner: orchestrates all recorders + health heartbeat."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dhan_client.client import DhanClient

from data_recorder.config import RecorderConfig, load_config
from data_recorder.futures_recorder import FuturesRecorder
from data_recorder.global_fetcher import GlobalFetcher
from data_recorder.heavyweight_recorder import HeavyweightRecorder
from data_recorder.index_recorder import IndexRecorder
from data_recorder.news_scraper import NewsScraper
from data_recorder.option_chain_recorder import OptionChainRecorder

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("data_recorder.runner")


class DataRecorderRunner:
    """Orchestrates all market data recorders."""

    def __init__(
        self,
        config: Optional[RecorderConfig] = None,
        *,
        dry_run: Optional[bool] = None,
        verbose: bool = False,
    ) -> None:
        if config is None:
            config = load_config(dry_run=dry_run, verbose=verbose)
        elif dry_run is not None:
            config.dry_run = dry_run

        self.config = config
        self.client = DhanClient(dry_run=config.dry_run)
        self.recorders: list[Any] = []
        self._shutdown = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown on SIGINT/SIGTERM."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        log.info("Received signal %d, shutting down gracefully...", signum)
        self._shutdown = True

    async def _write_heartbeat(self) -> None:
        """Write health heartbeat every minute."""
        heartbeat_file = self.config.output_dir / "recorder_heartbeat.jsonl"
        heartbeat_file.parent.mkdir(parents=True, exist_ok=True)

        while not self._shutdown:
            heartbeat = {
                "timestamp": datetime.now().isoformat(),
                "status": "running",
                "dry_run": self.config.dry_run,
            }

            # Append heartbeat
            with open(heartbeat_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(heartbeat) + "\n")
                f.flush()

            await asyncio.sleep(self.config.heartbeat_interval)

    async def run_async(self) -> None:
        """Run all recorders asynchronously."""
        log.info(
            "Data recorder starting (dry_run=%s, output_dir=%s)",
            self.config.dry_run,
            self.config.output_dir,
        )

        # Create all recorders
        index_rec = IndexRecorder(
            self.client,
            self.config.index_symbols,
            self.config.output_dir,
            verbose=self.config.verbose,
        )
        futures_rec = FuturesRecorder(
            self.client,
            self.config.futures_symbols,
            self.config.output_dir,
            verbose=self.config.verbose,
        )
        chain_rec = OptionChainRecorder(
            self.client,
            self.config.option_chain_underlyings,
            self.config.output_dir,
            verbose=self.config.verbose,
        )
        heavyweight_rec = HeavyweightRecorder(
            self.client,
            self.config.heavyweight_symbols,
            self.config.output_dir,
            verbose=self.config.verbose,
        )
        news_scraper = NewsScraper(
            self.config.news_feeds,
            self.config.output_dir,
            verbose=self.config.verbose,
        )
        global_fetcher = GlobalFetcher(
            self.config.global_symbols,
            self.config.output_dir,
            verbose=self.config.verbose,
        )

        self.recorders = [
            index_rec,
            futures_rec,
            chain_rec,
            heavyweight_rec,
            news_scraper,
            global_fetcher,
        ]

        # Run in dry-run mode or production mode
        if self.config.dry_run:
            log.info("Running in DRY-RUN mode (synthetic data only)")
            await self._run_dry_mode()
        else:
            log.info("Running in PRODUCTION mode (live Dhan API)")
            await self._run_production_mode()

    async def _run_dry_mode(self) -> None:
        """Run dry-run mode (synchronous, quick test)."""
        index_rec, futures_rec, chain_rec, heavyweight_rec, news_scraper, global_fetcher = (
            self.recorders
        )

        # Run each recorder's dry-run sequentially
        await index_rec._run_dry()
        await futures_rec._run_dry()
        await chain_rec._run_dry()
        await heavyweight_rec._run_dry()
        await news_scraper.run_dry()
        await global_fetcher.run_dry()

        # Close all writers
        for recorder in self.recorders:
            recorder.close()

        self.client.close()
        log.info("Dry-run complete. Check output files in %s", self.config.output_dir)

    async def _run_production_mode(self) -> None:
        """Run production mode (continuous, all recorders concurrently)."""
        index_rec, futures_rec, chain_rec, heavyweight_rec, news_scraper, global_fetcher = (
            self.recorders
        )

        # Run all recorders + heartbeat concurrently
        tasks = [
            asyncio.create_task(index_rec.run()),
            asyncio.create_task(futures_rec.run()),
            asyncio.create_task(chain_rec.run()),
            asyncio.create_task(heavyweight_rec.run()),
            asyncio.create_task(news_scraper.run()),
            asyncio.create_task(global_fetcher.run()),
            asyncio.create_task(self._write_heartbeat()),
        ]

        try:
            # Wait for shutdown signal
            while not self._shutdown:
                await asyncio.sleep(1)

            # Cancel all tasks
            log.info("Cancelling all recorder tasks...")
            for task in tasks:
                task.cancel()

            # Wait for tasks to complete cancellation
            await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            # Close all writers
            for recorder in self.recorders:
                recorder.close()

            self.client.close()
            log.info("Data recorder stopped")

    def start(self) -> None:
        """Start the recorder (blocking)."""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            log.info("Interrupted by user")
            sys.exit(0)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="DhanHQ market data recorder")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run in dry-run mode (synthetic data)"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    runner = DataRecorderRunner(dry_run=args.dry_run, verbose=args.verbose)
    runner.start()


if __name__ == "__main__":
    main()

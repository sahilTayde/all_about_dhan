"""Main runner for all data recorders."""

import signal
import sys
from typing import List

from .config import get_config
from .index_recorder import IndexRecorder
from .futures_recorder import FuturesRecorder
from .option_chain_recorder import OptionChainRecorder
from .heavyweight_recorder import HeavyweightRecorder
from .news_scraper import NewsScraper
from .global_fetcher import GlobalFetcher


class DataRecorderRunner:
    """
    Orchestrates all data recorders.
    
    Runs independently of trading loop (crash in one doesn't affect the other).
    Lightweight (minimal CPU/memory), writes to gitignored data/ directory.
    """
    
    def __init__(self, dry_run: bool = False, verbose: bool = True):
        config = get_config()
        config.dry_run = dry_run
        config.verbose = verbose
        
        self.config = config
        self.recorders: List = []
        self.running = False
        
        # Initialize all recorders
        self.index_recorder = IndexRecorder(config)
        self.futures_recorder = FuturesRecorder(config)
        self.option_chain_recorder = OptionChainRecorder(config)
        self.heavyweight_recorder = HeavyweightRecorder(config)
        self.news_scraper = NewsScraper(config)
        self.global_fetcher = GlobalFetcher(config)
        
        self.recorders = [
            self.index_recorder,
            self.futures_recorder,
            self.option_chain_recorder,
            self.heavyweight_recorder,
            self.news_scraper,
            self.global_fetcher
        ]
    
    def start(self) -> None:
        """Start all recorders."""
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        if self.config.verbose:
            print("[DataRecorderRunner] Starting all recorders...")
            print(f"[DataRecorderRunner] Mode: {'DRY-RUN' if self.config.dry_run else 'PRODUCTION'}")
            print(f"[DataRecorderRunner] Output: {self.config.base_path}/")
        
        try:
            # In dry-run, recorders run once and exit
            # In production, index/futures/option/heavyweight would run in loops
            # For simplicity, run sequentially in dry-run
            for recorder in self.recorders:
                if not self.running:
                    break
                recorder.start()
        
        except Exception as e:
            print(f"[DataRecorderRunner] ERROR: {e}", file=sys.stderr)
            raise
        
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop all recorders and close files."""
        if self.config.verbose:
            print("[DataRecorderRunner] Stopping all recorders...")
        
        for recorder in self.recorders:
            try:
                recorder.stop()
            except Exception as e:
                print(f"[DataRecorderRunner] Error stopping recorder: {e}", file=sys.stderr)
        
        self.running = False
        if self.config.verbose:
            print("[DataRecorderRunner] All recorders stopped.")
    
    def _signal_handler(self, signum, frame):
        """Handle SIGINT (Ctrl+C) and SIGTERM gracefully."""
        print(f"\n[DataRecorderRunner] Received signal {signum}. Shutting down...")
        self.running = False
        self.stop()
        sys.exit(0)


def main(dry_run: bool = False):
    """CLI entry point."""
    runner = DataRecorderRunner(dry_run=dry_run)
    runner.start()


if __name__ == "__main__":
    # Default: dry-run mode (safe for testing without credentials)
    # To run production mode: python -m data_recorder.runner --production
    import sys
    dry_run = "--production" not in sys.argv
    main(dry_run=dry_run)

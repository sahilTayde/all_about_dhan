"""Tests for dry-run mode (synthetic data generation)."""

import json
import tempfile
from pathlib import Path
from datetime import date

from data_recorder.config import RecorderConfig
from data_recorder.index_recorder import IndexRecorder
from data_recorder.futures_recorder import FuturesRecorder
from data_recorder.option_chain_recorder import OptionChainRecorder
from data_recorder.heavyweight_recorder import HeavyweightRecorder
from data_recorder.news_scraper import NewsScraper
from data_recorder.global_fetcher import GlobalFetcher


def test_index_recorder_dry_run():
    """Test IndexRecorder generates synthetic data in dry-run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = RecorderConfig(base_path=Path(tmpdir), dry_run=True, verbose=False)
        recorder = IndexRecorder(config)
        
        recorder.start()
        recorder.stop()
        
        # Check file created
        today = date.today()
        filepath = Path(tmpdir) / "index_ticks" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert filepath.exists()
        
        # Check content (should have 3 symbols × 2 minutes = 6 ticks)
        with open(filepath, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 6
        
        # Check schema
        for line in lines:
            tick = json.loads(line)
            assert "symbol" in tick
            assert "timestamp" in tick
            assert "open" in tick
            assert "high" in tick
            assert "low" in tick
            assert "close" in tick
            assert "volume" in tick  # May be None for spot index
            assert tick["symbol"] in config.index_symbols


def test_futures_recorder_dry_run():
    """Test FuturesRecorder generates synthetic data with volume."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = RecorderConfig(base_path=Path(tmpdir), dry_run=True, verbose=False)
        recorder = FuturesRecorder(config)
        
        recorder.start()
        recorder.stop()
        
        # Check file
        today = date.today()
        filepath = Path(tmpdir) / "futures_ticks" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert filepath.exists()
        
        # Check content
        with open(filepath, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 6  # 3 symbols × 2 minutes
        
        # Check volume field (CRITICAL: must not be None)
        for line in lines:
            tick = json.loads(line)
            assert tick["volume"] is not None
            assert tick["volume"] > 0
            assert "open_interest" in tick


def test_option_chain_recorder_dry_run():
    """Test OptionChainRecorder generates synthetic chain."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = RecorderConfig(base_path=Path(tmpdir), dry_run=True, verbose=False)
        recorder = OptionChainRecorder(config)
        
        recorder.start()
        recorder.stop()
        
        # Check file
        today = date.today()
        filepath = Path(tmpdir) / "option_chain" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert filepath.exists()
        
        # Check content (3 strikes × 2 types CE/PE = 6 options)
        with open(filepath, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 6
        
        # Check schema (OI, IV, greeks are CRITICAL)
        for line in lines:
            option = json.loads(line)
            assert "underlying" in option
            assert "expiry" in option
            assert "strike" in option
            assert "option_type" in option
            assert option["option_type"] in ["CE", "PE"]
            assert "ltp" in option
            assert "open_interest" in option
            assert option["open_interest"] is not None
            assert "iv" in option  # Implied volatility
            assert "delta" in option
            assert "gamma" in option
            assert "theta" in option
            assert "vega" in option


def test_heavyweight_recorder_dry_run():
    """Test HeavyweightRecorder generates synthetic heavyweight ticks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = RecorderConfig(base_path=Path(tmpdir), dry_run=True, verbose=False)
        recorder = HeavyweightRecorder(config)
        
        recorder.start()
        recorder.stop()
        
        # Check file
        today = date.today()
        filepath = Path(tmpdir) / "heavyweight_ticks" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert filepath.exists()
        
        # Check content (15 stocks × 2 minutes = 30 ticks)
        with open(filepath, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 30
        
        # Check schema
        for line in lines:
            tick = json.loads(line)
            assert "symbol" in tick
            assert "timestamp" in tick
            assert "ltp" in tick
            assert "volume" in tick
            assert tick["symbol"] in config.heavyweight_symbols


def test_news_scraper_dry_run():
    """Test NewsScraper generates synthetic headlines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = RecorderConfig(base_path=Path(tmpdir), dry_run=True, verbose=False)
        scraper = NewsScraper(config)
        
        scraper.start()
        scraper.stop()
        
        # Check file
        today = date.today()
        filepath = Path(tmpdir) / "news" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert filepath.exists()
        
        # Check content (2 feeds × 2 headlines = 4 headlines)
        with open(filepath, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 4
        
        # Check schema
        for line in lines:
            headline = json.loads(line)
            assert "news_id" in headline
            assert "timestamp" in headline
            assert "source" in headline
            assert "headline" in headline
            assert "url" in headline
            assert headline["source"] in ["MoneyControl", "EconomicTimes"]


def test_global_fetcher_dry_run():
    """Test GlobalFetcher generates synthetic global market data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = RecorderConfig(base_path=Path(tmpdir), dry_run=True, verbose=False)
        fetcher = GlobalFetcher(config)
        
        fetcher.start()
        fetcher.stop()
        
        # Check file
        today = date.today()
        filepath = Path(tmpdir) / "global_markets" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert filepath.exists()
        
        # Check content (7 symbols)
        with open(filepath, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 7
        
        # Check schema
        for line in lines:
            data = json.loads(line)
            assert "symbol" in data
            assert "date" in data
            assert "close" in data
            assert "change_pct" in data
            assert data["symbol"] in config.global_symbols

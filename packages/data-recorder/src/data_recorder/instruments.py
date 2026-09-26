"""Instrument lookup with daily cache: futures, indices, heavyweights.

Parses Dhan scrip master CSV and caches results for the day.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient

log = logging.getLogger("data_recorder.instruments")

IST = timezone(timedelta(hours=5, minutes=30))


def ist_date_str() -> str:
    """Current IST date as YYYYMMDD."""
    return datetime.now(IST).strftime("%Y%m%d")


def _parse_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """Normalize CSV row keys (handle column name variations)."""
    # Security ID column candidates
    sec_id = (
        row.get("SEM_SMST_SECURITY_ID")
        or row.get("SECURITY_ID")
        or row.get("SEM_SECURITY_ID")
        or row.get("SMST_SECURITY_ID")
    )

    return {
        "security_id": int(sec_id) if sec_id and sec_id.strip() else None,
        "symbol": (
            row.get("SEM_CUSTOM_SYMBOL")
            or row.get("DISPLAY_NAME")
            or row.get("SM_SYMBOL_NAME")
            or ""
        ).strip(),
        "trading_symbol": (row.get("SM_SYMBOL_NAME") or row.get("SYMBOL_NAME") or "").strip(),
        "segment": (row.get("SEM_SEGMENT") or row.get("SEGMENT") or "").strip(),
        "instrument_type": (
            row.get("SEM_EXCH_INSTRUMENT_TYPE") or row.get("INSTRUMENT_TYPE") or ""
        ).strip(),
        "expiry": (row.get("SEM_EXPIRY_DATE") or row.get("SM_EXPIRY_DATE") or "").strip(),
    }


def _is_last_week_of_month(date: datetime) -> bool:
    """Check if date is in the last 7 days of the month (rollover period)."""
    next_month = date.replace(day=28) + timedelta(days=4)
    last_day = (next_month - timedelta(days=next_month.day)).day
    return date.day > last_day - 7


def _current_and_next_month_expiry() -> tuple[str, str]:
    """Get current and next month expiry dates (YYYY-MM-DD).
    
    Returns (current_month_expiry, next_month_expiry) for rollover handling.
    NSE futures expire on the last Thursday of the month.
    """
    today = datetime.now(IST)
    
    # Find last Thursday of current month
    current_month_last = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    current_thursday = current_month_last
    while current_thursday.weekday() != 3:  # 3 = Thursday
        current_thursday -= timedelta(days=1)
    
    # Find last Thursday of next month
    next_month_first = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    next_month_last = (next_month_first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    next_thursday = next_month_last
    while next_thursday.weekday() != 3:
        next_thursday -= timedelta(days=1)
    
    return current_thursday.strftime("%Y-%m-%d"), next_thursday.strftime("%Y-%m-%d")


def parse_instruments(csv_text: str) -> dict[str, Any]:
    """Parse scrip master CSV and extract indices, futures, heavyweights.
    
    Returns:
        {
            "indices": {"NIFTY": 13, "BANKNIFTY": 25, "SENSEX": 51},
            "futures": {
                "NIFTYFUT": {"security_id": 123, "expiry": "2026-09-24"},
                "BANKNIFTYFUT": {"security_id": 456, "expiry": "2026-09-24"},
                ...
            },
            "heavyweights": {"RELIANCE": 234, "TCS": 567, ...}
        }
    """
    reader = csv.DictReader(csv_text.strip().split("\n"))
    
    indices: dict[str, int] = {}
    futures: dict[str, dict[str, Any]] = {}
    heavyweights: dict[str, int] = {}
    
    # Target symbols
    index_symbols = {"NIFTY", "BANKNIFTY", "SENSEX"}
    future_underlyings = {"NIFTY", "BANKNIFTY", "SENSEX"}
    heavyweight_symbols = {
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
        "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "HCLTECH",
    }
    
    current_expiry, next_expiry = _current_and_next_month_expiry()
    today = datetime.now(IST)
    in_rollover = _is_last_week_of_month(today)
    
    for row in reader:
        try:
            parsed = _parse_csv_row(row)
            if not parsed["security_id"]:
                continue
            
            symbol = parsed["symbol"]
            segment = parsed["segment"]
            instrument_type = parsed["instrument_type"]
            
            # Index futures (FUTIDX)
            if instrument_type == "FUTIDX" and segment == "NSE_FNO":
                underlying = parsed["trading_symbol"].replace("FUT", "").strip()
                if underlying in future_underlyings:
                    expiry = parsed["expiry"]
                    
                    # Record current month contract
                    if expiry == current_expiry:
                        key = f"{underlying}FUT"
                        futures[key] = {
                            "security_id": parsed["security_id"],
                            "expiry": expiry,
                            "underlying": underlying,
                        }
                    
                    # During rollover week, also record next month
                    if in_rollover and expiry == next_expiry:
                        key = f"{underlying}FUT_NEXT"
                        futures[key] = {
                            "security_id": parsed["security_id"],
                            "expiry": expiry,
                            "underlying": underlying,
                        }
            
            # Indices (IDX_I segment)
            elif segment == "IDX_I" and symbol in index_symbols:
                indices[symbol] = parsed["security_id"]
            
            # Heavyweights (NSE_EQ equity segment)
            elif segment == "NSE_EQ" and symbol in heavyweight_symbols:
                heavyweights[symbol] = parsed["security_id"]
                
        except Exception as e:
            log.debug("Skipping row: %s", e)
            continue
    
    return {
        "indices": indices,
        "futures": futures,
        "heavyweights": heavyweights,
        "fetched_at": datetime.now(IST).isoformat(),
        "current_expiry": current_expiry,
        "next_expiry": next_expiry,
        "in_rollover": in_rollover,
    }


def load_instruments(
    client: DhanClient, cache_dir: Path, *, force_refresh: bool = False
) -> dict[str, Any]:
    """Load instruments with daily cache.
    
    Cache file: {cache_dir}/instruments_YYYYMMDD.json
    Refreshes daily at 00:00 IST or when force_refresh=True.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    date_str = ist_date_str()
    cache_file = cache_dir / f"instruments_{date_str}.json"
    
    # Try cache first
    if not force_refresh and cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            log.info("Loaded instruments from cache: %s", cache_file.name)
            return cached
        except Exception as e:
            log.warning("Cache read failed: %s", e)
    
    # Fetch fresh data
    log.info("Fetching fresh instrument master from Dhan...")
    csv_text = client.instruments.fetch_scrip_master_text()
    
    if client.dry_run:
        log.info("Dry-run: using fixture instruments (no real scrip master)")
        return {
            "indices": {"NIFTY": 13, "BANKNIFTY": 25, "SENSEX": 51},
            "futures": {
                "NIFTYFUT": {"security_id": 99999, "expiry": "2026-09-24", "underlying": "NIFTY"},
                "BANKNIFTYFUT": {"security_id": 99998, "expiry": "2026-09-24", "underlying": "BANKNIFTY"},
            },
            "heavyweights": {
                "RELIANCE": 88881, "TCS": 88882, "HDFCBANK": 88883,
                "INFY": 88884, "ICICIBANK": 88885,
            },
            "fetched_at": datetime.now(IST).isoformat(),
            "current_expiry": "2026-09-24",
            "next_expiry": "2026-10-29",
            "in_rollover": False,
        }
    
    # Parse CSV
    instruments = parse_instruments(csv_text)
    
    # Save to cache
    try:
        cache_file.write_text(json.dumps(instruments, indent=2), encoding="utf-8")
        log.info("Cached instruments to: %s", cache_file.name)
    except Exception as e:
        log.warning("Cache write failed: %s", e)
    
    log.info(
        "Loaded %d indices, %d futures, %d heavyweights",
        len(instruments["indices"]),
        len(instruments["futures"]),
        len(instruments["heavyweights"]),
    )
    
    return instruments

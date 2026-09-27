"""Instrument resolution from Dhan master."""

from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from typing import Any

from dhan_client.rest import DhanRestClient
from dhan_client.types import FeedInstrument


def get_nearest_weekly_expiry(underlying: str, today: date) -> str:
    """Get nearest weekly expiry for underlying (placeholder - needs real implementation)."""
    # TODO: Parse from Dhan instrument master or calculate
    # For now, return a date ~1 week out
    from datetime import timedelta
    
    # Find next Thursday
    days_ahead = 3 - today.weekday()  # Thursday is 3
    if days_ahead <= 0:
        days_ahead += 7
    expiry = today + timedelta(days=days_ahead)
    return expiry.strftime("%Y-%m-%d")


def resolve_instruments(
    underlying: str, spot: float, client: DhanRestClient | None = None
) -> dict[str, tuple[FeedInstrument, str, str]]:
    """
    Resolve instruments for recording.
    
    Returns:
        Dict mapping security_id -> (FeedInstrument, instrument_id, rule)
        where instrument_id is in format NSE_FNO:NIFTY:2026-09-29:24500:CE
    """
    # TODO: Real implementation needs to:
    # 1. Fetch instrument master from Dhan
    # 2. Find nearest weekly expiry
    # 3. Calculate ATM from spot
    # 4. Look up security IDs for strikes
    
    # Placeholder for now - uses fake IDs
    exchange = "NSE" if underlying != "SENSEX" else "BSE"
    segment = f"{exchange}_FNO"
    expiry = get_nearest_weekly_expiry(underlying, date.today())
    
    atm = round(spot / 50) * 50
    strikes = {
        "ATM": atm,
        "ITM100_CE": atm + 100,
        "ITM200_CE": atm + 200,
        "ITM100_PE": atm - 100,
        "ITM200_PE": atm - 200,
    }
    
    instruments: dict[str, tuple[FeedInstrument, str, str]] = {}
    
    # Options (placeholder security IDs - real implementation needs Dhan master)
    for rule, strike in strikes.items():
        if "_CE" in rule:
            side = "CE"
            rule_name = rule.replace("_CE", "")
        elif "_PE" in rule:
            side = "PE"
            rule_name = rule.replace("_PE", "")
        else:
            side = "CE"
            rule_name = rule
            
        # Placeholder numeric ID (real implementation needs lookup)
        security_id = f"{strike}{1 if side == 'CE' else 2}"
        instrument_id = f"{segment}:{underlying}:{expiry}:{strike}:{side}"
        
        feed_inst = FeedInstrument(
            exchange_segment=segment,
            security_id=security_id
        )
        instruments[security_id] = (feed_inst, instrument_id, f"{rule_name}|{side}")
    
    # Index (placeholder)
    idx_segment = f"{exchange}_IDX"
    idx_security_id = "999920000" if underlying == "NIFTY" else "999920005"
    idx_instrument_id = f"{idx_segment}:{underlying}"
    instruments[idx_security_id] = (
        FeedInstrument(exchange_segment=idx_segment, security_id=idx_security_id),
        idx_instrument_id,
        "INDEX|INDEX"
    )
    
    # Future (placeholder)
    fut_security_id = f"{atm}9"
    fut_instrument_id = f"{segment}:{underlying}:{expiry}"
    instruments[fut_security_id] = (
        FeedInstrument(exchange_segment=segment, security_id=fut_security_id),
        fut_instrument_id,
        "FUTURE|FUTURE"
    )
    
    return instruments

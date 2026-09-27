"""Deterministic ID generation for orders, events, signals."""

import hashlib
from datetime import datetime, timezone


def order_id(account_id: str, signal_id: str, leg: str) -> str:
    """
    Generate deterministic 27-char order ID from account, signal, and leg.

    Format: "aad" + sha256(f"{account}|{signal}|{leg}").hexdigest()[:24]
    Matches legacy desk/paper.py and engine logs.

    Args:
        account_id: Account identifier (must not contain "|")
        signal_id: Signal identifier (must not contain "|")
        leg: Leg identifier (must not contain "|", e.g. "entry", "stop", "exit")

    Returns:
        27-character string starting with "aad"

    Raises:
        ValueError: if any input contains "|"
    """
    # Reject "|" in inputs to prevent collision attacks
    if "|" in account_id or "|" in signal_id or "|" in leg:
        raise ValueError("order_id inputs must not contain '|' separator")

    # Deterministic hash matching legacy format
    h = hashlib.sha256(f"{account_id}|{signal_id}|{leg}".encode()).hexdigest()
    return f"aad{h[:24]}"


def event_id(role: str, input_event_id: str, n: int) -> str:
    """
    Generate deterministic event ID.

    Format: sha256(f"{role}|{input_event_id}|{n}").hexdigest()[:32]

    Args:
        role: Service role (e.g. "engine", "boss", "desk")
        input_event_id: ID of the input event that triggered this
        n: Sequence number for this role/input

    Returns:
        32-character hex string

    Raises:
        ValueError: if any input contains "|"
    """
    # Reject "|" in inputs to prevent collision attacks
    if "|" in role or "|" in input_event_id:
        raise ValueError("event_id inputs must not contain '|' separator")

    h = hashlib.sha256(f"{role}|{input_event_id}|{n}".encode()).hexdigest()
    return h[:32]


def signal_id(
    strategy_id: str,
    version: str,
    underlying: str,
    decision_ts: str | datetime,
    n: int,
) -> str:
    """
    Generate deterministic signal ID.

    Format: sg_{strategy_slug}_{underlying}_{yyyymmdd}_{hhmm}_{n}
    Example: sg_r8e1_nifty_20260928_1001_0

    Args:
        strategy_id: Strategy identifier (e.g. "R8-E1-COIL-SIDE")
        version: Strategy version (e.g. "1.0.0")
        underlying: Underlying symbol (e.g. "NIFTY")
        decision_ts: Decision timestamp (ISO-8601 string or datetime, must be timezone-aware)
        n: Sequence number for this strategy/underlying/minute

    Returns:
        Signal ID string

    Raises:
        ValueError: if decision_ts is naive (no timezone)
    """
    # Parse decision_ts to datetime if string
    dt = datetime.fromisoformat(decision_ts) if isinstance(decision_ts, str) else decision_ts

    # Reject naive timestamps
    if dt.tzinfo is None:
        raise ValueError("signal_id decision_ts must be timezone-aware")

    # Normalize to IST (Asia/Kolkata, UTC+5:30)
    # Note: Python doesn't have zoneinfo in stdlib until 3.9, but we can use timedelta
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt.astimezone(ist)

    # Extract date and time
    date_str = dt_ist.strftime("%Y%m%d")
    time_str = dt_ist.strftime("%H%M")

    # Normalize strategy_id + version to slug: collision-free, includes version
    # Keep all alphanumerics (lowercase) to ensure distinct strategies get distinct slugs
    # "R8-E1" + "1.0.0" -> "r8e1v100"
    # "R8-E1-COIL-SIDE" + "1.0.0" -> "r8e1coilsidev100"
    combined = strategy_id + "v" + version
    strat_slug = "".join(c for c in combined.lower() if c.isalnum())

    if not strat_slug:
        raise ValueError(
            "signal_id strategy_id and version must contain at least one alphanumeric character"
        )

    # Normalize underlying to lowercase
    und = underlying.lower()

    return f"sg_{strat_slug}_{und}_{date_str}_{time_str}_{n}"

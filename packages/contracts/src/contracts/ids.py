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

    Format: sg_{strategy_slug}_{hash}_{underlying}_{yyyymmdd}_{hhmm}_{n}
    Example: sg_r8-e1-v1.0.0_bfe5cd_nifty_20260928_1001_0

    Args:
        strategy_id: Strategy identifier (e.g. "R8-E1-COIL-SIDE"); must not contain "|"
        version: Strategy version (e.g. "1.0.0"); must not contain "|"
        underlying: Underlying symbol (e.g. "NIFTY"); must not contain "|"
        decision_ts: Decision timestamp (ISO-8601 string or datetime, must be timezone-aware)
        n: Sequence number for this strategy/underlying/minute (int >= 0)

    Returns:
        Signal ID string

    Raises:
        ValueError: if any string input contains "|", decision_ts is naive,
            underlying is empty, or n is not a non-negative int
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError("signal_id n must be a non-negative int")

    if not isinstance(underlying, str) or not any(c.isalnum() for c in underlying):
        raise ValueError("signal_id underlying must contain at least one alphanumeric character")

    if isinstance(decision_ts, str) and "|" in decision_ts:
        raise ValueError("signal_id inputs must not contain '|' separator")

    # Reject "|" so the hash field separator cannot be forged
    # ("R8|", "1.0") vs ("R8", "|1.0") would otherwise collide.
    if "|" in strategy_id or "|" in version or "|" in underlying:
        raise ValueError("signal_id inputs must not contain '|' separator")

    # Parse decision_ts to datetime if string
    dt = datetime.fromisoformat(decision_ts) if isinstance(decision_ts, str) else decision_ts

    # Reject naive timestamps
    if dt.tzinfo is None:
        raise ValueError("signal_id decision_ts must be timezone-aware")

    # Normalize to IST (Asia/Kolkata, UTC+5:30)
    from datetime import timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt.astimezone(ist)

    # Extract date and time
    date_str = dt_ist.strftime("%Y%m%d")
    time_str = dt_ist.strftime("%H%M")

    # Normalize strategy_id + version to slug: keep [a-z0-9.-], join with "-v"
    # "R8-E1" + "1.10.0" -> "r8-e1-v1.10.0" (distinct from 11.0.0)
    strategy_slug = "".join(c.lower() if c.isalnum() or c in ".-" else "" for c in strategy_id)
    version_slug = "".join(c if c.isalnum() or c in ".-" else "" for c in version)
    strat_slug = f"{strategy_slug}-v{version_slug}"

    if not strategy_slug or not version_slug:
        raise ValueError(
            "signal_id strategy_id and version must contain at least one alphanumeric character"
        )

    # Hash every input so distinct accepted tuples cannot collide
    collision_check = hashlib.sha256(
        f"{strategy_id}|{version}|{underlying}|{dt_ist.isoformat()}|{n}".encode()
    ).hexdigest()[:6]

    und = underlying.lower()

    return f"sg_{strat_slug}_{collision_check}_{und}_{date_str}_{time_str}_{n}"

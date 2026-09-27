"""Deterministic ID generation for orders, events, signals."""

import hashlib
import secrets
from datetime import datetime


def event_id() -> str:
    """Generate a random event ID (32-char hex)."""
    return secrets.token_hex(16)


def order_id(account_id: str, signal_id: str, leg: str) -> str:
    """
    Generate deterministic 27-char order ID from account, signal, and leg.

    Format: [a-z0-9], stable across processes for the same inputs.
    Fits Dhan correlationId (max 30 chars).

    Args:
        account_id: Account identifier
        signal_id: Signal identifier
        leg: Leg identifier (e.g. "entry", "stop", "exit")

    Returns:
        27-character lowercase alphanumeric string
    """
    # Deterministic hash of inputs
    h = hashlib.sha256(f"{account_id}:{signal_id}:{leg}".encode()).digest()
    # Convert to base36-like (a-z0-9 only)
    # Take first 20 bytes, convert to int, then to base36
    num = int.from_bytes(h[:20], "big")
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = []
    for _ in range(27):
        result.append(chars[num % 36])
        num //= 36
    return "".join(result)


def signal_id(strategy_id: str, version: str, underlying: str, decision_ts: str, n: int) -> str:
    """
    Generate deterministic signal ID.

    Format: sg_{strategy_id}_{underlying}_{yyyymmdd}_{hhmm}_{n}
    Lowercase, underscores for readability.

    Args:
        strategy_id: Strategy identifier (e.g. "R8-E1-COIL-SIDE")
        version: Strategy version
        underlying: Underlying symbol (e.g. "NIFTY")
        decision_ts: Decision timestamp (ISO-8601)
        n: Sequence number for this strategy/underlying/minute

    Returns:
        Signal ID string
    """
    # Parse decision_ts to extract date and time
    dt = datetime.fromisoformat(decision_ts)
    date_str = dt.strftime("%Y%m%d")
    time_str = dt.strftime("%H%M")

    # Normalize strategy_id and underlying to lowercase with hyphens
    strat = strategy_id.lower().replace("_", "-")
    und = underlying.lower()

    return f"sg_{strat}_{und}_{date_str}_{time_str}_{n}"

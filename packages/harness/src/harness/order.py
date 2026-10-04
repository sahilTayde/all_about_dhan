"""Off-market LIMIT-only intent. MARKET and marketable prices are refused."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

DEFAULT_OFF_MARKET_LIMIT = 1.0
MAX_OFF_MARKET_LIMIT = 1.05
ALLOWED_SIDES = frozenset({"BUY"})
ALLOWED_ORDER_TYPES = frozenset({"LIMIT"})
FORBIDDEN_ORDER_TYPES = frozenset(
    {"MARKET", "SL", "SL-M", "STOP_LOSS", "STOP_LOSS_MARKET", "SUPER"}
)
_CORRELATION = re.compile(r"^[A-Za-z0-9 _-]{1,30}$")


class HarnessOrderError(Exception):
    """Submit/cancel path failed after gates. ``exit_code`` is 3."""

    exit_code = 3


@dataclass(frozen=True)
class OffMarketIntent:
    symbol: str
    security_id: str
    side: str = "BUY"
    order_type: str = "LIMIT"
    limit_price: float = DEFAULT_OFF_MARKET_LIMIT
    lots: int = 1
    lot_size: int = 1
    exchange: str = "NSE_FNO"
    product_type: str = "INTRADAY"
    client_order_id: str = ""

    @property
    def qty(self) -> int:
        return int(self.lots) * int(self.lot_size)


def new_client_order_id() -> str:
    return f"aadsh{secrets.token_hex(4)}"


def default_intent(*, security_id: str = "TEST", symbol: str = "NIFTY CE") -> OffMarketIntent:
    return OffMarketIntent(
        symbol=symbol,
        security_id=security_id,
        client_order_id=new_client_order_id(),
    )


def validate_off_market(intent: OffMarketIntent) -> OffMarketIntent:
    """Refuse anything that could fill. Far-off BUY LIMIT only."""
    problems: list[str] = []
    side = (intent.side or "").strip().upper()
    kind = (intent.order_type or "").strip().upper()
    if side not in ALLOWED_SIDES:
        problems.append(f"side {side!r} is not BUY")
    if kind in FORBIDDEN_ORDER_TYPES or kind not in ALLOWED_ORDER_TYPES:
        problems.append(f"order_type {kind!r} is not LIMIT (MARKET/SL refused)")
    try:
        price = float(intent.limit_price)
    except (TypeError, ValueError):
        price = 0.0
        problems.append("limit_price is not a number")
    if price <= 0:
        problems.append("limit_price must be > 0")
    if price > MAX_OFF_MARKET_LIMIT:
        problems.append(f"limit_price {price} is above the off-market cap {MAX_OFF_MARKET_LIMIT}")
    if intent.lots <= 0 or intent.lot_size <= 0 or intent.qty <= 0:
        problems.append("lots/lot_size must be positive")
    if not (intent.security_id or "").strip():
        problems.append("security_id is required")
    cid = (intent.client_order_id or "").strip() or new_client_order_id()
    if not _CORRELATION.match(cid):
        problems.append("client_order_id must be 1-30 chars of [A-Za-z0-9 _-]")
    if problems:
        raise HarnessOrderError("; ".join(problems))
    return OffMarketIntent(
        symbol=intent.symbol or "NIFTY CE",
        security_id=intent.security_id.strip(),
        side=side,
        order_type=kind,
        limit_price=price,
        lots=int(intent.lots),
        lot_size=int(intent.lot_size),
        exchange=intent.exchange or "NSE_FNO",
        product_type=intent.product_type or "INTRADAY",
        client_order_id=cid,
    )

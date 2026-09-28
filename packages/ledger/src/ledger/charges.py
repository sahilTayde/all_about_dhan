"""Per-order charges for Indian index options. Rates live in config/charges.yaml."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Self, overload

import yaml

# This repo's config/charges.yaml (editable install), not the process CWD; CWD only as a fallback.
_REPO_CHARGES = Path(__file__).resolve().parents[4] / "config" / "charges.yaml"
DEFAULT_CHARGES_PATH = _REPO_CHARGES if _REPO_CHARGES.is_file() else Path("config/charges.yaml")
RATE_KEYS = (
    "brokerage_per_order_inr",
    "stt_sell_premium_frac",
    "exchange_txn_frac",
    "sebi_fee_frac",
    "stamp_duty_buy_frac",
    "gst_frac",
)
BY_EXCHANGE = "exchange_txn_frac_by_exchange"
UNDERLYING_EXCHANGE = "underlying_exchange"
_PAISE = Decimal("0.01")


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("bool is not a money value")
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    raise TypeError(f"cannot coerce {type(value)!r} to Decimal")


class Paisa(Decimal):
    """Paise Decimal that still mixes with float callers (desk-ml.costs)."""

    def __new__(cls, value: Any) -> Self:
        return Decimal.__new__(cls, _as_decimal(value))

    def _other(self, other: Any) -> Decimal | None:
        try:
            return _as_decimal(other)
        except TypeError:
            return None

    def __eq__(self, other: object) -> bool:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Decimal.__eq__(Decimal(self), coerced)

    def __ne__(self, other: object) -> bool:
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    def __lt__(self, other: Any) -> bool:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Decimal.__lt__(Decimal(self), coerced)

    def __le__(self, other: Any) -> bool:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Decimal.__le__(Decimal(self), coerced)

    def __gt__(self, other: Any) -> bool:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Decimal.__gt__(Decimal(self), coerced)

    def __ge__(self, other: Any) -> bool:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Decimal.__ge__(Decimal(self), coerced)

    def __add__(self, other: Any) -> Paisa:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Paisa(Decimal(self) + coerced)

    def __radd__(self, other: Any) -> Paisa:
        return self.__add__(other)

    def __sub__(self, other: Any) -> Paisa:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Paisa(Decimal(self) - coerced)

    def __rsub__(self, other: Any) -> Paisa:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Paisa(coerced - Decimal(self))

    def __mul__(self, other: Any) -> Paisa:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Paisa(Decimal(self) * coerced)

    def __rmul__(self, other: Any) -> Paisa:
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> Paisa:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Paisa(Decimal(self) / coerced)

    def __rtruediv__(self, other: Any) -> Paisa:
        coerced = self._other(other)
        if coerced is None:
            return NotImplemented
        return Paisa(coerced / Decimal(self))

    def __abs__(self) -> Paisa:
        return Paisa(abs(Decimal(self)))

    def __neg__(self) -> Paisa:
        return Paisa(-Decimal(self))

    @overload
    def __round__(self, ndigits: None = None) -> int: ...

    @overload
    def __round__(self, ndigits: int) -> Paisa: ...

    def __round__(self, ndigits: int | None = None) -> int | Paisa:
        if ndigits is None:
            return int(Decimal(self).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        step = Decimal(1).scaleb(-int(ndigits))
        return Paisa(Decimal(self).quantize(step, rounding=ROUND_HALF_UP))


def load_rates(path: Path = DEFAULT_CHARGES_PATH, *, by_exchange: bool = False) -> dict[str, Any]:
    """Flat rates by default. `by_exchange=True` also loads the per-exchange transaction charge
    and the underlying -> exchange map (SENSEX at the BSE rate); legacy callers never ask for it."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    missing = [k for k in RATE_KEYS if k not in data]
    if missing:
        raise ValueError(f"{path}: missing charge rates {missing}")
    rates: dict[str, Any] = {k: float(data[k]) for k in RATE_KEYS}
    if by_exchange:
        by_ex, und_ex = data.get(BY_EXCHANGE), data.get(UNDERLYING_EXCHANGE)
        if not isinstance(by_ex, dict) or not isinstance(und_ex, dict):
            raise ValueError(f"{path}: by_exchange needs {BY_EXCHANGE} and {UNDERLYING_EXCHANGE}")
        rates[BY_EXCHANGE] = {str(k).upper(): float(v) for k, v in by_ex.items()}
        rates[UNDERLYING_EXCHANGE] = {str(k).upper(): str(v).upper() for k, v in und_ex.items()}
    return rates


def exchange_for(symbol_or_underlying: str, rates: dict[str, Any]) -> str | None:
    """'SENSEX 82000 CE' or 'SENSEX' -> 'BSE'. None when the rates are flat (legacy)."""
    table = rates.get(UNDERLYING_EXCHANGE)
    if not table:
        return None
    m = re.match(r"[A-Z]+", str(symbol_or_underlying or "").strip().upper())
    und = m.group(0) if m else ""
    if und not in table:
        raise ValueError(f"no exchange for underlying {und!r} in {UNDERLYING_EXCHANGE}")
    return table[und]


def _d(x: Any) -> Decimal:
    return _as_decimal(x)


def _inr(x: Decimal) -> Decimal:
    return x.quantize(_PAISE, rounding=ROUND_HALF_UP)


def order_charges(
    side: str,
    qty: int,
    price: Decimal | float | str,
    rates: dict[str, Any],
    *,
    include_brokerage: bool = True,
    exchange: str | None = None,
) -> dict[str, Decimal]:
    """Charges for one executed order (or one fill of it).

    Each component is rounded to paise like a contract note line; GST is on the rounded
    brokerage + exchange + SEBI. Pass include_brokerage=False for the 2nd+ fill of one order.
    `exchange` (NSE/BSE) picks the per-exchange transaction charge from `load_rates(by_exchange=True)`.
    Price may be Decimal; every returned line is Decimal (Paisa) quantized to paise except
    turnover, which stays exact.
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    if exchange is None:
        txn_frac = rates["exchange_txn_frac"]
    else:
        txn_frac = rates[BY_EXCHANGE][exchange.upper()]
    turnover = _d(qty) * _d(price)
    brokerage = _inr(_d(rates["brokerage_per_order_inr"])) if include_brokerage else Decimal("0.00")
    exchange_fee = _inr(turnover * _d(txn_frac))
    sebi = _inr(turnover * _d(rates["sebi_fee_frac"]))
    stt = _inr(turnover * _d(rates["stt_sell_premium_frac"])) if side == "SELL" else Decimal("0.00")
    stamp = _inr(turnover * _d(rates["stamp_duty_buy_frac"])) if side == "BUY" else Decimal("0.00")
    gst = _inr((brokerage + exchange_fee + sebi) * _d(rates["gst_frac"]))
    total = brokerage + exchange_fee + sebi + stt + stamp + gst
    return {
        "turnover": Paisa(turnover),
        "brokerage": Paisa(brokerage),
        "stt": Paisa(stt),
        "exchange": Paisa(exchange_fee),
        "sebi": Paisa(sebi),
        "stamp": Paisa(stamp),
        "gst": Paisa(gst),
        "total": Paisa(total),
    }

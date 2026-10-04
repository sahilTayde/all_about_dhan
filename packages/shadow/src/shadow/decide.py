"""Evaluate the paper/shadow basket on a closed bar. Log-only. No orders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketdata.types import BarClosed
from strategies.api import Bar, Signal
from strategies.runtime import SessionRuntime

from shadow.basket import (
    REASON_CONFLICT,
    REASON_NO_CLOSED_BAR,
    REASON_PLUGIN_ABSTAIN,
    LoadedBasket,
)


class MapFeatureView:
    """Read-only feature map. Dry-run injects EMAs; follow uses empty (fail closed)."""

    def __init__(self, values: dict[str, object] | None = None) -> None:
        self._values = dict(values or {})

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None:
        del instrument, tf
        return self._values.get(name)


class DryRunCrossFeatures:
    """Two-bar EMA cross for TEST-CROSS. Dry-run only. Not a live feature engine."""

    def __init__(self) -> None:
        self._n = 0

    def next_view(self) -> MapFeatureView:
        self._n += 1
        if self._n == 1:
            return MapFeatureView({"ema_5": 10.0, "ema_20": 11.0})
        return MapFeatureView({"ema_5": 12.0, "ema_20": 11.0})


@dataclass(frozen=True)
class BasketDecision:
    action: str
    reason: str
    side: str = ""
    strategy_id: str = ""
    instrument_id: str = ""
    underlying: str = ""
    ltp: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def bar_from_closed(closed: BarClosed) -> Bar | None:
    if closed.o is None or closed.c is None:
        return None
    return Bar(
        instrument_id=closed.instrument_id,
        open=float(closed.o),
        high=float(closed.h if closed.h is not None else closed.o),
        low=float(closed.l if closed.l is not None else closed.o),
        close=float(closed.c),
        volume=int(closed.v or 0),
        timestamp=closed.end,
        available_ts=closed.available_ts or closed.end,
        gap=closed.gap,
    )


def _underlying(instrument_id: str) -> str:
    raw = instrument_id.upper()
    for name in ("NIFTY", "BANKNIFTY", "SENSEX"):
        if name in raw:
            return name
    return raw.split(":")[0] if raw else "UNKNOWN"


def session_abstain(session: LoadedBasket, *, instrument_id: str = "NIFTY", ltp: float | None = None) -> BasketDecision:
    reason = session.refuse_reason() or REASON_PLUGIN_ABSTAIN
    return BasketDecision(
        action="HOLD",
        reason=reason,
        instrument_id=instrument_id,
        underlying=_underlying(instrument_id),
        ltp=ltp,
        extra={
            "basket_hash": session.basket.basket_hash,
            "basket_source": session.basket.source,
            "defaults_from": session.defaults_from,
            "detail": session.refuse_detail(),
            "enabled": list(session.enabled_ids),
        },
    )


def no_closed_bar(session: LoadedBasket, *, instrument_id: str = "NIFTY") -> BasketDecision:
    row = session_abstain(session, instrument_id=instrument_id)
    extra = dict(row.extra)
    return BasketDecision(
        action="HOLD",
        reason=REASON_NO_CLOSED_BAR,
        instrument_id=instrument_id,
        underlying=row.underlying,
        extra=extra,
    )


def decide_bar(
    session: LoadedBasket,
    bar: Bar,
    view: MapFeatureView,
    *,
    ltp: float | None = None,
) -> BasketDecision:
    extra = {
        "basket_hash": session.basket.basket_hash,
        "basket_source": session.basket.source,
        "defaults_from": session.defaults_from,
        "enabled": list(session.enabled_ids),
    }
    refuse = session.refuse_reason()
    if refuse is not None:
        extra["detail"] = session.refuse_detail()
        return BasketDecision(
            action="HOLD",
            reason=refuse,
            instrument_id=bar.instrument_id,
            underlying=_underlying(bar.instrument_id),
            ltp=ltp if ltp is not None else bar.close,
            extra=extra,
        )
    runtime = SessionRuntime(session.loaded)
    signals: list[Signal] = runtime.on_bar(bar, view)
    if not signals:
        extra["detail"] = session.refuse_detail()
        return BasketDecision(
            action="HOLD",
            reason=REASON_PLUGIN_ABSTAIN,
            instrument_id=bar.instrument_id,
            underlying=_underlying(bar.instrument_id),
            ltp=ltp if ltp is not None else bar.close,
            extra=extra,
        )
    sides = {sig.side for sig in signals}
    if len(sides) > 1:
        extra["contributors"] = [sig.strategy_id for sig in signals]
        return BasketDecision(
            action="HOLD",
            reason=REASON_CONFLICT,
            instrument_id=bar.instrument_id,
            underlying=_underlying(bar.instrument_id),
            ltp=ltp if ltp is not None else bar.close,
            extra=extra,
        )
    sig = signals[0]
    extra["strategy_id"] = sig.strategy_id
    extra["signal_id"] = sig.signal_id
    extra["signal_reasons"] = list(sig.reasons)
    extra["stage"] = "shadow"
    return BasketDecision(
        action="ENTER",
        reason=str(sig.reasons[0]) if sig.reasons else "SIGNAL",
        side=sig.side,
        strategy_id=sig.strategy_id,
        instrument_id=bar.instrument_id,
        underlying=sig.underlying or _underlying(bar.instrument_id),
        ltp=ltp if ltp is not None else bar.close,
        extra=extra,
    )

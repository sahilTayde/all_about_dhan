"""Dhan packet -> Tick / DepthQuote; security id -> InstrumentId."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from marketdata.depth import quote_from_full, quote_from_ltp
from marketdata.frames import Packet
from marketdata.instruments import Instrument
from marketdata.types import BarClosed, Tick


class SecurityMap:
    """(exchange_segment, security_id) -> Instrument from the session universe."""

    def __init__(self, instruments: Iterable[Instrument]) -> None:
        self._by: dict[tuple[str, str], Instrument] = {
            (inst.exchange_segment, str(inst.security_id)): inst for inst in instruments
        }

    def resolve(self, segment: str | None, security_id: int | str) -> Instrument | None:
        if not segment:
            return None
        return self._by.get((segment, str(security_id)))


def _opt_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def tick_from_fields(instrument_id: str, fields: dict[str, Any], exchange_ts: str) -> Tick | None:
    """LTP print. Missing or non-finite LTP is not a tick."""
    raw = fields.get("ltp")
    if raw is None:
        return None
    ltp = float(raw)
    if ltp != ltp or ltp in (float("inf"), float("-inf")):
        return None
    return Tick(
        instrument_id=instrument_id,
        ltp=ltp,
        ltq=_opt_int(fields.get("last_quantity") if fields.get("last_quantity") is not None else fields.get("ltq")),
        volume=_opt_int(fields.get("volume")),
        oi=_opt_int(fields.get("oi")),
        exchange_ts=exchange_ts,
    )


def tick_from_packet(packet: Packet, instrument_id: str, exchange_ts: str) -> Tick | None:
    return tick_from_fields(instrument_id, packet.decoded.fields, exchange_ts)


def tick_payload(tick: Tick) -> dict[str, Any]:
    return {
        "instrument_id": tick.instrument_id,
        "ltp": tick.ltp,
        "ltq": tick.ltq,
        "volume": tick.volume,
        "oi": tick.oi,
        "exchange_ts": tick.exchange_ts,
    }


def bar_payload(bar: BarClosed) -> dict[str, Any]:
    return {
        "instrument_id": bar.instrument_id,
        "tf": bar.tf,
        "start": bar.start,
        "end": bar.end,
        "o": bar.o,
        "h": bar.h,
        "l": bar.l,
        "c": bar.c,
        "v": bar.v,
        "n_ticks": bar.n_ticks,
        "gap": bar.gap,
        "late_ticks": bar.late_ticks,
    }


def depth_from_packet(packet: Packet, instrument_id: str, exchange_ts: str) -> dict[str, Any] | None:
    kind, fields = packet.decoded.kind, packet.decoded.fields
    if kind == "full":
        quote = quote_from_full(fields)
    elif kind in ("ticker", "index", "quote") and fields.get("ltp") is not None:
        quote = quote_from_ltp(float(fields["ltp"]))
    else:
        return None
    return {"instrument_id": instrument_id, **quote, "exchange_ts": exchange_ts, "repeat": False}

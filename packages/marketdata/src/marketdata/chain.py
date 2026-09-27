"""Option-chain poller. One unique request / 3 s (Dhan documented rate)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dhan_client.endpoints import RATE_LIMIT_OPTION_CHAIN_SECONDS

FetchChain = Callable[[int, str, str], dict[str, Any]]


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _leg(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"ltp": None, "bid": None, "ask": None, "oi": None, "oi_chg": None, "iv": None, "volume": None}
    return {
        "ltp": _num(raw.get("last_price", raw.get("ltp"))),
        "bid": _num(raw.get("bid", raw.get("best_bid"))),
        "ask": _num(raw.get("ask", raw.get("best_ask"))),
        "oi": _int(raw.get("oi")),
        "oi_chg": _int(raw.get("oi_chg", raw.get("previous_oi"))),
        "iv": _num(raw.get("iv")),
        "volume": _int(raw.get("volume")),
    }


def snapshot_from_chain(chain: dict[str, Any], underlying: str, expiry: str) -> dict[str, Any]:
    """Map a Dhan `/optionchain` body (or a fixture) to CHAIN_SNAPSHOT."""
    oc_raw = chain.get("oc")
    oc: dict[Any, Any] = oc_raw if isinstance(oc_raw, dict) else {}
    strikes: list[dict[str, Any]] = []
    for key, cell in oc.items():
        try:
            strike = int(float(key))
        except (TypeError, ValueError):
            continue
        if not isinstance(cell, dict):
            continue
        strikes.append(
            {
                "strike": strike,
                "ce": _leg(cell.get("ce") or cell.get("CE")),
                "pe": _leg(cell.get("pe") or cell.get("PE")),
            }
        )
    strikes.sort(key=lambda row: int(row["strike"]))
    return {
        "underlying": underlying,
        "expiry": expiry,
        "spot": _num(chain.get("last_price", chain.get("spot"))),
        "strikes": strikes,
    }


class ChainPoller:
    """Call ``fetch`` at most once per ``interval_s`` (default 3 s)."""

    def __init__(self, fetch: FetchChain, *, interval_s: float = RATE_LIMIT_OPTION_CHAIN_SECONDS) -> None:
        self._fetch = fetch
        self.interval_s = interval_s
        self._last_s = float("-inf")
        self.calls = 0

    def due(self, now_s: float) -> bool:
        return now_s - self._last_s >= self.interval_s

    def poll(
        self,
        underlying_scrip: int,
        underlying_seg: str,
        expiry: str,
        underlying: str,
        now_s: float,
    ) -> dict[str, Any] | None:
        if not self.due(now_s):
            return None
        self._last_s = now_s
        self.calls += 1
        return snapshot_from_chain(self._fetch(underlying_scrip, underlying_seg, expiry), underlying, expiry)

"""Python adapters for TV-EP grid. Public textbook rules only — no Pine paste."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Callable, Optional

from backtest_engine.indicators import Bar, macd_hist, sma
from backtest_engine.tv_ep.catalog import CatalogEntry, ParamSpec

LeanFn = Callable[[list[Bar], dict[str, float]], list[str]]


@dataclass(frozen=True)
class Adapter:
    id: str
    ported: bool
    default_schema: dict[str, ParamSpec]
    leans: Optional[LeanFn]

    def schema_for(self, entry: CatalogEntry) -> dict[str, ParamSpec]:
        return entry.input_schema or self.default_schema

    def param_grid(self, entry: CatalogEntry) -> list[dict[str, float]]:
        schema = self.schema_for(entry)
        if not schema:
            return [{}]
        keys = list(schema.keys())
        combos = product(*(schema[k].values() for k in keys))
        out: list[dict[str, float]] = []
        for combo in combos:
            params = dict(zip(keys, combo))
            if self.id == "sma_cross" and params.get("fast", 0) >= params.get("slow", 0):
                continue
            if self.id == "macd_hist" and params.get("fast", 0) >= params.get("slow", 0):
                continue
            out.append(params)
        return out or [{}]


def _sma_leans(bars: list[Bar], params: dict[str, float]) -> list[str]:
    closes = [b.close for b in bars]
    fast = sma(closes, int(params.get("fast", 10)))
    slow = sma(closes, int(params.get("slow", 50)))
    leans = ["HOLD"] * len(bars)
    for i in range(1, len(bars)):
        if None in (fast[i], slow[i], fast[i - 1], slow[i - 1]):
            continue
        if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i]:
            leans[i] = "CE"
        elif fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            leans[i] = "PE"
    return leans


def _macd_leans(bars: list[Bar], params: dict[str, float]) -> list[str]:
    hist = macd_hist(
        [b.close for b in bars],
        fast=int(params.get("fast", 12)),
        slow=int(params.get("slow", 26)),
        signal=int(params.get("signal", 9)),
    )
    leans = ["HOLD"] * len(bars)
    for i in range(1, len(bars)):
        if hist[i] is None or hist[i - 1] is None:
            continue
        if hist[i - 1] <= 0 and hist[i] > 0:
            leans[i] = "CE"
        elif hist[i - 1] >= 0 and hist[i] < 0:
            leans[i] = "PE"
    return leans


ADAPTERS: dict[str, Adapter] = {
    "sma_cross": Adapter(
        id="sma_cross",
        ported=True,
        default_schema={
            "fast": ParamSpec("int", 10, (8, 10, 21)),
            "slow": ParamSpec("int", 50, (21, 50)),
        },
        leans=_sma_leans,
    ),
    "macd_hist": Adapter(
        id="macd_hist",
        ported=True,
        default_schema={
            "fast": ParamSpec("int", 12, (8, 12)),
            "slow": ParamSpec("int", 26, (26,)),
            "signal": ParamSpec("int", 9, (9,)),
        },
        leans=_macd_leans,
    ),
    "stub": Adapter(
        id="stub",
        ported=False,
        default_schema={},
        leans=None,
    ),
}


def get_adapter(adapter_id: str) -> Adapter:
    if adapter_id not in ADAPTERS:
        return ADAPTERS["stub"]
    return ADAPTERS[adapter_id]


def registry_meta() -> list[dict[str, Any]]:
    return [
        {
            "adapter": a.id,
            "ported": a.ported,
            "promotion": "NO_PROMOTE",
        }
        for a in ADAPTERS.values()
    ]

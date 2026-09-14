"""Python adapters for TV-EP grid. Public textbook rules only — no Pine paste."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Callable, Optional

from backtest_engine.indicators import Bar, macd_hist, sma
from backtest_engine.tv_ep.catalog import CatalogEntry, ParamSpec
from backtest_engine.tv_ep.ports import PORT_FNS

# Catalog ids that must light up when the sibling port lands under a shorter name.
ADAPTER_ALIASES = {
    "pmax_flip": "pmax",
}

LeanFn = Callable[[list[Bar], dict[str, float]], list[str]]


@dataclass(frozen=True)
class Adapter:
    id: str
    ported: bool
    default_schema: dict[str, ParamSpec]
    leans: Optional[LeanFn]
    partial: bool = False
    gap: str = ""

    def schema_for(self, entry: CatalogEntry) -> dict[str, ParamSpec]:
        """Catalog may carry 200 TTS inputs — grid only keys this adapter knows."""
        incoming = entry.input_schema or {}
        if not self.default_schema:
            return incoming
        if not incoming:
            return self.default_schema
        out: dict[str, ParamSpec] = {}
        for k, spec in self.default_schema.items():
            chosen = incoming.get(k, spec)
            grid = tuple(chosen.grid[:3]) if chosen.grid else (chosen.default,)
            out[k] = ParamSpec(chosen.type, chosen.default, grid)
        return out

    def param_grid(self, entry: CatalogEntry) -> list[dict[str, float]]:
        schema = self.schema_for(entry)
        if not schema:
            return [{}]
        keys = list(schema.keys())
        combos = product(*(schema[k].values() for k in keys))
        out: list[dict[str, float]] = []
        for combo in combos:
            params = dict(zip(keys, combo))
            fast = params.get("fast") or params.get("Fast_len") or params.get("Short_Term_MA_Length")
            slow = params.get("slow") or params.get("Slow_len") or params.get("Long_Term_MA_Length")
            if fast is not None and slow is not None and fast >= slow:
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


def _spec(default: float, *grid: float, typ: str = "int") -> ParamSpec:
    g = grid or (default,)
    return ParamSpec(typ, default, tuple(g))


ADAPTERS: dict[str, Adapter] = {
    "sma_cross": Adapter(
        id="sma_cross",
        ported=True,
        default_schema={"fast": _spec(10, 8, 10, 21), "slow": _spec(50, 50)},
        leans=_sma_leans,
    ),
    "macd_hist": Adapter(
        id="macd_hist",
        ported=True,
        default_schema={
            "fast": _spec(12, 12),
            "slow": _spec(26, 26),
            "signal": _spec(9, 9),
        },
        leans=_macd_leans,
    ),
    "stub": Adapter(
        id="stub",
        ported=False,
        default_schema={},
        leans=None,
        gap="unported placeholder — do not assign listing 001–023 here",
    ),
}


def _add(
    adapter_id: str,
    schema: dict[str, ParamSpec],
    *,
    partial: bool = False,
    gap: str = "",
) -> None:
    ADAPTERS[adapter_id] = Adapter(
        id=adapter_id,
        ported=True,
        default_schema=schema,
        leans=PORT_FNS[adapter_id],
        partial=partial,
        gap=gap,
    )


_add("ag_sell", {
    "MA_length": _spec(40, 30, 40),
    "ATR_length": _spec(20, 20),
    "ATR_factor": _spec(2.5, 2.0, 2.5, typ="float"),
    "Month_of_harvest": _spec(11, 11),
    "Delay_in_months_after_harvest": _spec(2, 2),
    "Days_between_trades": _spec(30, 30),
}, partial=True, gap="commodity harvest calendar; pyramiding=3 cash commission 300/contract")
_add("one_pct_week", {
    "dip_pct": _spec(1.0, 1.0, typ="float"),
    "target_pct": _spec(1.0, 1.0, typ="float"),
}, partial=True, gap="TQQQ weekly session; 0.5% BE exit not in lean simulator")
_add("csv_replay", {"csv_long": _spec(0, 0)}, partial=True, gap="needs Transactions CSV; no OHLC alpha")
_add("trendmaster_ma", {
    "Short_Term_MA_Length": _spec(9, 8, 9, 13),
    "Long_Term_MA_Length": _spec(21, 21, 34),
    "ma_type_code": _spec(0, 0),
}, partial=True, gap="FX Asia/London/NY session boxes + S/R/RSI/MACD soup not ported")
_add("double_tap", {
    "Pivot_Length": _spec(50, 20, 50),
    "Pivot_Tolerance": _spec(15.0, 15.0, typ="float"),
    "Detect_Bottoms": _spec(1, 1),
    "Detect_Tops": _spec(1, 1),
}, partial=True, gap="Fib target/stop + 3Commas alerts omitted")
_add("ema_trail", {"Fast_len": _spec(20, 20), "Slow_len": _spec(50, 50)}, partial=True, gap="percent trailing SL/target is TV close engine")
_add("tts_ma_cross", {"fast": _spec(21, 21), "slow": _spec(49, 49)}, partial=True, gap="222-input trailing template; internal SMA 21/49 only; 0.1% commission")
_add("bot3c_ma", {
    "MA_Length_1": _spec(21, 21),
    "MA_Length_2": _spec(50, 50),
}, partial=True, gap="3Commas webhook/JSON; 0.05% commission; ATR trail omitted")
_add("pivot_rev", {"leftBars": _spec(2, 2), "rightBars": _spec(1, 1)}, partial=True, gap="monthly returns table is viz; 0.1% commission")
_add("stoch_kd", {"K": _spec(13, 13), "D": _spec(3, 3), "Smooth": _spec(4, 4)}, partial=True, gap="pyramiding=100 / 30x margin TV-only")
_add("risk_size_demo", {"long_every": _spec(333, 333), "short_every": _spec(444, 444)}, partial=True, gap="random bar_index demo; risk qty not a lean")
_add("osc_ma", {
    "MA_Crossover_Strat_Short_Length": _spec(3, 3),
    "MA_Crossover_Strat_Long_Length": _spec(9, 9),
}, partial=True, gap="oscillator compare / Laguerre MA → EMA proxy")
_add("keltner_stop", {
    "length": _spec(20, 20),
    "Multiplier": _spec(1.0, 1.0, typ="float"),
    "ATR_Length": _spec(10, 10),
}, partial=True, gap="Kelly fraction omitted; 0.1% commission")
_add("ext_signal_sma", {"fast": _spec(14, 14), "slow": _spec(28, 28)}, partial=True, gap="template needs external ±1 source")
_add("sma_sltp_money", {"fast": _spec(14, 14), "slow": _spec(28, 28)}, partial=True, gap="$$ SL/TP needs mintick/pointvalue")
_add("sma_step_trail", {"fast": _spec(14, 14), "slow": _spec(28, 28)}, partial=True, gap="long-only; stepped trail stages omitted")
_add("pmax", {
    "ATR_Length": _spec(10, 10, 14),
    "ATR_Multiplier": _spec(3.0, 2.5, 3.0, typ="float"),
    "Moving_Average_Length": _spec(10, 10),
}, partial=True, gap="20-ticker screener + VAR/ZLEMA MA types omitted")
ADAPTERS["pmax_flip"] = ADAPTERS["pmax"]
_add("grid_like", {"point": _spec(2.0, 2.0, typ="float")}, partial=True, gap="martingale qty ignored; author says don't trade")
_add("gap_fill", {"invert": _spec(0, 0)}, partial=False, gap="")
_add("macd_martingale", {
    "fast": _spec(12, 12),
    "slow": _spec(26, 26),
    "Take_Profit_Percent": _spec(5.0, 5.0, typ="float"),
}, partial=True, gap="crypto martingale pyramid; long-only; 0% TV commission")
_add("lube_friction", {
    "bars_back": _spec(500, 50, 500),
    "friction_stop": _spec(50, 50),
    "friction_start": _spec(-10, -10),
    "lowest_friction_bars": _spec(100, 100),
}, partial=True, gap="BTC 30m origin; leverage input ignored")
_add("timed_sma", {
    "FastMA_Length": _spec(14, 14),
    "SlowMA_Length": _spec(28, 28),
}, partial=True, gap="session 0000-0000 = always; long-only; 0.27% commission")
_add("grover_llorens", {"length": _spec(480, 20, 480), "mult": _spec(14.0, 14.0, typ="float")}, partial=True, gap="length=480 needs long tape")


def get_adapter(adapter_id: str) -> Adapter:
    key = ADAPTER_ALIASES.get(adapter_id, adapter_id)
    if key not in ADAPTERS:
        return ADAPTERS["stub"]
    return ADAPTERS[key]


def registry_meta() -> list[dict[str, Any]]:
    return [
        {
            "adapter": a.id,
            "ported": a.ported,
            "partial": a.partial,
            "gap": a.gap or None,
            "promotion": "NO_PROMOTE",
        }
        for a in ADAPTERS.values()
    ]

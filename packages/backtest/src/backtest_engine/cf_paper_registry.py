"""Plugin registry for Chart Fanatics PAPER CE/PE detectors.

Simple path: bars → registered detector → CE/PE + premium levels.
Keep structure thin — each family plugs in; Okala is first citizen.
PAPER only. NO_PROMOTE. News veto soft-default OFF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

from backtest_engine.indicators import Bar

DetectFn = Callable[..., Optional[dict[str, Any]]]


@dataclass
class CfSignalPlugin:
    """One family detector on the simple signal path."""

    plugin_id: str
    family: str
    priority: int  # lower = earlier
    detect: DetectFn
    mix_ids: tuple[str, ...] = ()
    enabled: bool = True
    note: str = ""


_PLUGINS: list[CfSignalPlugin] = []
_BOOTSTRAPPED = False


def register_plugin(plugin: CfSignalPlugin) -> None:
    global _PLUGINS
    _PLUGINS = [p for p in _PLUGINS if p.plugin_id != plugin.plugin_id]
    _PLUGINS.append(plugin)
    _PLUGINS.sort(key=lambda p: (p.priority, p.plugin_id))


def clear_plugins() -> None:
    global _PLUGINS, _BOOTSTRAPPED
    _PLUGINS = []
    _BOOTSTRAPPED = False


def list_plugins() -> list[CfSignalPlugin]:
    _ensure_defaults()
    return list(_PLUGINS)


def _ensure_defaults() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True

    from backtest_engine.okala_in_paper import detect_okala_signal

    register_plugin(
        CfSignalPlugin(
            plugin_id="okala_in",
            family="okala",
            priority=10,
            detect=detect_okala_signal,
            mix_ids=(
                "MIX-CF-OKALA-IN-LEVEL",
                "MIX-CF-OKALA-IN-FORK",
                "MIX-CF-OKALA-IN-H-CROSS",
                "MIX-CF-OKALA-IN-REPAIR",
            ),
            note="FOUNDER_PAPER_ACCEPT Okala India — robust WR cells + starter extend",
        )
    )

    from backtest_engine.cf_structure_paper import detect_structure_signal

    register_plugin(
        CfSignalPlugin(
            plugin_id="cf_structure_in",
            family="structure",
            priority=20,
            detect=detect_structure_signal,
            mix_ids=(),  # filled dynamically from overnight accept JSON
            note="FOUNDER_PAPER_ACCEPT structure CF overnight cells (if any)",
        )
    )


def detect_cf_signal(
    underlying: str,
    bars_1m: Optional[list[Bar]] = None,
    *,
    option_ltp: Optional[float] = None,
    premium_meta: Optional[dict[str, Any]] = None,
    spot_underlying: Optional[float] = None,
    big_news_hold: bool = False,
    session_kind: Optional[str] = None,
    veto_reasons: Optional[Sequence[str]] = None,
    plugin_ids: Optional[Sequence[str]] = None,
) -> Optional[dict[str, Any]]:
    """Try registered CF plugins in priority order; return first PAPER hit.

    Same premium contract as Okala: Entry=LTP, Stop×0.75, Target×1.25 when LTP set.
    """
    _ensure_defaults()
    bars = list(bars_1m or [])
    want = set(plugin_ids) if plugin_ids else None
    for plugin in _PLUGINS:
        if not plugin.enabled:
            continue
        if want is not None and plugin.plugin_id not in want:
            continue
        try:
            sig = plugin.detect(
                underlying,
                bars,
                option_ltp=option_ltp,
                premium_meta=premium_meta,
                spot_underlying=spot_underlying,
                big_news_hold=big_news_hold,
                session_kind=session_kind,
                veto_reasons=veto_reasons,
            )
        except TypeError:
            # Older detectors may only take positional underlying/bars
            sig = plugin.detect(underlying, bars)
        if sig and isinstance(sig, dict) and sig.get("side") in ("CE", "PE"):
            out = dict(sig)
            out.setdefault("plugin_id", plugin.plugin_id)
            out.setdefault("cf_family", plugin.family)
            out.setdefault("NO_PROMOTE", True)
            out.setdefault("orders", "refused")
            out.setdefault("paper_only", True)
            return out
    return None


def detect_all_cf_signals(
    underlying: str,
    bars_1m: Optional[list[Bar]] = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Collect hits from every enabled plugin (for multi-book paper watch)."""
    _ensure_defaults()
    bars = list(bars_1m or [])
    hits: list[dict[str, Any]] = []
    for plugin in _PLUGINS:
        if not plugin.enabled:
            continue
        try:
            sig = plugin.detect(underlying, bars, **kwargs)
        except TypeError:
            sig = plugin.detect(underlying, bars)
        if sig and isinstance(sig, dict) and sig.get("side") in ("CE", "PE"):
            out = dict(sig)
            out.setdefault("plugin_id", plugin.plugin_id)
            out.setdefault("cf_family", plugin.family)
            hits.append(out)
    return hits


@dataclass
class RegistryMeta:
    plugins: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""


def registry_meta() -> dict[str, Any]:
    _ensure_defaults()
    return {
        "plugins": [
            {
                "plugin_id": p.plugin_id,
                "family": p.family,
                "priority": p.priority,
                "enabled": p.enabled,
                "mix_ids": list(p.mix_ids),
                "note": p.note,
            }
            for p in _PLUGINS
        ],
        "NO_PROMOTE": True,
        "paper_only": True,
        "note": (
            "Simple CF plugin registry — Okala + structure overnight. "
            "News veto soft-default OFF. Optimize later."
        ),
    }

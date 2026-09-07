"""Okala India PAPER signal detector — FOUNDER_PAPER_ACCEPT starter (NO_PROMOTE).

Simple path: bars → pattern → CE/PE → premium Entry/Stop/Target → paper notify.

NIFTY cells with robust WR > 50% (n≥20) stay the research gate.
BANKNIFTY / SENSEX use the same pattern rules under FOUNDER_STARTER_EXTEND
(no eligible BT cells yet). News veto is OFF by default (NEWS_VETO_ENABLED=false).

PAPER notify only. Never live orders. Never RESEARCH_READY_FOR_PROGRAMMING.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Sequence

from backtest_engine.indicators import Bar, _wilder_atr
from backtest_engine.levels import (
    DEFAULT_PREMIUM_TARGET_PCT,
    bind_option_premium_levels,
)
from backtest_engine.okala_in_proxy import (
    MAGNET_SEED,
    SETUPS,
    classify_regimes,
    leans_for_setup,
    mix_id_for_setup,
)
from backtest_engine.resample import resample
from dhan_client.config import repo_root

FOUNDER_LABEL = "FOUNDER_PAPER_ACCEPT"
NO_PROMOTE = True
PAPER_ENABLE = True
WR_ROBUST_MIN = 0.50
MIN_TRADES = 20
RECON_REL = Path("data/recon/OKALA_IN_BACKTEST_2026-09-07.json")

# Founder mandate: signal on all three index underlyings.
OKALA_UNDERLYINGS = frozenset({"NIFTY", "BANKNIFTY", "SENSEX"})
# BT cells exist for NIFTY(+BN grid) only; BN/SENSEX without WR gate = starter extend.
STARTER_EXTEND_UNDERLYINGS = frozenset({"BANKNIFTY", "SENSEX"})
ELIGIBILITY_CELL = "FOUNDER_PAPER_ACCEPT_CELL"
ELIGIBILITY_EXTEND = "FOUNDER_STARTER_EXTEND"

# PAPER starter premium risk (HYPOTHESIS until swing/greek map exists):
# Entry = LTP, Target = entry×1.25, Stop = entry×0.75.
PAPER_STARTER_TARGET_PCT = DEFAULT_PREMIUM_TARGET_PCT  # 0.25
PAPER_STARTER_STOP_PCT = 0.25

# Specs mirrored from NIFTY robust cells + spirit pairs for extend underlyings.
STARTER_EXTEND_SPECS: tuple[tuple[int, str, tuple[int, int]], ...] = (
    (1, "H_CROSS", (10, 0)),
    (1, "H_CROSS", (30, 40)),
    (1, "H_CROSS", (30, 80)),
    (5, "REPAIR", (60, 50)),
    (1, "FORK", (60, 50)),
    (1, "FORK", (10, 0)),
    (1, "LEVEL", (20, 60)),
    (1, "LEVEL", (30, 70)),
)


def news_veto_enabled() -> bool:
    """Soft-default OFF — founder parked news HOLD on the customer paper path.

    Re-enable later with NEWS_VETO_ENABLED=true|1|yes|on.
    """
    raw = (os.environ.get("NEWS_VETO_ENABLED") or "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class OkalaPaperCell:
    cell: str
    mix_id: str
    underlying: str
    tf_min: int
    regime: str
    magnet_pair: tuple[int, int]
    setup: str
    n: int
    wr_robust: float
    wr_raw: Optional[float] = None
    eligibility: str = ELIGIBILITY_CELL

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["magnet_pair"] = list(self.magnet_pair)
        return d


@dataclass
class OkalaPaperHit:
    mix_id: str
    underlying: str
    lean: str  # CE | PE
    setup: str
    tf_min: int
    regime: str
    magnet_pair: tuple[int, int]
    cell: str
    n: int
    wr_robust: float
    reasons: list[str] = field(default_factory=list)
    founder_label: str = FOUNDER_LABEL
    paper_enable: bool = PAPER_ENABLE
    promote: bool = False
    no_promote: bool = True
    data_gaps: list[str] = field(default_factory=list)
    eligibility: str = ELIGIBILITY_CELL

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["magnet_pair"] = list(self.magnet_pair)
        d["side"] = "BUY_CE" if self.lean == "CE" else "BUY_PE"
        d["orders"] = "refused"
        d["layer"] = "HYPOTHESIS"
        d["gate"] = "FOUNDER_PAPER_ACCEPT_starter_NO_PROMOTE"
        d["win_rate_claim"] = None  # VALIDATION cell WR is research-only
        return d


def _pair_key(pair: Sequence[int] | tuple[int, int]) -> str:
    return f"{int(pair[0])}:{int(pair[1])}"


def _normalize_pair(raw: Any) -> tuple[int, int]:
    if isinstance(raw, str) and ":" in raw:
        a, b = raw.split(":", 1)
        return int(a), int(b)
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return int(raw[0]), int(raw[1])
    raise ValueError(f"bad magnet_pair: {raw!r}")


@lru_cache(maxsize=4)
def load_paper_eligible_cells(
    recon_path: str = "",
    *,
    wr_min: float = WR_ROBUST_MIN,
    min_n: int = MIN_TRADES,
) -> tuple[OkalaPaperCell, ...]:
    """Cells with wr_robust > wr_min and n ≥ min_n (default founder gate)."""
    path = Path(recon_path) if recon_path else (repo_root() / RECON_REL)
    if not path.is_file():
        return tuple()
    blob = json.loads(path.read_text(encoding="utf-8"))
    cells = blob.get("cells") or []
    out: list[OkalaPaperCell] = []
    for row in cells:
        if not isinstance(row, dict):
            continue
        wr = row.get("wr_robust")
        n = int(row.get("n") or 0)
        if wr is None or n < min_n or float(wr) <= wr_min:
            continue
        try:
            pair = _normalize_pair(row.get("magnet_pair"))
        except ValueError:
            continue
        setup = str(row.get("setup") or "")
        if setup not in SETUPS:
            continue
        und = str(row.get("underlying") or "").upper()
        # Eligible WR cells are NIFTY-only in this recon; BN rows never pass gate.
        if und not in ("NIFTY", "BANKNIFTY"):
            continue
        out.append(
            OkalaPaperCell(
                cell=str(row.get("cell") or ""),
                mix_id=str(row.get("mix_id") or mix_id_for_setup(setup)),
                underlying=und,
                tf_min=int(row.get("tf_min") or 0),
                regime=str(row.get("regime") or ""),
                magnet_pair=pair,
                setup=setup,
                n=n,
                wr_robust=float(wr),
                wr_raw=float(row["wr_raw"]) if row.get("wr_raw") is not None else None,
                eligibility=ELIGIBILITY_CELL,
            )
        )
    out.sort(key=lambda c: (-c.wr_robust, -c.n, c.cell))
    return tuple(out)


def clear_eligible_cache() -> None:
    load_paper_eligible_cells.cache_clear()


def is_cell_paper_eligible(
    *,
    underlying: str,
    tf_min: int,
    regime: str,
    magnet_pair: tuple[int, int] | Sequence[int],
    setup: str,
    wr_robust: Optional[float] = None,
    n: Optional[int] = None,
    recon_path: str = "",
) -> bool:
    """Runtime gate: allowlist match, or explicit wr/n threshold when provided."""
    if wr_robust is not None and n is not None:
        return float(wr_robust) > WR_ROBUST_MIN and int(n) >= MIN_TRADES
    pair = (int(magnet_pair[0]), int(magnet_pair[1]))
    und = underlying.upper()
    for cell in load_paper_eligible_cells(recon_path):
        if (
            cell.underlying == und
            and cell.tf_min == int(tf_min)
            and cell.regime == regime
            and cell.magnet_pair == pair
            and cell.setup == setup
        ):
            return True
    return False


def paper_eligible_allowlist(*, recon_path: str = "") -> list[dict[str, Any]]:
    return [c.to_dict() for c in load_paper_eligible_cells(recon_path)]


def big_news_blocks_okala(
    *,
    force: Optional[bool] = None,
    session_kind: Optional[str] = None,
    veto_reasons: Optional[Sequence[str]] = None,
) -> bool:
    """News HOLD on Okala paper ticket — gated by NEWS_VETO_ENABLED (default false).

    ``force=True`` still blocks (explicit test / operator override).
    ``force=False`` never blocks.
    When NEWS_VETO_ENABLED is false, session/veto tags do **not** block.
    """
    if force is True:
        return True
    if force is False:
        return False
    if not news_veto_enabled():
        return False
    kind = (session_kind or "").upper()
    if kind in ("NEWS_DAY", "EXPIRY"):
        return True
    blob = " ".join(str(x) for x in (veto_reasons or [])).upper()
    return any(
        tag in blob
        for tag in ("BIG_NEWS", "NEWS_DAY", "BIG_NEWS_HOLD", "EVENT_WINDOW")
    )


def _bars_for_tf(bars_1m: list[Bar], tf_min: int) -> list[Bar]:
    if tf_min <= 1:
        return list(bars_1m)
    return resample(bars_1m, tf_min)


def _hit_from_cell(
    *,
    und: str,
    lean: str,
    cell: OkalaPaperCell,
    regime_now: str,
) -> OkalaPaperHit:
    reasons = [
        f"{FOUNDER_LABEL}: {cell.eligibility} · {cell.cell or cell.setup}",
        f"pattern={cell.setup} regime={regime_now} tf={cell.tf_min}m "
        f"magnets={_pair_key(cell.magnet_pair)}",
        f"lean={lean} → {'BUY_CE' if lean == 'CE' else 'BUY_PE'}",
        "VALIDATION wr_robust is research-only — not a ticket win-rate claim"
        if cell.eligibility == ELIGIBILITY_CELL
        else (
            f"{ELIGIBILITY_EXTEND}: BN/SENSEX (or ungated) pattern fire — "
            "same Okala rules; caution label; NO_PROMOTE"
        ),
        "NO_PROMOTE live · optimize later · PAPER only",
    ]
    return OkalaPaperHit(
        mix_id=cell.mix_id,
        underlying=und,
        lean=lean,
        setup=cell.setup,
        tf_min=cell.tf_min,
        regime=regime_now,
        magnet_pair=cell.magnet_pair,
        cell=cell.cell or f"{und}|{cell.tf_min}m|{regime_now}|"
        f"{_pair_key(cell.magnet_pair)}|{cell.setup}|{ELIGIBILITY_EXTEND}",
        n=cell.n,
        wr_robust=cell.wr_robust,
        reasons=reasons,
        eligibility=cell.eligibility,
    )


def detect_okala_paper_signals(
    underlying: str,
    bars_1m: list[Bar],
    *,
    recon_path: str = "",
    big_news_hold: bool = False,
    session_kind: Optional[str] = None,
    veto_reasons: Optional[Sequence[str]] = None,
    min_bars: int = 80,
    allow_starter_extend: bool = True,
) -> list[OkalaPaperHit]:
    """Return paper hits when pattern forms. Empty if blocked/DI."""
    und = underlying.upper()
    if und not in OKALA_UNDERLYINGS:
        return []
    if big_news_blocks_okala(
        force=big_news_hold if big_news_hold else None,
        session_kind=session_kind,
        veto_reasons=veto_reasons,
    ):
        return []
    if not bars_1m or len(bars_1m) < min_bars:
        return []

    eligible = [c for c in load_paper_eligible_cells(recon_path) if c.underlying == und]
    use_extend = allow_starter_extend and (
        und in STARTER_EXTEND_UNDERLYINGS or not eligible
    )

    by_tf: dict[int, tuple[list[Bar], list[str], list[float | None]]] = {}
    hits: list[OkalaPaperHit] = []

    def _ensure_tf(tf_min: int) -> tuple[list[Bar], list[str], list[float | None]]:
        if tf_min not in by_tf:
            bars = _bars_for_tf(bars_1m, tf_min)
            if len(bars) < max(40, min_bars // max(tf_min, 1)):
                by_tf[tf_min] = ([], [], [])
            else:
                regimes = classify_regimes(bars)
                atrs = _wilder_atr(bars, 14)
                by_tf[tf_min] = (bars, regimes, atrs)
        return by_tf[tf_min]

    for cell in eligible:
        bars, regimes, atrs = _ensure_tf(cell.tf_min)
        if not bars or not regimes:
            continue
        regime_now = regimes[-1]
        if regime_now != cell.regime:
            continue
        leans = leans_for_setup(cell.setup, bars, cell.magnet_pair, atrs)
        if not leans:
            continue
        lean = leans[-1]
        if lean not in ("CE", "PE"):
            continue
        hits.append(_hit_from_cell(und=und, lean=lean, cell=cell, regime_now=regime_now))

    if use_extend and not hits:
        for tf_min, setup, pair in STARTER_EXTEND_SPECS:
            bars, regimes, atrs = _ensure_tf(tf_min)
            if not bars or not regimes:
                continue
            regime_now = regimes[-1]
            leans = leans_for_setup(setup, bars, pair, atrs)
            if not leans:
                continue
            lean = leans[-1]
            if lean not in ("CE", "PE"):
                continue
            stub = OkalaPaperCell(
                cell="",
                mix_id=mix_id_for_setup(setup),
                underlying=und,
                tf_min=tf_min,
                regime=regime_now,
                magnet_pair=pair,
                setup=setup,
                n=0,
                wr_robust=0.0,
                eligibility=ELIGIBILITY_EXTEND,
            )
            hits.append(
                _hit_from_cell(und=und, lean=lean, cell=stub, regime_now=regime_now)
            )

    hits.sort(
        key=lambda h: (
            0 if h.eligibility == ELIGIBILITY_CELL else 1,
            -h.wr_robust,
            -h.n,
            h.mix_id,
        )
    )
    return hits


def best_okala_paper_hit(
    underlying: str,
    bars_1m: list[Bar],
    **kwargs: Any,
) -> Optional[OkalaPaperHit]:
    hits = detect_okala_paper_signals(underlying, bars_1m, **kwargs)
    return hits[0] if hits else None


def detect_okala_signal(
    underlying: str,
    bars_1m: Optional[list[Bar]] = None,
    *,
    option_ltp: Optional[float] = None,
    premium_meta: Optional[dict[str, Any]] = None,
    spot_underlying: Optional[float] = None,
    recon_path: str = "",
    big_news_hold: bool = False,
    session_kind: Optional[str] = None,
    veto_reasons: Optional[Sequence[str]] = None,
) -> Optional[dict[str, Any]]:
    """Single simple pipeline: pattern → CE/PE → premium levels (PAPER starter).

    Returns None when no pattern. Premium Entry/Stop/Target are option units when
    ``option_ltp`` is provided; otherwise directional intent + honest DI on levels.
    """
    bars = list(bars_1m or [])
    hit = best_okala_paper_hit(
        underlying,
        bars,
        recon_path=recon_path,
        big_news_hold=big_news_hold,
        session_kind=session_kind,
        veto_reasons=veto_reasons,
    )
    if hit is None:
        return None

    spot = spot_underlying
    if spot is None and bars:
        spot = float(bars[-1].close)

    meta = dict(premium_meta or {})
    reasons = list(hit.reasons)
    data_gaps = list(hit.data_gaps)
    entry: Any = None
    stop: Any = None
    target: Any = None
    levels: dict[str, Any] = {}
    strike = meta.get("strike")
    expiry = meta.get("expiry")

    if option_ltp is not None and float(option_ltp) > 0:
        levels = bind_option_premium_levels(
            option_ltp=float(option_ltp),
            lean=hit.lean,
            strike=strike,
            underlying_spot=spot,
            target_pct=PAPER_STARTER_TARGET_PCT,
            stop_pct=PAPER_STARTER_STOP_PCT,
            expiry=expiry,
            premium_source=str(meta.get("source") or "mock_or_dhan_optionchain"),
            bars=bars,
        )
        entry = levels.get("entry")
        stop = levels.get("stop")
        target = levels.get("target")
        strike = levels.get("strike", strike)
        reasons.append(
            f"PAPER starter premium: Entry=LTP Stop=entry×"
            f"{1.0 - PAPER_STARTER_STOP_PCT:.2f} Target=entry×"
            f"{1.0 + PAPER_STARTER_TARGET_PCT:.2f} (MIX-SLTP-PREM-PCT + starter stop). "
            "HYPOTHESIS until swing/greek map. Not a fill."
        )
    else:
        data_gaps.append(
            "DATA_INSUFFICIENT: option premium unbound — directional CE/PE kept; "
            "Entry/Stop/Target empty until LTP bind"
        )
        reasons.append(data_gaps[-1])

    return {
        "side": hit.lean,
        "buy_side": "BUY_CE" if hit.lean == "CE" else "BUY_PE",
        "mix_id": hit.mix_id,
        "entry": entry,
        "stop": stop,
        "target": target,
        "spot_underlying": spot,
        "underlying": hit.underlying,
        "strike": strike,
        "expiry": expiry,
        "unit": "OPTION_PREMIUM" if entry is not None else None,
        "reasons": reasons,
        "data_gaps": data_gaps,
        "eligibility": hit.eligibility,
        "okala_setup": hit.setup,
        "okala_cell": hit.cell,
        "okala_regime": hit.regime,
        "okala_tf_min": hit.tf_min,
        "okala_magnet_pair": list(hit.magnet_pair),
        "research_wr_robust": hit.wr_robust if hit.eligibility == ELIGIBILITY_CELL else None,
        "research_n": hit.n if hit.eligibility == ELIGIBILITY_CELL else None,
        "founder_label": FOUNDER_LABEL,
        "NO_PROMOTE": True,
        "orders": "refused",
        "paper_only": True,
        "news_veto_enabled": news_veto_enabled(),
        "levels": levels,
        "levels_note": (levels or {}).get("levels_note"),
        "layer": "HYPOTHESIS",
        "win_rate_claim": None,
    }


def okala_paper_meta() -> dict[str, Any]:
    cells = load_paper_eligible_cells()
    return {
        "founder_label": FOUNDER_LABEL,
        "paper_enable": PAPER_ENABLE,
        "promote": False,
        "NO_PROMOTE": NO_PROMOTE,
        "wr_robust_min": WR_ROBUST_MIN,
        "min_trades": MIN_TRADES,
        "magnet_seed": MAGNET_SEED,
        "recon": str(RECON_REL),
        "eligible_cells": [c.to_dict() for c in cells],
        "eligible_count": len(cells),
        "underlyings": sorted(OKALA_UNDERLYINGS),
        "starter_extend_underlyings": sorted(STARTER_EXTEND_UNDERLYINGS),
        "news_veto_enabled": news_veto_enabled(),
        "paper_starter_stop_pct": PAPER_STARTER_STOP_PCT,
        "paper_starter_target_pct": PAPER_STARTER_TARGET_PCT,
        "note": (
            "Starter PAPER CE/PE notify. NIFTY uses robust WR>50% cells; "
            "BN/SENSEX = FOUNDER_STARTER_EXTEND same rules. "
            "News veto soft-default OFF (NEWS_VETO_ENABLED). "
            "Catalog win_rate stays null. Live promote forbidden."
        ),
    }

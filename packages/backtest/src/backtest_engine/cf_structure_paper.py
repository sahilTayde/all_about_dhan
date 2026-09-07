"""Structure CF PAPER detector — FOUNDER_PAPER_ACCEPT overnight cells only.

Loads accepted cells from data/recon/CF_OVERNIGHT_*_2026-09-07.json (non-Okala).
Same premium starter as Okala: LTP / ×0.75 stop / ×1.25 target.
PAPER notify only. NO_PROMOTE.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Sequence

from backtest_engine.cf_overnight_catalog import build_catalog, call_lean
from backtest_engine.cf_structure_in_proxy import prep_series
from backtest_engine.indicators import Bar
from backtest_engine.levels import (
    DEFAULT_PREMIUM_TARGET_PCT,
    bind_option_premium_levels,
)
from backtest_engine.okala_in_paper import (
    FOUNDER_LABEL,
    PAPER_STARTER_STOP_PCT,
    PAPER_STARTER_TARGET_PCT,
    big_news_blocks_okala,
    news_veto_enabled,
)
from backtest_engine.resample import resample
from dhan_client.config import repo_root

WR_ROBUST_MIN = 0.50
MIN_TRADES = 20
DATE_TAG = "2026-09-07"
UNDERLYINGS = frozenset({"NIFTY", "BANKNIFTY", "SENSEX"})
STARTER_EXTEND = frozenset({"BANKNIFTY", "SENSEX"})


@dataclass(frozen=True)
class StructurePaperCell:
    cell: str
    mix_id: str
    family: str
    underlying: str
    tf_min: int
    regime: str
    setup: str
    params: dict[str, Any]
    param_key: str
    n: int
    wr_robust: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StructurePaperHit:
    mix_id: str
    underlying: str
    lean: str
    setup: str
    tf_min: int
    regime: str
    params: dict[str, Any]
    cell: str
    n: int
    wr_robust: float
    family: str
    reasons: list[str] = field(default_factory=list)
    founder_label: str = FOUNDER_LABEL
    eligibility: str = "FOUNDER_PAPER_ACCEPT_CELL"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["side"] = "BUY_CE" if self.lean == "CE" else "BUY_PE"
        d["orders"] = "refused"
        d["NO_PROMOTE"] = True
        return d


def _recon_glob(root: Path) -> list[Path]:
    recon = root / "data" / "recon"
    if not recon.is_dir():
        return []
    skip_tokens = ("OKALA", "ROLLUP", "QUEUE", "INVENTORY", "C_SUMMARY", "SKIPS")
    out = []
    for path in sorted(recon.glob(f"CF_OVERNIGHT_*_{DATE_TAG}.json")):
        name = path.name.upper()
        if any(tok in name for tok in skip_tokens):
            continue
        out.append(path)
    return out


@lru_cache(maxsize=2)
def load_structure_eligible_cells(recon_dir: str = "") -> tuple[StructurePaperCell, ...]:
    root = repo_root()
    paths = (
        [Path(recon_dir)]
        if recon_dir
        else _recon_glob(root)
    )
    if recon_dir:
        p = Path(recon_dir)
        paths = [p] if p.is_file() else list(p.glob(f"CF_OVERNIGHT_*_{DATE_TAG}.json"))
    out: list[StructurePaperCell] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows = blob.get("accepted") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            wr = row.get("wr_robust")
            n = int(row.get("n") or 0)
            if wr is None or n < MIN_TRADES or float(wr) <= WR_ROBUST_MIN:
                continue
            und = str(row.get("underlying") or "").upper()
            if und not in UNDERLYINGS:
                continue
            params = row.get("params") or {}
            if not isinstance(params, dict):
                params = {}
            out.append(
                StructurePaperCell(
                    cell=str(row.get("cell") or ""),
                    mix_id=str(row.get("mix_id") or ""),
                    family=str(row.get("family") or ""),
                    underlying=und,
                    tf_min=int(row.get("tf_min") or 0),
                    regime=str(row.get("regime") or ""),
                    setup=str(row.get("setup") or ""),
                    params=dict(params),
                    param_key=str(row.get("param_key") or "default"),
                    n=n,
                    wr_robust=float(wr),
                )
            )
    out.sort(key=lambda c: (-c.wr_robust, -c.n, c.cell))
    return tuple(out)


def clear_structure_cache() -> None:
    load_structure_eligible_cells.cache_clear()


def _arm_for(mix_id: str, setup: str):
    for arm in build_catalog():
        if arm.mix_id == mix_id and arm.setup == setup:
            return arm
    return None


def detect_structure_paper_signals(
    underlying: str,
    bars_1m: list[Bar],
    *,
    big_news_hold: bool = False,
    session_kind: Optional[str] = None,
    veto_reasons: Optional[Sequence[str]] = None,
    min_bars: int = 80,
) -> list[StructurePaperHit]:
    und = underlying.upper()
    if und not in UNDERLYINGS:
        return []
    if big_news_blocks_okala(
        force=big_news_hold if big_news_hold else None,
        session_kind=session_kind,
        veto_reasons=veto_reasons,
    ):
        return []
    if not bars_1m or len(bars_1m) < min_bars:
        return []

    eligible = [c for c in load_structure_eligible_cells() if c.underlying == und]
    # BN/SENSEX: also try NIFTY-accepted specs as FOUNDER_STARTER_EXTEND
    if und in STARTER_EXTEND and not eligible:
        eligible = [
            StructurePaperCell(
                cell=c.cell,
                mix_id=c.mix_id,
                family=c.family,
                underlying=und,
                tf_min=c.tf_min,
                regime=c.regime,
                setup=c.setup,
                params=c.params,
                param_key=c.param_key,
                n=0,
                wr_robust=0.0,
            )
            for c in load_structure_eligible_cells()
            if c.underlying == "NIFTY"
        ]

    by_tf: dict[int, tuple[list[Bar], list[str]]] = {}
    hits: list[StructurePaperHit] = []

    for cell in eligible:
        if cell.tf_min not in by_tf:
            bars = list(bars_1m) if cell.tf_min <= 1 else resample(bars_1m, cell.tf_min)
            need = max(25, min_bars // max(cell.tf_min, 1))
            if len(bars) < need:
                by_tf[cell.tf_min] = ([], [])
            else:
                regimes, _ = prep_series(bars)
                by_tf[cell.tf_min] = (bars, regimes)
        bars, regimes = by_tf[cell.tf_min]
        if not bars or not regimes:
            continue
        regime_now = regimes[-1]
        if cell.n > 0 and regime_now != cell.regime:
            continue
        arm = _arm_for(cell.mix_id, cell.setup)
        if arm is None:
            continue
        try:
            leans = call_lean(arm, bars, cell.params)
        except Exception:
            continue
        if not leans:
            continue
        lean = leans[-1]
        if lean not in ("CE", "PE"):
            continue
        eligibility = (
            "FOUNDER_PAPER_ACCEPT_CELL"
            if cell.n > 0
            else "FOUNDER_STARTER_EXTEND"
        )
        reasons = [
            f"{FOUNDER_LABEL}: {eligibility} · {cell.cell or cell.setup}",
            f"pattern={cell.setup} regime={regime_now} tf={cell.tf_min}m "
            f"params={cell.param_key}",
            f"lean={lean} → {'BUY_CE' if lean == 'CE' else 'BUY_PE'}",
            "NO_PROMOTE live · structure CF overnight · PAPER only",
        ]
        hits.append(
            StructurePaperHit(
                mix_id=cell.mix_id,
                underlying=und,
                lean=lean,
                setup=cell.setup,
                tf_min=cell.tf_min,
                regime=regime_now,
                params=dict(cell.params),
                cell=cell.cell or f"{und}|{cell.tf_min}m|{regime_now}|{cell.mix_id}",
                n=cell.n,
                wr_robust=cell.wr_robust,
                family=cell.family,
                reasons=reasons,
                eligibility=eligibility,
            )
        )

    hits.sort(
        key=lambda h: (
            0 if h.eligibility == "FOUNDER_PAPER_ACCEPT_CELL" else 1,
            -h.wr_robust,
            -h.n,
            h.mix_id,
        )
    )
    return hits


def detect_structure_signal(
    underlying: str,
    bars_1m: Optional[list[Bar]] = None,
    *,
    option_ltp: Optional[float] = None,
    premium_meta: Optional[dict[str, Any]] = None,
    spot_underlying: Optional[float] = None,
    big_news_hold: bool = False,
    session_kind: Optional[str] = None,
    veto_reasons: Optional[Sequence[str]] = None,
) -> Optional[dict[str, Any]]:
    bars = list(bars_1m or [])
    hits = detect_structure_paper_signals(
        underlying,
        bars,
        big_news_hold=big_news_hold,
        session_kind=session_kind,
        veto_reasons=veto_reasons,
    )
    if not hits:
        return None
    hit = hits[0]
    spot = spot_underlying
    if spot is None and bars:
        spot = float(bars[-1].close)
    meta = dict(premium_meta or {})
    reasons = list(hit.reasons)
    data_gaps: list[str] = []
    entry = stop = target = None
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
            f"{1.0 + PAPER_STARTER_TARGET_PCT:.2f}"
        )
    else:
        data_gaps.append(
            "DATA_INSUFFICIENT: option premium unbound — directional CE/PE kept"
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
        "cf_setup": hit.setup,
        "cf_cell": hit.cell,
        "cf_regime": hit.regime,
        "cf_tf_min": hit.tf_min,
        "cf_params": hit.params,
        "cf_family": hit.family,
        "research_wr_robust": (
            hit.wr_robust if hit.eligibility == "FOUNDER_PAPER_ACCEPT_CELL" else None
        ),
        "research_n": hit.n if hit.eligibility == "FOUNDER_PAPER_ACCEPT_CELL" else None,
        "founder_label": FOUNDER_LABEL,
        "NO_PROMOTE": True,
        "orders": "refused",
        "paper_only": True,
        "news_veto_enabled": news_veto_enabled(),
        "levels": levels,
        "layer": "HYPOTHESIS",
        "win_rate_claim": None,
        "plugin_id": "cf_structure_in",
    }


def structure_paper_meta() -> dict[str, Any]:
    cells = load_structure_eligible_cells()
    return {
        "founder_label": FOUNDER_LABEL,
        "eligible_count": len(cells),
        "eligible_cells": [c.to_dict() for c in cells[:50]],
        "NO_PROMOTE": True,
        "paper_starter_stop_pct": PAPER_STARTER_STOP_PCT,
        "paper_starter_target_pct": DEFAULT_PREMIUM_TARGET_PCT,
        "date_tag": DATE_TAG,
    }

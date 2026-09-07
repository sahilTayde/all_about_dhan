"""Codeable Chart Fanatics arms for overnight India permutation grids.

PAPER / research only. EXTERNAL_RESEARCH proxies — not DHAN-DERIVED.
Teacher params may be adjusted on the fly (observation protocol).
NO_PROMOTE. No STRAT-015+.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from backtest_engine.indicators import Bar

LeanFn = Callable[..., list[str]]


@dataclass(frozen=True)
class CfArm:
    """One MIX-CF-* setup with India-port lean + small param grid."""

    family: str
    mix_id: str
    setup: str
    lean_fn: LeanFn
    param_grid: tuple[dict[str, Any], ...]
    india_note: str = "structure_proxy_HYPOTHESIS"
    skip_reason: str | None = None

    def param_key(self, params: dict[str, Any]) -> str:
        if not params:
            return "default"
        return "|".join(f"{k}={params[k]}" for k in sorted(params))


def _grid(**axes: Sequence[Any]) -> tuple[dict[str, Any], ...]:
    """Cartesian product of named axes → frozen param dicts."""
    keys = list(axes.keys())
    if not keys:
        return ({},)
    rows: list[dict[str, Any]] = [{}]
    for key in keys:
        nxt: list[dict[str, Any]] = []
        for base in rows:
            for val in axes[key]:
                row = dict(base)
                row[key] = val
                nxt.append(row)
        rows = nxt
    return tuple(rows)


def build_catalog() -> tuple[CfArm, ...]:
    """All codeable CF arms with compact observation-protocol grids."""
    from backtest_engine.cf_andrea_omor_proxy import (
        lean_cf_andrea_fail_auction,
        lean_cf_andrea_orb_accept,
        lean_cf_andrea_stop_fade,
        lean_cf_omor_mmm_frame,
        lean_cf_omor_ote,
        lean_cf_omor_pdh_reversal,
    )
    from backtest_engine.cf_carmine_jadecap_proxy import (
        lean_cf_carmine_fail_break,
        lean_cf_carmine_open_hold,
        lean_cf_jadecap_fvg_draw,
        lean_cf_jadecap_swing_fail,
    )
    from backtest_engine.cf_marci_tori_proxy import (
        lean_cf_marci_bb_reality,
        lean_cf_marci_rizzy_ext,
        lean_cf_tori_tl_bounce,
        lean_cf_tori_tl_break,
    )
    from backtest_engine.cf_marco_mayne_proxy import (
        lean_cf_marco_eq_sweep,
        lean_cf_marco_sweep_reclaim,
        lean_cf_mayne_breaker,
        lean_cf_mayne_msb_discount,
    )
    from backtest_engine.cf_tg_kane_proxy import (
        lean_cf_kane_eq50,
        lean_cf_kane_po3_sweep,
        lean_cf_tg_ema_wave,
        lean_cf_tg_trident,
    )
    from backtest_engine.cf_umar_forest_proxy import (
        lean_cf_forest_poc_retest,
        lean_cf_forest_vpe_edge,
        lean_cf_umar_morning_top,
    )
    from backtest_engine.cf_usman_brando_proxy import (
        lean_cf_brando_htf_bounce,
        lean_cf_brando_htf_reclaim,
        lean_cf_brando_round_break,
    )
    from backtest_engine.fabio_proxy import (
        lean_cf_break_retest_pd,
        lean_cf_failed_auction,
        lean_cf_mr_to_poc,
    )

    arms: list[CfArm] = [
        # --- Fabio ---
        CfArm(
            "fabio",
            "MIX-CF-FABIO-TREND-NY",
            "FAILED_AUCTION",
            lean_cf_failed_auction,
            _grid(confirm_bars=(2, 3, 5)),
            "PDH/PDL reclaim — India PDH analog OK",
        ),
        CfArm(
            "fabio",
            "MIX-CF-FABIO-TREND-NY",
            "BREAK_RETEST",
            lean_cf_break_retest_pd,
            _grid(retest_bars=(5, 8, 12)),
            "PD break-retest; NY clock unmapped",
        ),
        CfArm(
            "fabio",
            "MIX-CF-FABIO-MR-RANGE",
            "MR_POC",
            lean_cf_mr_to_poc,
            ({},),
            "VA/POC from prior session profile HYPOTHESIS",
        ),
        # --- Marco / Mayne ---
        CfArm(
            "marco_mayne",
            "MIX-CF-MARCO-LIQ-TRAP",
            "SWEEP_RECLAIM",
            lean_cf_marco_sweep_reclaim,
            _grid(confirm_bars=(3, 4, 6)),
        ),
        CfArm(
            "marco_mayne",
            "MIX-CF-MARCO-INT-EXT",
            "EQ_SWEEP",
            lean_cf_marco_eq_sweep,
            _grid(lookback=(30, 40), equal_frac=(0.0008, 0.0015), confirm_bars=(3, 5)),
        ),
        CfArm(
            "marco_mayne",
            "MIX-CF-MAYNE-ICT-HTF",
            "MSB_DISCOUNT",
            lean_cf_mayne_msb_discount,
            _grid(pullback_bars=(25, 40)),
        ),
        CfArm(
            "marco_mayne",
            "MIX-CF-MAYNE-BREAKER",
            "BREAKER",
            lean_cf_mayne_breaker,
            _grid(lookback=(15, 20), max_gap=(8, 12)),
        ),
        # --- Marci / Tori ---
        CfArm(
            "marci_tori",
            "MIX-CF-MARCI-RIZZY",
            "RIZZY_EXT",
            lean_cf_marci_rizzy_ext,
            _grid(lookback=(30, 40)),
        ),
        CfArm(
            "marci_tori",
            "MIX-CF-MARCI-BB-REALITY",
            "BB_REALITY",
            lean_cf_marci_bb_reality,
            _grid(length=(20,), k=(2.0, 2.5)),
        ),
        CfArm(
            "marci_tori",
            "MIX-CF-TORI-TL-BOUNCE",
            "TL_BOUNCE",
            lean_cf_tori_tl_bounce,
            _grid(lookback=(40, 60), touch_frac=(0.0015, 0.0025)),
        ),
        CfArm(
            "marci_tori",
            "MIX-CF-TORI-TL-BREAK",
            "TL_BREAK",
            lean_cf_tori_tl_break,
            _grid(lookback=(40, 60)),
        ),
        # --- TG / Kane ---
        CfArm(
            "tg_kane",
            "MIX-CF-TG-TRIDENT",
            "TRIDENT",
            lean_cf_tg_trident,
            _grid(max_body_frac=(0.30, 0.35), fvg_lookback=(4, 6)),
        ),
        CfArm(
            "tg_kane",
            "MIX-CF-TG-EMA-WAVE",
            "EMA_WAVE",
            lean_cf_tg_ema_wave,
            _grid(mid_len=(13, 15), pullback_bars=(2, 3)),
        ),
        CfArm(
            "tg_kane",
            "MIX-CF-KANE-EQ50",
            "EQ50",
            lean_cf_kane_eq50,
            _grid(lookback=(30, 40), touch_frac=(0.0015, 0.002)),
        ),
        CfArm(
            "tg_kane",
            "MIX-CF-KANE-PO3-SMT",
            "PO3_SWEEP",
            lean_cf_kane_po3_sweep,
            _grid(lookback=(15, 20), confirm_bars=(3, 5)),
        ),
        # --- Umar / Forest ---
        CfArm(
            "umar_forest",
            "MIX-CF-UMAR-MORNING-TOP",
            "MORNING_TOP",
            lean_cf_umar_morning_top,
            _grid(gap_frac=(0.0010, 0.0015), bounce_look=(12, 16)),
        ),
        CfArm(
            "umar_forest",
            "MIX-CF-FOREST-VPE-EDGE",
            "VPE_EDGE",
            lean_cf_forest_vpe_edge,
            _grid(touch_frac=(0.0010, 0.0015)),
        ),
        CfArm(
            "umar_forest",
            "MIX-CF-FOREST-POC-RETEST",
            "POC_RETEST",
            lean_cf_forest_poc_retest,
            _grid(touch_frac=(0.0015, 0.002), trend_look=(15, 20)),
        ),
        # --- Carmine / Jadecap ---
        CfArm(
            "carmine_jadecap",
            "MIX-CF-CARMINE-FAIL-BREAK",
            "FAIL_BREAK",
            lean_cf_carmine_fail_break,
            _grid(confirm_bars=(3, 4, 6)),
        ),
        CfArm(
            "carmine_jadecap",
            "MIX-CF-CARMINE-OPEN-HOLD",
            "OPEN_HOLD",
            lean_cf_carmine_open_hold,
            _grid(pullback_bars=(8, 12), hold_frac=(0.0002, 0.0003)),
        ),
        CfArm(
            "carmine_jadecap",
            "MIX-CF-JADECAP-SWING-FAIL",
            "SWING_FAIL",
            lean_cf_jadecap_swing_fail,
            _grid(confirm_bars=(4, 6)),
        ),
        CfArm(
            "carmine_jadecap",
            "MIX-CF-JADECAP-FVG-DRAW",
            "FVG_DRAW",
            lean_cf_jadecap_fvg_draw,
            _grid(confirm_bars=(6, 8)),
        ),
        # --- Usman / Brando ---
        CfArm(
            "usman_brando",
            "MIX-CF-BRANDO-ROUND-BREAK",
            "ROUND_BREAK",
            lean_cf_brando_round_break,
            _grid(round_step=(50.0, 100.0), confirm_bars=(2, 3)),
        ),
        CfArm(
            "usman_brando",
            "MIX-CF-BRANDO-HTF-RECLAIM",
            "HTF_RECLAIM",
            lean_cf_brando_htf_reclaim,
            _grid(swing_days=(15, 20), confirm_bars=(6, 8)),
        ),
        CfArm(
            "usman_brando",
            "MIX-CF-BRANDO-HTF-BOUNCE",
            "HTF_BOUNCE",
            lean_cf_brando_htf_bounce,
            _grid(swing_lookback=(40, 60), touch_frac=(0.0015, 0.002)),
        ),
        # --- Andrea / Omor ---
        CfArm(
            "andrea_omor",
            "MIX-CF-ANDREA-FAIL-AUCTION",
            "FAIL_AUCTION",
            lean_cf_andrea_fail_auction,
            _grid(confirm_bars=(4, 6)),
        ),
        CfArm(
            "andrea_omor",
            "MIX-CF-ANDREA-ORB-ACCEPT",
            "ORB_ACCEPT",
            lean_cf_andrea_orb_accept,
            _grid(confirm_bars=(2, 3), hold_frac=(0.0002, 0.0004)),
        ),
        CfArm(
            "andrea_omor",
            "MIX-CF-ANDREA-STOP-FADE",
            "STOP_FADE",
            lean_cf_andrea_stop_fade,
            _grid(confirm_bars=(2, 3)),
        ),
        CfArm(
            "andrea_omor",
            "MIX-CF-OMOR-MMM-FRAME",
            "MMM_FRAME",
            lean_cf_omor_mmm_frame,
            _grid(confirm_bars=(4, 5)),
        ),
        CfArm(
            "andrea_omor",
            "MIX-CF-OMOR-OTE",
            "OTE",
            lean_cf_omor_ote,
            _grid(swing_lookback=(15, 20), ote_lo=(0.55, 0.58), ote_hi=(0.66, 0.70)),
        ),
        CfArm(
            "andrea_omor",
            "MIX-CF-OMOR-PDH-REVERSAL",
            "PDH_REV",
            lean_cf_omor_pdh_reversal,
            _grid(near_frac=(0.0010, 0.0015), confirm_bars=(4, 6)),
        ),
    ]
    return tuple(arms)


# MIX rows that cannot run an INDEX OHLC overnight grid (missing India alternative).
SKIP_MIXES: tuple[dict[str, str], ...] = (
    {
        "mix_id": "MIX-CF-USMAN-OI-STRIKE",
        "reason": "Needs OPTIDX OI strike map — not in INDEX OHLC cache",
    },
    {
        "mix_id": "MIX-CF-USMAN-0DTE-GAMMA",
        "reason": "Needs 0DTE greeks / gamma surface — DATA_INSUFFICIENT",
    },
    {
        "mix_id": "MIX-CF-USMAN-WEEKLY-SIZE",
        "reason": "Premium DOW sizing — not structure lean",
    },
    {
        "mix_id": "MIX-CF-USMAN-PRICE-STOP",
        "reason": "Teacher price-stop book; no India structure port frozen",
    },
    {
        "mix_id": "MIX-CF-BRANDO-SIZE-ZERO",
        "reason": "Premium max-loss size rule — not OHLC pattern",
    },
    {
        "mix_id": "MIX-CF-BRANDO-NEWS-ALIGN",
        "reason": "News+level gate; news calendar DI for overnight grid",
    },
    {
        "mix_id": "MIX-CF-CARMINE-ABSORB",
        "reason": "Order-flow absorb required — PARKED / no India OF tape",
    },
    {
        "mix_id": "MIX-CF-JADECAP-SESSION-LIQ",
        "reason": "Asia/London/NY session stack — NSE clock map DI",
    },
    {
        "mix_id": "MIX-CF-ANDREA-ABSORB",
        "reason": "Footprint / OF absorb — PARKED",
    },
    {
        "mix_id": "MIX-CF-OMOR-KZ-ADR",
        "reason": "London/NY ADR killzone — NSE analog underdefined",
    },
    {
        "mix_id": "MIX-CF-UMAR-OPENING-DRIVE",
        "reason": "Named-only catalog row; no codeable lean beyond morning-top",
    },
)


def call_lean(arm: CfArm, bars: list[Bar], params: dict[str, Any]) -> list[str]:
    return arm.lean_fn(bars, **params)


def families() -> tuple[str, ...]:
    return tuple(sorted({a.family for a in build_catalog()}))

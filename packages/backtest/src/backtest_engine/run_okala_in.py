"""Run Okala India adaptation grid — MIX-CF-OKALA-IN-*.

PAPER/research only. Cache OHLC. NO_PROMOTE. Teacher WR claims stay claims.
CLI: python -m backtest_engine okala-in
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.fetch import INDEX_YAML, load_cached_series
from backtest_engine.indicators import _wilder_atr
from backtest_engine.okala_in_proxy import (
    MAGNET_SEED,
    OUTLIER_TRIM,
    REGIMES,
    SETUPS,
    SL_ATR_MULT,
    TP_SL_RATIO,
    classify_regimes,
    leans_for_setup,
    magnet_pairs_meta,
    mix_id_for_setup,
    sample_magnet_pairs,
    simulate_okala,
    wr_stats,
)
from backtest_engine.resample import resample

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}
UNDERLYINGS = ("NIFTY", "BANKNIFTY")
TF_MINUTES = (1, 2, 3, 5, 10, 15)
MIN_BARS = {1: 5_000, 2: 2_500, 3: 2_000, 5: 1_200, 10: 600, 15: 400}
MIN_TRADES_CELL = 20


def _log(msg: str) -> None:
    print(f"[okala-in] {msg}", file=sys.stderr, flush=True)


def _trim_bars_years(bars: list, years: float) -> list:
    if not bars or years <= 0:
        return list(bars)
    end_ts = bars[-1].ts
    start_ts = end_ts - int(years * 365 * 86400)
    return [b for b in bars if b.ts >= start_ts]


def _cell_key(
    underlying: str,
    tf: int,
    regime: str,
    pair: tuple[int, int],
    setup: str,
) -> str:
    return f"{underlying}|{tf}m|{regime}|{pair[0]}:{pair[1]}|{setup}"


def run_okala_in(
    client: Optional[DhanClient] = None,
    *,
    years: float = 2.0,
    years_1m: float = 0.5,
    underlyings: tuple[str, ...] = UNDERLYINGS,
    tfs: tuple[int, ...] = TF_MINUTES,
    setups: tuple[str, ...] = SETUPS,
    magnet_seed: int = MAGNET_SEED,
    write_reports: bool = True,
) -> dict[str, Any]:
    """Full grid: underlying × TF × regime × magnet-pair × setup.

    client unused when cache is present (no live fetch; no invented fills).
    """
    _ = client  # optional; cache-only path
    t0 = time.time()
    pairs = sample_magnet_pairs(seed=magnet_seed)
    pairs_meta = magnet_pairs_meta(seed=magnet_seed)
    cells: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []
    bar_meta: dict[str, Any] = {}

    for underlying in underlyings:
        if underlying not in INDEX_BY_NAME:
            data_gaps.append({"underlying": underlying, "reason": "unknown_index"})
            continue
        _, sid, seg, inst = INDEX_BY_NAME[underlying]
        bars_1m_all = load_cached_series(
            security_id=str(sid),
            exchange_segment=seg,
            instrument=inst,
            interval=1,
        )
        if not bars_1m_all:
            data_gaps.append(
                {
                    "underlying": underlying,
                    "tf": "all",
                    "status": "DATA_INSUFFICIENT",
                    "reason": "no_cached_1m_ohlc",
                }
            )
            _log(f"{underlying}: no cache → DI")
            continue
        for tf in tfs:
            lookback = years_1m if tf == 1 else years
            bars_1m = _trim_bars_years(bars_1m_all, lookback)
            bars = resample(bars_1m, tf) if tf > 1 else list(bars_1m)
            need = MIN_BARS.get(tf, 400)
            meta_key = f"{underlying}_{tf}m"
            bar_meta[meta_key] = {
                "n_bars": len(bars),
                "lookback_years": lookback,
                "from_ts": bars[0].ts if bars else None,
                "to_ts": bars[-1].ts if bars else None,
                "min_bars_required": need,
            }
            if len(bars) < need:
                data_gaps.append(
                    {
                        "underlying": underlying,
                        "tf_min": tf,
                        "status": "DATA_INSUFFICIENT",
                        "n_bars": len(bars),
                        "need": need,
                    }
                )
                for regime in REGIMES:
                    for pair in pairs:
                        for setup in setups:
                            cells.append(
                                {
                                    "cell": _cell_key(underlying, tf, regime, pair, setup),
                                    "mix_id": mix_id_for_setup(setup),
                                    "underlying": underlying,
                                    "tf_min": tf,
                                    "regime": regime,
                                    "magnet_pair": list(pair),
                                    "setup": setup,
                                    "status": "DATA_INSUFFICIENT",
                                    "promote": False,
                                    "validated": False,
                                    "n": 0,
                                    "wr_raw": None,
                                    "wr_robust": None,
                                    "reason": f"bars<{need}",
                                    "layer": "VALIDATION",
                                    "note": "NO_PROMOTE",
                                }
                            )
                _log(f"{underlying} {tf}m: DI bars={len(bars)} need={need}")
                continue

            regimes = classify_regimes(bars)
            atrs = _wilder_atr(bars, 14)
            _log(
                f"{underlying} {tf}m bars={len(bars)} lookback={lookback}y "
                f"pairs={len(pairs)} setups={len(setups)}"
            )

            for pair in pairs:
                for setup in setups:
                    mix_id = mix_id_for_setup(setup)
                    leans = leans_for_setup(setup, bars, pair, atrs)
                    trades = simulate_okala(
                        bars,
                        leans,
                        regimes,
                        atrs,
                        strategy_id=mix_id,
                        underlying=underlying,
                        pair=pair,
                        setup=setup,
                        tf_min=tf,
                    )
                    for regime in REGIMES:
                        subset = [t for t in trades if t.regime == regime]
                        stats = wr_stats(subset, trim=OUTLIER_TRIM)
                        status = "VALIDATION"
                        reason = "ok"
                        if stats["n"] < MIN_TRADES_CELL:
                            status = "DATA_INSUFFICIENT" if stats["n"] == 0 else "SMALL_SAMPLE"
                            reason = f"n<{MIN_TRADES_CELL}"
                        cells.append(
                            {
                                "cell": _cell_key(underlying, tf, regime, pair, setup),
                                "mix_id": mix_id,
                                "underlying": underlying,
                                "tf_min": tf,
                                "regime": regime,
                                "magnet_pair": list(pair),
                                "setup": setup,
                                "status": status,
                                "promote": False,
                                "validated": False,
                                "customer_default": False,
                                "n": stats["n"],
                                "wins": stats["wins"],
                                "wr_raw": stats["wr_raw"],
                                "n_robust": stats["n_robust"],
                                "wins_robust": stats["wins_robust"],
                                "wr_robust": stats["wr_robust"],
                                "expectancy_raw": stats["expectancy_raw"],
                                "expectancy_robust": stats["expectancy_robust"],
                                "outlier_method": stats["outlier_method"],
                                "reason": reason,
                                "layer": "VALIDATION",
                                "unit": "INDEX_POINTS_PROXY_NOT_OPTION_PREMIUM",
                                "risk_port": {
                                    "hypothesis": "NQ_10_15_to_ATR_scaled",
                                    "sl_atr_mult": SL_ATR_MULT,
                                    "tp_sl_ratio": TP_SL_RATIO,
                                },
                                "note": "NO_PROMOTE; teacher_65_70_claims_null",
                            }
                        )

    elapsed = time.time() - t0
    ranked = [
        c
        for c in cells
        if c.get("wr_robust") is not None and c.get("n", 0) >= MIN_TRADES_CELL
    ]
    best = sorted(ranked, key=lambda c: (c["wr_robust"], c["n"]), reverse=True)[:25]
    worst = sorted(ranked, key=lambda c: (c["wr_robust"], -c["n"]))[:25]
    report: dict[str, Any] = {
        "run_id": "OKALA_IN_BACKTEST_2026-09-07",
        "layer": "VALIDATION",
        "hypothesis_parent": "MIX-CF-OKALA-* India adaptation (PROJECT-DERIVED / observation-gated)",
        "origin": "EXTERNAL_RESEARCH teacher + PROJECT_MIX India port",
        "bind": "teams/01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md",
        "promote": False,
        "NO_PROMOTE": True,
        "teacher_wr_claims": "null — title 65% / host 70% / guest mid-low 70s stay CLAIMS",
        "magnet_pairs": pairs_meta,
        "regimes_definition": {
            "layer": "HYPOTHESIS",
            "bullish": "ADX>=22 and SMA20>SMA50 and SMA20_slope_5 > 0.05*ATR14",
            "bearish": "ADX>=22 and SMA20<SMA50 and SMA20_slope_5 < -0.05*ATR14",
            "sideways": "ADX<18 and Kaufman_ER20<0.25",
            "choppy": "else (noisy/mixed)",
        },
        "outlier_exclusion": {
            "method": f"drop_top_bottom_{int(OUTLIER_TRIM * 100)}pct_trade_pnl",
            "report_both": ["wr_raw", "wr_robust"],
        },
        "risk_conversion_hypothesis": {
            "teacher_nq": "SL=10 TP1≈15 points",
            "india_port": f"SL=max({SL_ATR_MULT}*ATR14, floor); TP=SL*{TP_SL_RATIO}",
            "note": "Not inventing NIFTY point identity with NQ; ATR-scaled HYPOTHESIS only",
        },
        "setups": {
            "LEVEL": "magnet reaction MR — codeable",
            "FORK": "capitulation + failed low + HH — codeable proxy",
            "H_CROSS": "bounce→rally→bearish pair reject — codeable stand-in; exact cross DI",
            "REPAIR": "LEVEL + repair-candle confluence only (not blind entry)",
        },
        "underlyings": list(underlyings),
        "tfs_min": list(tfs),
        "years": years,
        "years_1m": years_1m,
        "min_trades_cell": MIN_TRADES_CELL,
        "bar_meta": bar_meta,
        "data_gaps": data_gaps,
        "n_cells": len(cells),
        "n_ranked": len(ranked),
        "best_cells": best,
        "worst_cells": worst,
        "elapsed_sec": round(elapsed, 2),
        "cells": cells,
    }

    if write_reports:
        _write_reports(report)
    return report


def _write_reports(report: dict[str, Any]) -> None:
    out_dir = repo_root() / "data" / "recon"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "OKALA_IN_BACKTEST_2026-09-07"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    # Full JSON (cells included)
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_render_md(report), encoding="utf-8")
    _log(f"wrote {json_path}")
    _log(f"wrote {md_path}")


def _fmt_wr(x: Any) -> str:
    if x is None:
        return "—"
    return f"{100.0 * float(x):.1f}%"


def _render_md(report: dict[str, Any]) -> str:
    pairs = report["magnet_pairs"]
    lines: list[str] = []
    lines.append("# Okala India adaptation backtest — 2026-09-07")
    lines.append("")
    lines.append("**Layer:** `VALIDATION` (WR outputs) / rules = `HYPOTHESIS`")
    lines.append("**Gate:** **NO_PROMOTE** · `customer_default: false` · teacher 65%/70% = CLAIMS only")
    lines.append("**Bind:** `teams/01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md`")
    lines.append("**IDs:** `MIX-CF-OKALA-IN-{LEVEL,FORK,H-CROSS,REPAIR}` — India adaptation family; not STRAT-015+; not NQ identity")
    lines.append("")
    lines.append("## Honesty")
    lines.append("")
    lines.append("```text")
    lines.append("promote: false")
    lines.append("NO_PROMOTE: true")
    lines.append("unit: INDEX_POINTS_PROXY_NOT_OPTION_PREMIUM")
    lines.append("fills: local OHLC cache only — no invented Dhan fills")
    lines.append("teacher_wr: null")
    lines.append("```")
    lines.append("")
    lines.append("## Magnet pairs (seed-locked)")
    lines.append("")
    lines.append(f"- **Seed:** `{pairs['seed']}`")
    lines.append(f"- **Modulus:** {pairs['modulus']} (last-two-digit INDEX grid)")
    lines.append(f"- **Residue search space:** `{pairs['residue_space']}`")
    lines.append(f"- **Spirit fixed (3):** `{pairs['spirit_fixed']}` → (10,100→0), (30,70), (20,60)")
    lines.append(f"- **All 10 pairs (long_residue, short_residue):** `{pairs['pairs']}`")
    lines.append(f"- **Meaning:** {pairs['pair_meaning']}")
    lines.append("")
    lines.append("## Regimes (HYPOTHESIS)")
    lines.append("")
    for k, v in report["regimes_definition"].items():
        if k == "layer":
            continue
        lines.append(f"- **{k}:** {v}")
    lines.append("")
    lines.append("## Outlier exclusion")
    lines.append("")
    lines.append(
        f"- Method: **{report['outlier_exclusion']['method']}** "
        "(drop extreme trade PnL tails before robust WR)."
    )
    lines.append("- Report both `wr_raw` and `wr_robust`.")
    lines.append("")
    lines.append("## Risk conversion (HYPOTHESIS)")
    lines.append("")
    rc = report["risk_conversion_hypothesis"]
    lines.append(f"- Teacher NQ: {rc['teacher_nq']}")
    lines.append(f"- India port: {rc['india_port']}")
    lines.append(f"- Note: {rc['note']}")
    lines.append("")
    lines.append("## Setups")
    lines.append("")
    for k, v in report["setups"].items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append(f"- Underlyings: {report['underlyings']}")
    lines.append(f"- TFs (min): {report['tfs_min']}")
    lines.append(f"- Lookback: {report['years']}y (TF>1m); **{report['years_1m']}y for 1m** (runtime cap)")
    lines.append(f"- Cells: {report['n_cells']} · ranked (n≥{report['min_trades_cell']}): {report['n_ranked']}")
    lines.append(f"- Elapsed: {report['elapsed_sec']}s")
    lines.append("")
    if report.get("data_gaps"):
        lines.append("### DATA_INSUFFICIENT / gaps")
        lines.append("")
        for g in report["data_gaps"][:40]:
            lines.append(f"- `{g}`")
        lines.append("")
    lines.append("### Bar meta")
    lines.append("")
    lines.append("| Series | Bars | Lookback y |")
    lines.append("|--------|------|------------|")
    for k, v in sorted((report.get("bar_meta") or {}).items()):
        lines.append(f"| {k} | {v.get('n_bars')} | {v.get('lookback_years')} |")
    lines.append("")
    lines.append("## Best cells (VALIDATION · wr_robust · n≥min)")
    lines.append("")
    lines.append("| Rank | Cell | n | WR raw | WR robust | Exp robust |")
    lines.append("|------|------|---|--------|-----------|------------|")
    for i, c in enumerate(report.get("best_cells") or [], 1):
        lines.append(
            f"| {i} | `{c['cell']}` | {c['n']} | {_fmt_wr(c['wr_raw'])} | "
            f"{_fmt_wr(c['wr_robust'])} | {c.get('expectancy_robust')} |"
        )
    lines.append("")
    lines.append("## Worst cells (VALIDATION · wr_robust · n≥min)")
    lines.append("")
    lines.append("| Rank | Cell | n | WR raw | WR robust | Exp robust |")
    lines.append("|------|------|---|--------|-----------|------------|")
    for i, c in enumerate(report.get("worst_cells") or [], 1):
        lines.append(
            f"| {i} | `{c['cell']}` | {c['n']} | {_fmt_wr(c['wr_raw'])} | "
            f"{_fmt_wr(c['wr_robust'])} | {c.get('expectancy_robust')} |"
        )
    lines.append("")
    lines.append("## Heat snapshot — best WR by underlying × TF (max wr_robust across regime/pair/setup)")
    lines.append("")
    heat: dict[tuple[str, int], float] = {}
    heat_n: dict[tuple[str, int], int] = {}
    for c in report.get("cells") or []:
        if c.get("wr_robust") is None or c.get("n", 0) < report["min_trades_cell"]:
            continue
        key = (c["underlying"], c["tf_min"])
        wr = float(c["wr_robust"])
        if key not in heat or wr > heat[key]:
            heat[key] = wr
            heat_n[key] = int(c["n"])
    lines.append("| Underlying | TF | Best wr_robust | n at that cell |")
    lines.append("|------------|----|----------------|----------------|")
    for und in report["underlyings"]:
        for tf in report["tfs_min"]:
            key = (und, tf)
            if key in heat:
                lines.append(f"| {und} | {tf}m | {_fmt_wr(heat[key])} | {heat_n[key]} |")
            else:
                lines.append(f"| {und} | {tf}m | DI / no ranked cell | — |")
    lines.append("")
    lines.append("## Explicit gate")
    lines.append("")
    lines.append("**NO_PROMOTE.** Do not set `RESEARCH_READY_FOR_PROGRAMMING`. Do not merge into `MIX-DEFAULT-BUY`.")
    lines.append("Catalog `win_rate` stays **null**. These WR numbers are research VALIDATION only.")
    lines.append("")
    lines.append(f"_Generated {datetime.now(IST).isoformat()}_")
    lines.append("")
    return "\n".join(lines)

"""Overnight CF India permutation grid — structure families + Okala rollup.

CLI: python -m backtest_engine cf-overnight
PAPER / research only. NO_PROMOTE. Cache OHLC. Outlier-robust WR (trim 5%).
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

from backtest_engine.cf_overnight_catalog import SKIP_MIXES, build_catalog, call_lean
from backtest_engine.cf_structure_in_proxy import prep_series, score_by_regime, simulate_structure
from backtest_engine.fetch import INDEX_YAML, load_cached_series
from backtest_engine.okala_in_proxy import OUTLIER_TRIM, REGIMES
from backtest_engine.resample import resample

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}
UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
TF_MINUTES = (1, 2, 3, 5, 10, 15)
MIN_BARS = {1: 5_000, 2: 2_500, 3: 2_000, 5: 1_200, 10: 600, 15: 400}
MIN_TRADES = 20
WR_ACCEPT = 0.50
DATE_TAG = "2026-09-07"


def _log(msg: str) -> None:
    print(f"[cf-overnight] {msg}", file=sys.stderr, flush=True)


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
    mix_id: str,
    setup: str,
    param_key: str,
) -> str:
    return f"{underlying}|{tf}m|{regime}|{mix_id}|{setup}|{param_key}"


def _write_json(path: Path, blob: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob, indent=2, default=str) + "\n", encoding="utf-8")


def _okala_accepted_from_recon(root: Path) -> list[dict[str, Any]]:
    path = root / "data/recon/OKALA_IN_BACKTEST_2026-09-07.json"
    if not path.is_file():
        return []
    blob = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in blob.get("cells") or []:
        if not isinstance(row, dict):
            continue
        wr = row.get("wr_robust")
        n = int(row.get("n") or 0)
        if wr is None or n < MIN_TRADES or float(wr) <= WR_ACCEPT:
            continue
        out.append(
            {
                **row,
                "family": "okala",
                "founder_label": "FOUNDER_PAPER_ACCEPT",
                "paper_enable": True,
                "promote": False,
            }
        )
    out.sort(key=lambda r: (-float(r["wr_robust"]), -int(r["n"])))
    return out


def run_cf_overnight(
    client: Optional[DhanClient] = None,
    *,
    years: float = 2.0,
    years_1m: float = 0.5,
    underlyings: tuple[str, ...] = UNDERLYINGS,
    tfs: tuple[int, ...] = TF_MINUTES,
    families: Optional[tuple[str, ...]] = None,
    write_reports: bool = True,
) -> dict[str, Any]:
    """Full structure grid + Okala accepted rollup.

    client unused when cache present (no invented fills).
    """
    _ = client
    t0 = time.time()
    root = repo_root()
    arms = build_catalog()
    if families:
        want = set(families)
        arms = tuple(a for a in arms if a.family in want)

    cells: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []
    bar_meta: dict[str, Any] = {}
    family_cells: dict[str, list[dict[str, Any]]] = {}

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
                continue
            regimes, atrs = prep_series(bars)
            _log(f"{underlying} {tf}m bars={len(bars)} arms={len(arms)}")
            for arm in arms:
                for params in arm.param_grid:
                    try:
                        leans = call_lean(arm, bars, params)
                    except Exception as exc:  # observation protocol: skip bad params
                        data_gaps.append(
                            {
                                "mix_id": arm.mix_id,
                                "setup": arm.setup,
                                "params": params,
                                "error": f"{exc.__class__.__name__}: {exc}",
                                "status": "LEAN_ERROR_SKIPPED",
                            }
                        )
                        continue
                    trades_all = simulate_structure(
                        bars,
                        leans,
                        regimes,
                        atrs,
                        strategy_id=arm.mix_id,
                        underlying=underlying,
                        setup=arm.setup,
                        tf_min=tf,
                        params=params,
                    )
                    by_reg = score_by_regime(trades_all)
                    pkey = arm.param_key(params)
                    for regime in REGIMES:
                        st = by_reg[regime]
                        n = int(st.get("n") or 0)
                        wr_r = st.get("wr_robust")
                        accept = (
                            wr_r is not None
                            and n >= MIN_TRADES
                            and float(wr_r) > WR_ACCEPT
                        )
                        row = {
                            "cell": _cell_key(
                                underlying, tf, regime, arm.mix_id, arm.setup, pkey
                            ),
                            "family": arm.family,
                            "mix_id": arm.mix_id,
                            "setup": arm.setup,
                            "underlying": underlying,
                            "tf_min": tf,
                            "regime": regime,
                            "params": params,
                            "param_key": pkey,
                            "n": n,
                            "wr_raw": st.get("wr_raw"),
                            "wr_robust": wr_r,
                            "expectancy_robust": st.get("expectancy_robust"),
                            "outlier_method": st.get("outlier_method"),
                            "status": "SCORED" if n else "NO_TRADES",
                            "founder_label": (
                                "FOUNDER_PAPER_ACCEPT" if accept else None
                            ),
                            "paper_enable": bool(accept),
                            "promote": False,
                            "NO_PROMOTE": True,
                            "validated": False,
                            "layer": "VALIDATION" if n else "HYPOTHESIS",
                            "india_note": arm.india_note,
                        }
                        cells.append(row)
                        family_cells.setdefault(arm.family, []).append(row)

    accepted = [c for c in cells if c.get("paper_enable")]
    accepted.sort(
        key=lambda r: (-float(r["wr_robust"] or 0), -int(r["n"] or 0), r["cell"])
    )
    okala_accepted = _okala_accepted_from_recon(root)
    skips = list(SKIP_MIXES)

    report: dict[str, Any] = {
        "as_of": DATE_TAG,
        "generated_at": datetime.now(tz=IST).isoformat(),
        "layer": "VALIDATION",
        "promote": False,
        "NO_PROMOTE": True,
        "research_ready_for_programming": False,
        "wr_gate": {">": WR_ACCEPT, "min_n": MIN_TRADES, "trim": OUTLIER_TRIM},
        "underlyings": list(underlyings),
        "tfs": list(tfs),
        "families_tested": sorted({a.family for a in arms}) + ["okala"],
        "arms": len(arms),
        "cells": len(cells),
        "accepted_structure": len(accepted),
        "accepted_okala": len(okala_accepted),
        "accepted_cells": accepted[:200],
        "okala_accepted_cells": okala_accepted[:50],
        "skips": skips,
        "data_gaps": data_gaps[:200],
        "bar_meta": bar_meta,
        "elapsed_s": round(time.time() - t0, 2),
        "unit": "INDEX_POINTS_PROXY_NOT_OPTION_PREMIUM",
        "note": (
            "Structure CF overnight permutations + Okala prior grid. "
            "PAPER FOUNDER_PAPER_ACCEPT when robust WR>50% and n≥20. "
            "NO_PROMOTE live. Catalog win_rate stays null."
        ),
    }

    if write_reports:
        recon = root / "data" / "recon"
        recon.mkdir(parents=True, exist_ok=True)
        # Per-family JSON (full cells)
        for fam, rows in family_cells.items():
            fam_accept = [r for r in rows if r.get("paper_enable")]
            fam_accept.sort(
                key=lambda r: (-float(r["wr_robust"] or 0), -int(r["n"] or 0))
            )
            blob = {
                "family": fam,
                "as_of": DATE_TAG,
                "promote": False,
                "NO_PROMOTE": True,
                "n_cells": len(rows),
                "n_accepted": len(fam_accept),
                "accepted": fam_accept,
                "cells": rows,
                "wr_gate": report["wr_gate"],
            }
            _write_json(recon / f"CF_OVERNIGHT_{fam.upper()}_{DATE_TAG}.json", blob)
        # Okala family pointer
        _write_json(
            recon / f"CF_OVERNIGHT_OKALA_{DATE_TAG}.json",
            {
                "family": "okala",
                "as_of": DATE_TAG,
                "source": "OKALA_IN_BACKTEST_2026-09-07.json",
                "promote": False,
                "NO_PROMOTE": True,
                "n_accepted": len(okala_accepted),
                "accepted": okala_accepted,
                "wired": True,
                "detector": "backtest_engine.okala_in_paper",
            },
        )
        # Skips wake-up
        skip_md = recon / f"CF_OVERNIGHT_SKIPS_{DATE_TAG}.md"
        lines = [
            f"# CF overnight skips — {DATE_TAG}",
            "",
            "**Gate:** PAPER · NO_PROMOTE · missing India alternative or uncodeable",
            "",
            "| MIX | Reason |",
            "|-----|--------|",
        ]
        for s in skips:
            lines.append(f"| `{s['mix_id']}` | {s['reason']} |")
        lines.append("")
        skip_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Rollup JSON (accepted only + summary — full cells live in family files)
        _write_json(recon / f"CF_OVERNIGHT_BACKTEST_ROLLUP_{DATE_TAG}.json", report)
        # Rollup MD
        md_path = recon / f"CF_OVERNIGHT_BACKTEST_ROLLUP_{DATE_TAG}.md"
        md = [
            f"# CF overnight backtest rollup — {DATE_TAG}",
            "",
            "**Layer:** VALIDATION (WR) / rules HYPOTHESIS  ",
            "**Gate:** NO_PROMOTE · PAPER FOUNDER_PAPER_ACCEPT when robust WR>50% · n≥20  ",
            "**Outlier:** drop top/bottom 5% trade PnL  ",
            "**Unit:** INDEX points proxy — not option premium",
            "",
            "## Families tested",
            "",
            ", ".join(f"`{f}`" for f in report["families_tested"]),
            "",
            f"- Structure cells scored: **{report['cells']}**",
            f"- Structure accepted: **{report['accepted_structure']}**",
            f"- Okala accepted (prior grid): **{report['accepted_okala']}**",
            f"- Skips (no India alt): **{len(skips)}**",
            f"- Elapsed: {report['elapsed_s']}s",
            "",
            "### Bar meta (sample)",
            "",
            "| Series | Bars | Lookback y |",
            "|--------|------|------------|",
        ]
        for k in sorted(bar_meta):
            m = bar_meta[k]
            md.append(f"| {k} | {m['n_bars']} | {m['lookback_years']} |")
        md += [
            "",
            "## Accepted structure cells (top 40)",
            "",
            "| Cell | n | WR robust | Mix |",
            "|------|---|-----------|-----|",
        ]
        for row in accepted[:40]:
            wr = row.get("wr_robust")
            wr_s = f"{100 * float(wr):.1f}%" if wr is not None else "—"
            md.append(
                f"| `{row['cell']}` | {row['n']} | {wr_s} | `{row['mix_id']}` |"
            )
        if not accepted:
            md.append("| *(none)* | | | |")
        md += [
            "",
            "## Okala accepted (from prior BT)",
            "",
            "| Cell | n | WR robust | Mix |",
            "|------|---|-----------|-----|",
        ]
        for row in okala_accepted[:20]:
            wr = row.get("wr_robust")
            wr_s = f"{100 * float(wr):.1f}%" if wr is not None else "—"
            md.append(
                f"| `{row.get('cell')}` | {row.get('n')} | {wr_s} | `{row.get('mix_id')}` |"
            )
        md += [
            "",
            "## Skips",
            "",
            f"See [`CF_OVERNIGHT_SKIPS_{DATE_TAG}.md`](CF_OVERNIGHT_SKIPS_{DATE_TAG}.md).",
            "",
            "## Honesty",
            "",
            "```text",
            "promote: false",
            "NO_PROMOTE: true",
            "RESEARCH_READY_FOR_PROGRAMMING: false",
            "fills: local OHLC cache only",
            "```",
            "",
            "## HANDOFF",
            "",
            "**Accepted:** Overnight structure grid + Okala rollup; FOUNDER_PAPER_ACCEPT "
            "cells for paper CE/PE wire only.  ",
            "**Rejected:** Live promote; inventing option fills; catalog win_rate writes.  ",
            "**UNKNOWN / DI:** OF absorb, Usman OI/gamma, London/NY ADR clocks, news-align.",
            "",
        ]
        md_path.write_text("\n".join(md), encoding="utf-8")
        _log(f"wrote {md_path}")

    return report


if __name__ == "__main__":
    run_cf_overnight()

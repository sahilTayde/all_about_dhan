"""Book-learning CREATE/TUNE on recon cache. Paper only. NO_PROMOTE."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence

from desk_ml.fit import fit_underlying, score_last
from desk_ml.inventory import IST, inventory_recon, ts_to_ist_date, window_bounds
from desk_ml.mrr import MRR_WINDOWS, mrr_fit_underlying
from desk_ml.persist import repo_root
from desk_ml.tape import load_triples

ML001_SEED = 14
UNDERLYINGS = ("NIFTY", "SENSEX")


def _public_ml001(report: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "ok",
        "status",
        "underlying",
        "n_rows",
        "n_feature_rows",
        "cluster_sizes",
        "centroids_orig",
        "supervised",
        "tape",
        "embargo",
        "win_rate",
        "verdict",
        "promote",
        "production_params_written",
        "session_note",
        "path",
        "note",
        "train_window",
        "seed",
        "k",
        "model_version",
    )
    return {k: report[k] for k in keys if k in report}


def run_book_tune(
    *,
    root: Optional[Path] = None,
    calendar_days: int = 21,
    underlyings: Sequence[str] = UNDERLYINGS,
    seed: int = ML001_SEED,
    windows: Sequence[int] = MRR_WINDOWS,
    persist: bool = True,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    base = root or repo_root()
    now, min_ts, max_ts = window_bounds(as_of=as_of, calendar_days=calendar_days)
    inv = inventory_recon(root=base, calendar_days=calendar_days, as_of=now, underlyings=tuple(underlyings))
    models: dict[str, Any] = {}
    for und in underlyings:
        full_triples, _ = load_triples(und, root=base)
        win_triples, win_meta = load_triples(und, root=base, min_ts=min_ts, max_ts=max_ts)
        week_missing = len(win_triples) == 0
        # Founder: OLD cache + last 1–3 weeks. If week join empty, still fit old cache and say so.
        fit_triples = list(full_triples)
        ml001 = fit_underlying(und, root=base, seed=seed, persist=persist, triples=fit_triples or None)
        scored = {"ok": False, "status": "SKIPPED"}
        if ml001.get("ok"):
            scored = score_last(und, root=base, triples=fit_triples or None)
        ml002 = mrr_fit_underlying(
            und,
            root=base,
            windows=windows,
            persist=persist,
            triples=fit_triples or None,
        )
        models[und] = {
            "week_tape_missing": week_missing,
            "week_join": win_meta,
            "fit_on": "old_cache_union" if fit_triples else "none",
            "fit_n_triples": len(fit_triples),
            "fit_span_ist": {
                "first": ts_to_ist_date(fit_triples[0].ts) if fit_triples else None,
                "last": ts_to_ist_date(fit_triples[-1].ts) if fit_triples else None,
            },
            "ml001_fit": _public_ml001(ml001),
            "ml001_score_last": {
                k: scored.get(k)
                for k in (
                    "ok",
                    "status",
                    "regime",
                    "overlay",
                    "reason_code",
                    "if_score",
                    "residual_z",
                    "premium_divergence",
                    "follow_gap",
                    "session_action",
                    "allow_new_paper_ce_pe",
                    "ts",
                    "promote",
                    "execution",
                )
                if k in scored
            },
            "ml002_mrr_fit": {
                k: ml002[k]
                for k in (
                    "ok",
                    "status",
                    "model_id",
                    "k_ce",
                    "k_pe",
                    "windows_tried",
                    "max_tweaks",
                    "tweaks",
                    "preferred",
                    "n_feature_rows",
                    "win_rate",
                    "verdict",
                    "promote",
                    "production_params_written",
                    "gate",
                    "path",
                    "note",
                    "tape",
                )
                if k in ml002
            },
        }

    day = now.date().isoformat()
    report = {
        "ok": True,
        "job": "BOOK_MODEL_TUNE",
        "as_of_ist": now.isoformat(timespec="seconds"),
        "calendar_days": calendar_days,
        "ml001_seed": seed,
        "mrr_windows": list(windows)[:3],
        "overlay": "FOLLOW-GAP",
        "inventory": inv,
        "models": models,
        "win_rate": None,
        "verdict": "NO_PROMOTE",
        "promote": False,
        "production_params_written": False,
        "gate": "BACKTEST_REQUIRED",
        "execution": "refused",
        "live_dhan": False,
        "super_order": False,
        "note": (
            "Cluster sizes and MRR/OU numbers describe this cache window. "
            "They are not a customer win rate and do not promote MIX/STRAT."
        ),
        "cli": {
            "inventory": "python -m desk_ml inventory --calendar-days 21",
            "ml001_fit": "python -m desk_ml fit --underlying NIFTY --seed 14",
            "ml001_score": "python -m desk_ml score --underlying NIFTY --source cache",
            "ml001_score_dual": "python -m desk_ml score --underlying NIFTY --source dual-tape",
            "ml002_score": "python -m desk_ml score --underlying NIFTY --model-id ML-002 --source dual-tape",
            "ml002_fit": "python -m desk_ml mrr-fit --underlying NIFTY",
            "book_tune": "python -m desk_ml book-tune --calendar-days 21",
        },
    }
    out_path = base / "data" / "recon" / f"BOOK_MODEL_TUNE_{day}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["path"] = str(out_path)
    return report

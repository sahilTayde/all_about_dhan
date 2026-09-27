"""Offline regime-shadow replay report: per day, how many boss decisions the adaptive weights / overlay
would flip, and the first-order P&L effect on the static replay's trades. Paper only, no broker.

    # recorded dual-tape days (local only)
    python scripts/regime_shadow_report.py --since 2026-09-17 --until 2026-09-25 --underlyings NIFTY
    # committed synthetic fixture, or N synthetic sessions (not market data)
    python scripts/regime_shadow_report.py --fixture packages/desk-ml/tests/fixtures/synthetic_session_nifty.json
    python scripts/regime_shadow_report.py --synthetic 5 --check-identical

Weights carry across days in date order (each day starts from the previous day's state).
`--check-identical` also replays each day with the regime hook forced off and requires the two
boards to be byte-identical after dropping wall-clock fields (exit 1 otherwise).
`--save-state` writes the final weight state atomically (the only writer of that file).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

from desk_ml.regime.shadow import RegimeShadow, jsonl_sink, load_config, use_runner
from desk_ml.regime.weights import WeightState

VOLATILE_KEYS = frozenset({"as_of_ist", "last_run_ist", "max_ts", "latency_p99_ms"})


def _strip(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if k not in VOLATILE_KEYS}
    if isinstance(x, list):
        return [_strip(v) for v in x]
    return x


def board_fingerprint(board: dict[str, Any]) -> str:
    """sha256 of the board as canonical JSON, wall-clock fields removed."""
    blob = json.dumps(_strip(board), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@contextmanager
def _fixture_patches(lot_size: int) -> Iterator[None]:
    """Synthetic sessions must not read repo prior-day closes or lot files."""
    import desk_ml.paper_scalp as ps

    saved = ps.load_index_closes, ps.resolve_lot_size
    ps.load_index_closes = lambda u, root=None: {}
    ps.resolve_lot_size = lambda und, root=None: (int(lot_size), "fixture")
    try:
        yield
    finally:
        ps.load_index_closes, ps.resolve_lot_size = saved


def run_report(
    days: Sequence[tuple[str, dict[str, Any]]],
    runner: RegimeShadow,
    *,
    check_identical: bool = False,
) -> dict[str, Any]:
    """`days` = [(day, replay_paper_scalp kwargs)] in date order. `write` is forced off."""
    from desk_ml.paper_scalp import replay_paper_scalp

    out: dict[str, Any] = {"days": [], "identical": {}, "ok": True}
    for day, kw in days:
        kw = {**kw, "write": False}
        with use_runner(runner):
            board = replay_paper_scalp(**kw)
        runner.finalize()
        closed = board.get("closed_trades") or []
        for und in kw.get("underlyings") or ("NIFTY",):
            out["days"].append(runner.day_report(day, str(und).upper(), closed))
        if check_identical:
            with use_runner(False):
                plain = replay_paper_scalp(**kw)
            a, b = board_fingerprint(plain), board_fingerprint(board)
            out["identical"][day] = {"ok": a == b, "off": a, "shadow": b}
            out["ok"] = out["ok"] and a == b
    tot = {"trades_static": 0, "net_static_inr": 0.0, "pnl_effect_known_inr": 0.0, "flips_actionable": 0,
           "unpriced_new_tickets": 0, "trades_flipped": 0}
    for r in out["days"]:
        tot["trades_static"] += r["trades_static"]
        tot["net_static_inr"] = round(tot["net_static_inr"] + r["net_static_inr"], 2)
        tot["pnl_effect_known_inr"] = round(tot["pnl_effect_known_inr"] + r["pnl_effect_known_inr"], 2)
        tot["flips_actionable"] += sum(r["flips_actionable"].values())
        tot["unpriced_new_tickets"] += r["unpriced_new_tickets"]
        tot["trades_flipped"] += r["trades_flipped"]
    tot["net_hypothetical_known_inr"] = round(tot["net_static_inr"] + tot["pnl_effect_known_inr"], 2)
    out["total"] = tot
    return out


def synthetic_days(n: int, start: str = "2026-09-14") -> list[str]:
    d, out = date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _print(rep: dict[str, Any]) -> None:
    for r in rep["days"]:
        fa = r["flips_actionable"]
        print(
            f"{r['day']} {r['underlying']}: static {r['trades_static']} trades {r['net_static_inr']:+,.2f} | "
            f"decisions {r['decisions']} flips {sum(r['flips'].values())} actionable {sum(fa.values())} "
            f"(suppress {fa['suppress']} new {fa['new']} reverse {fa['reverse']}) overlay_veto {r['overlay_vetoes']} | "
            f"trades flipped {r['trades_flipped']} resized {r['trades_resized']} known effect "
            f"{r['pnl_effect_known_inr']:+,.2f} -> {r['net_hypothetical_known_inr']:+,.2f} | "
            f"unpriced {r['unpriced_new_tickets']} (proxy {r['unpriced_proxy_index_points']:+.1f} idx pts) | "
            f"minutes {r['minutes_by_primary']} intermarket {r['intermarket']} | "
            f"outcomes {r['outcomes_applied']} weights v{r['weights_version']}"
        )
    for day, chk in rep["identical"].items():
        print(f"{day}: {'IDENTICAL' if chk['ok'] else 'DIFFERENT'} off {chk['off'][:12]} shadow {chk['shadow'][:12]}")
    t = rep["total"]
    print(
        f"TOTAL static {t['trades_static']} trades {t['net_static_inr']:+,.2f} | actionable flips {t['flips_actionable']} "
        f"| trades flipped {t['trades_flipped']} known effect {t['pnl_effect_known_inr']:+,.2f} -> "
        f"{t['net_hypothetical_known_inr']:+,.2f} | unpriced {t['unpriced_new_tickets']}"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="regime_shadow_report", description=__doc__.split("\n\n")[0])
    ap.add_argument("--fixture", type=Path, help="synthetic fixture JSON (desk_ml.event_parity format)")
    ap.add_argument("--synthetic", type=int, default=0, metavar="N", help="N generated synthetic sessions")
    ap.add_argument("--root", type=Path, help="repo root with data/recon (default: this checkout)")
    ap.add_argument("--since", default="2026-09-17")
    ap.add_argument("--until", default="2026-09-25")
    ap.add_argument("--days", nargs="*", help="explicit IST dates (overrides --since/--until)")
    ap.add_argument("--underlyings", nargs="*", default=["NIFTY"])
    ap.add_argument("--source", default="dual-tape")
    ap.add_argument("--no-live-session", action="store_true", help="historical replay instead of live-session params")
    ap.add_argument("--kw", action="append", default=[], metavar="KEY=JSON", help="extra replay_paper_scalp kwarg")
    ap.add_argument("--config", type=Path, help="regime config (default config/regime.yaml)")
    ap.add_argument("--fresh-state", action="store_true", help="start from empty weights instead of the saved state")
    ap.add_argument("--save-state", action="store_true", help="write the final weight state (atomic, versioned)")
    ap.add_argument("--log-jsonl", type=Path, help="append REGIME_LABEL / BOSS_SHADOW records here")
    ap.add_argument("--check-identical", action="store_true", help="also replay with the hook off; boards must match")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)

    from desk_ml.event_parity import _kw, fixture_replay_kwargs, load_fixture, synthetic_triples
    from desk_ml.persist import repo_root

    root = args.root or repo_root()
    cfg = load_config(root, args.config)
    sp = Path(cfg.weights.state_path)
    state_path = sp if sp.is_absolute() else root / sp
    state = WeightState(cfg.weights) if args.fresh_state else WeightState.load(state_path, cfg.weights)
    runner = RegimeShadow(cfg, root=root, state=state, sink=jsonl_sink(args.log_jsonl) if args.log_jsonl else None)

    with tempfile.TemporaryDirectory() as tmp:
        if args.fixture or args.synthetic:
            fixtures = [load_fixture(args.fixture)] if args.fixture else [
                {"underlying": "NIFTY", "session_ist_date": d, "lot_size": 65,
                 "triples": synthetic_triples(day=d, seed=100 + n)}
                for n, d in enumerate(synthetic_days(args.synthetic))
            ]
            days = [(fx["session_ist_date"], fixture_replay_kwargs(fx, Path(tmp))) for fx in fixtures]
            with _fixture_patches(int(fixtures[0]["lot_size"])):
                rep = run_report(days, runner, check_identical=args.check_identical)
        else:
            from desk_ml.paper_scalp import list_fix_first_days

            names = args.days or [d for d in list_fix_first_days(root=root, since=args.since) if d <= args.until]
            if not names:
                print(f"no dual-tape days in {root}/data/recon/paper_watch/DUAL-TAPE for {args.since}..{args.until}")
                return 1
            days = [(d, dict(root=root, underlyings=tuple(args.underlyings), source=args.source,
                             live_session=not args.no_live_session, session_ist_date=d, **_kw(args.kw)))
                    for d in names]
            rep = run_report(days, runner, check_identical=args.check_identical)

    _print(rep)
    if args.save_state:
        print(f"weights state v{runner.state.save(state_path)} -> {state_path}")
    if args.json:
        print(json.dumps(rep, indent=2, default=str))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

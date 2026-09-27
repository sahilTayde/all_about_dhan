"""Mutation check for the backtest gate: move each exit constant by a small step, the gate must fail.

    python tools/backtest_gate/mutate.py check             # every mutant must be caught (exit 1 if not)
    python tools/backtest_gate/mutate.py check --only EXIT_BOOK_NEAR_FRAC
    python tools/backtest_gate/mutate.py search --n 16     # design: which candidate days catch which mutants

A mutant is a real source edit of `desk_ml/paper_scalp.py` (`NAME = <new value>`), applied by an
import hook in a fresh subprocess, so values derived at import time (DEFAULT_PAPER_PARAMS,
UNFILLED_SECONDS, ...) follow exactly as they would after a developer's edit. Per-index point
profiles are dict entries read at call time; those are changed right after the module executes.
Nothing is written to the checkout. Paper only; no broker is called.
"""

from __future__ import annotations

import argparse
import importlib.abc
import importlib.util
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional, Sequence

HERE = Path(__file__).resolve().parent
TARGET = "desk_ml.paper_scalp"

# Every exit-side constant (booking overlay, stall, time exits, stop/target sizing, trail, target
# steps, give-up, unfilled cancel, flatten) with one small realistic step.
EXIT_MUTANTS: dict[str, str] = {
    "EXIT_BOOK_NEAR_FRAC": "0.60",
    "EXIT_NO_PROG_BARS": "4",
    "EXIT_NO_PROG_MFE": "2.5",
    "STALL_MIN_SEC": "15 * 60",
    "STALL_HIGH_STALE_SEC": "6 * 60",
    "STALL_MIN_SEC_CHOP": "6 * 60",
    "STALL_HIGH_STALE_CHOP": "2 * 60",
    "STALL_ER_MAX": "0.22",
    "STALL_TREND_ER": "0.30",
    "STALL_TARGET_PROGRESS": "0.45",
    "STALL_CHOP_PROGRESS": "0.30",
    "STALL_LOOKBACK": "10",
    "TIME_HARD_SEC": "35 * 60",
    "SCALP_HOLD_BARS": "6",
    "FLATTEN_MINUTES_IST": "15 * 60 + 10",
    "STOP_FRAC": "0.35",
    "TARGET_FRAC": "0.50",
    "MAX_TARGET_R": "1.5",
    "MIN_STOP_PREMIUM": "6.0",
    "MIN_STOP_FRAC_ENTRY": "0.05",
    "GIVE_UP_FRAC": "0.10",
    "TRAIL_BAND_MIN": "3.0",
    "TRAIL_BAND_MAX": "10.0",
    "TARGET_STEP_MAX": "1",
    "T1_CONFIRM_SECONDS": "120",
    "FILL_AWAY_FRAC": "0.025",
    "UNFILLED_BARS": "3",
    "OVERLAY_CANCEL_COOLDOWN_SEC": "10 * 60",
    "PREMIUM_PRINT_CAP": "18",
}
PROFILE_STEPS = {
    "NIFTY": {"atr_stop_k": 1.0, "min_stop": 5.0, "max_stop": 15.0, "trail_k": 0.75, "trail_min": 3.0,
              "trail_max": 8.0, "rr_continue": 2.2, "rr_trend": 1.8, "rr_sr": 1.1, "rr_base": 1.3,
              "chop_target_cap": 8.0},
    "SENSEX": {"atr_stop_k": 1.5, "min_stop": 15.0, "max_stop": 36.0, "trail_k": 1.25, "trail_min": 10.0,
               "trail_max": 24.0, "rr_continue": 2.0, "rr_trend": 1.6, "rr_sr": 1.05, "rr_base": 1.25},
}
for _und, _steps in PROFILE_STEPS.items():
    for _k, _v in _steps.items():
        EXIT_MUTANTS[f"INDEX_POINT_PROFILES.{_und}.{_k}"] = repr(_v)

# Constants that cannot move any result in a replay, with the reason. Checked like the others:
# if one of these ever starts moving results, `check` reports it so the entry can be removed.
UNEXERCISABLE: dict[str, str] = {
    "SCALP_HOLD_BARS": (
        "Dead branch: _exit_reason only uses hold_bars when `not can_stall`, and can_stall is "
        "`seen_high_ts is not None`, which the first mark of every filled ticket sets. Only TIME_HARD_SEC "
        "ends a trade on time."
    ),
    "PREMIUM_PRINT_CAP": (
        "Only stall_book_reason reads premium_prints, and only the last STALL_LOOKBACK (15) of them, so any "
        "cap >= 15 (24 -> 18 here) gives identical exits. A cap below 15 would matter."
    ),
    "MIN_STOP_PREMIUM": (
        "Only the legacy stop floor for an index without INDEX_POINT_PROFILES (BANKNIFTY) reads it, as "
        "max(MIN_STOP_PREMIUM, entry * MIN_STOP_FRAC_ENTRY). The SOD product trades ITM only (ATM tapes are "
        "skipped as ITM_ONLY_NO_QUOTE) and a BANKNIFTY ITM premium is at least the 300-point depth, so "
        "entry * 0.06 >= 18 always beats 8 (or 6)."
    ),
    "INDEX_POINT_PROFILES.NIFTY.min_stop": (
        "Every use (risk floor, the flat-path ATR fallback min_stop * 0.5) is then floored by floor_path_stop at "
        "entry * MIN_STOP_FRAC_ENTRY; an ITM NIFTY premium is >= 200, so that floor is >= 12 > 6 (or 5)."
    ),
    "OVERLAY_CANCEL_COOLDOWN_SEC": (
        "should_overlay_cancel_cooldown needs index_path_is_chop(), but PATH_KIND_HOLD tests the identical "
        "predicate (should_index_path_kind_hold == index_path_is_chop) one step earlier and returns while "
        "skip_sideways is on. Replays always use DEFAULT_PAPER_PARAMS (skip_sideways=True); only a live session "
        "params file can turn it off."
    ),
    "FILL_AWAY_FRAC": (
        "Only _unfilled_reason (working buy limits) reads it. A SOD ticket is a working limit only when "
        "paper_impulse_fill() is false, but the strength gates admit only a last-3 impulse (pause_continue also "
        "sets last3_impulse) or an ITM-bin confirm (a SHORT_COVER vote comes with the same wing's PREMIUM_UP, "
        "reaching BIN_MIN_VOTES), both impulse fills. 0 working limits in ~150 synthetic days incl. OI chains."
    ),
    "UNFILLED_BARS": "Same as FILL_AWAY_FRAC: it only sets the working-limit timeout (UNFILLED_SECONDS).",
}

# Live paths that no synthetic day reached yet (searched ~150 designed days: regime walks, quiet/chop legs,
# wicks, OI chain cells, scripted trend-pause-resume and trend-then-chop legs, volatile BANKNIFTY).
# Not claimed impossible: the mutation test reports them as xfail until a fixture day is added.
NOT_REACHED: dict[str, str] = {
    "STALL_HIGH_STALE_SEC": (
        "Non-chop stall needs INDEX ER >= 0.35 with a last-3 pullback, price above entry but below the high, "
        "premium ER <= 0.18 over 15 prints, age >= 20 min and the high stale 6-8 min, with no CANCEL_AGAINST first."
    ),
    "STALL_HIGH_STALE_CHOP": (
        "Chop stalls in the fixtures always fire via at_failed_high / chop_near before the 2-3 min stale test differs."
    ),
    "TRAIL_BAND_MIN": (
        "Legacy trail band (BANKNIFTY, target_shift) drops below 4 only with a volume drop <= 0.7x plus a "
        "LONG_UNWIND vote on the traded wing at the T1 lock."
    ),
    "INDEX_POINT_PROFILES.NIFTY.rr_continue": (
        "Binds only for a pause_continue entry with vol_expand and risk * rr < 1.618 * typical premium range, "
        "not chop-capped and not feasibility-clipped."
    ),
    "INDEX_POINT_PROFILES.SENSEX.rr_continue": "Same conditions as the NIFTY rr_continue entry.",
}


class SourcePatch(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Load `desk_ml.paper_scalp` from its own file with one constant edited."""

    def __init__(self, name: str, value: str) -> None:
        self.name, self.value = name, value

    def find_spec(self, fullname: str, path: Any = None, target: Any = None):  # noqa: D401
        if fullname != TARGET or not path:
            return None
        origin = str(Path(list(path)[0]) / "paper_scalp.py")
        return importlib.util.spec_from_file_location(fullname, origin, loader=self)

    def create_module(self, spec):  # default module creation
        return None

    def exec_module(self, module) -> None:
        text = Path(module.__file__).read_text(encoding="utf-8")
        if "." in self.name:
            code = compile(text, module.__file__, "exec")
            exec(code, module.__dict__)
            table, und, key = self.name.split(".")
            if key not in getattr(module, table)[und]:
                raise KeyError(f"{self.name} not found")
            getattr(module, table)[und][key] = float(self.value)
            return
        new, n = re.subn(rf"^{re.escape(self.name)}(\s*:[^=]+)?\s*=.*$", f"{self.name} = {self.value}", text, flags=re.M)
        if n != 1:
            raise ValueError(f"{self.name}: expected one top-level assignment, found {n}")
        exec(compile(new, module.__file__, "exec"), module.__dict__)


# ------------------------------------------------------------------ worker (one mutant per process)


def _worker(args: argparse.Namespace) -> int:
    if args.mutant:
        name, _, value = args.mutant.partition("=")
        sys.meta_path.insert(0, SourcePatch(name, value))
    sys.path.insert(0, str(HERE))
    import gate

    if args.mode == "search":
        out = {}
        variants = (("", {}),) if args.no_shift else (("", {}), ("+shift", {"apply_target_shift": True}))
        for p in args.fixtures:
            for tag, kw in variants:
                r = gate.replay_fixture(Path(p), event_path=False, replay_kw=kw)
                out[Path(p).stem + tag] = {"n": r["n_trades"], "net": r["net_pnl_inr"], "sha": r["trades_sha256"]}
        print(json.dumps(out))
        return 0
    expected = json.loads(gate.EXPECTED.read_text(encoding="utf-8"))["fixtures"]
    combos = list(expected)
    if args.first:
        combos.sort(key=lambda k: 0 if k.split("/")[0] in args.first else 1)
    for key in combos:
        stem, profile = key.split("/")
        path = next(p for p in gate.fixture_paths() if p.stem == stem)
        actual = gate.replay_profile(path, profile)
        if gate.diff(expected[key], actual):
            print(json.dumps({"caught": key}))
            return 1
    print(json.dumps({"caught": None}))
    return 0


def _spawn(argv: list[str], timeout: float = 900) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    return subprocess.run([sys.executable, str(Path(__file__).resolve()), *argv], capture_output=True, text=True,
                          timeout=timeout, env=env)


def _last_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"no JSON in worker output: {stdout[-400:]}")


# ------------------------------------------------------------------ check


def check(names: Sequence[str], jobs: int = 4) -> dict[str, dict[str, Any]]:
    """name -> {"caught": combo or None, "error": ...}. Uses the committed expected results."""
    hints = json.loads((HERE / "fixtures" / "recipes.json").read_text(encoding="utf-8")).get("catches", {})

    def one(name: str) -> tuple[str, dict[str, Any]]:
        argv = ["worker", "--mode", "gate", "--mutant", f"{name}={EXIT_MUTANTS[name]}"]
        if hints.get(name):
            argv += ["--first", *hints[name]]
        proc = _spawn(argv)
        try:
            return name, _last_json(proc.stdout)
        except ValueError:
            return name, {"caught": None, "error": (proc.stderr or proc.stdout)[-600:]}

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return dict(pool.map(one, names))


# ------------------------------------------------------------------ search (fixture design)


def candidate_recipes(n: int, start: int) -> list[dict[str, Any]]:
    import random

    days = ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17",
            "2026-09-18", "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24"]
    out = []
    for i in range(start, start + n):
        rng = random.Random(1000 + i)
        und = ("NIFTY", "SENSEX", "NIFTY", "SENSEX", "BANKNIFTY")[i % 5]
        r: dict[str, Any] = {"id": f"cand_{i:03d}_{und.lower()}", "underlying": und, "day": days[i % len(days)],
                             "seed": 100 + i, "p_switch": round(rng.choice([0.004, 0.008, 0.012, 0.02, 0.03]), 3),
                             "drift": round(rng.uniform(0.4, 2.0), 2), "noise": round(rng.uniform(1.5, 5.0), 2),
                             "revert": round(rng.uniform(0.01, 0.12), 3), "tv_open": round(rng.uniform(45, 80), 1),
                             "tv_close": round(rng.uniform(15, 40), 1)}
        if i >= 100:  # round 2: shapes the plain regime walk rarely makes
            r.update({
                "noise": round(rng.choice([rng.uniform(0.5, 1.5), rng.uniform(1.5, 5.0)]), 2),
                "quiet": round(rng.uniform(0.06, 0.4), 3),
                "wick": round(rng.choice([0.0, rng.uniform(0.5, 3.0)]), 2),
                "vol_trend": round(rng.uniform(0, 1500)),
                "vol_spike": round(rng.choice([0.0, rng.uniform(0.01, 0.06)]), 3),
                "weights": [rng.choice([1, 2, 3]) for _ in range(4)],
            })
        if i >= 200:  # round 3: chain cells with OI (cover / unwind votes) and a wider volatility range
            r.update({"wings": rng.random() < 0.8, "oi_cover": round(rng.uniform(-1.0, 1.0), 2),
                      "noise": round(rng.choice([rng.uniform(0.8, 2.0), rng.uniform(2.0, 5.0), rng.uniform(5.0, 9.0)]), 2),
                      "wick": round(rng.uniform(0.5, 3.0), 2)})
        out.append(r)
    return out


def search(n: int, start: int, jobs: int, names: Sequence[str], extra: Sequence[Path],
           recipes: Optional[list[dict[str, Any]]] = None, no_shift: bool = False) -> dict[str, Any]:
    import synth

    recipes = candidate_recipes(n, start) if recipes is None else recipes
    paths = [*extra, *(synth.fixture_path(r) for r in recipes)]
    fx = [str(p) for p in paths]

    def one(mutant: Optional[str]) -> tuple[Optional[str], dict[str, Any]]:
        argv = ["worker", "--mode", "search", "--fixtures", *fx, *(["--no-shift"] if no_shift else [])]
        if mutant:
            argv += ["--mutant", f"{mutant}={EXIT_MUTANTS[mutant]}"]
        proc = _spawn(argv, timeout=3600)
        try:
            return mutant, _last_json(proc.stdout)
        except ValueError as exc:
            raise RuntimeError(f"worker {mutant or 'baseline'} failed: {proc.stderr[-800:]}") from exc

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = dict(pool.map(one, [None, *names]))
    base = results.pop(None)
    catches = {m: [stem for stem, fp in res.items() if fp != base[stem]] for m, res in results.items()}
    return {"recipes": {r["id"]: r for r in recipes}, "baseline": base, "catches": catches}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="tools/backtest_gate/mutate.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("worker")
    w.add_argument("--mode", choices=("gate", "search"), required=True)
    w.add_argument("--mutant")
    w.add_argument("--fixtures", nargs="*", default=[])
    w.add_argument("--first", nargs="*", default=[])
    w.add_argument("--no-shift", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--only", nargs="*")
    c.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    s = sub.add_parser("search")
    s.add_argument("--n", type=int, default=12)
    s.add_argument("--start", type=int, default=0)
    s.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    s.add_argument("--only", nargs="*")
    s.add_argument("--extra", nargs="*", default=[], type=Path, help="existing fixture files to include")
    s.add_argument("--out", type=Path)
    s.add_argument("--recipes", type=Path, help="search these recipes (JSON list or {recipes: [...]}) instead")
    s.add_argument("--no-shift", action="store_true", help="default profile only (skip the target-shift replay)")
    args = ap.parse_args(argv)

    if args.cmd == "worker":
        return _worker(args)
    names = list(args.only or EXIT_MUTANTS)
    if args.cmd == "search":
        given = None
        if args.recipes:
            blob = json.loads(args.recipes.read_text(encoding="utf-8"))
            given = blob["recipes"] if isinstance(blob, dict) else blob
        res = search(args.n, args.start, args.jobs, names, args.extra, recipes=given, no_shift=args.no_shift)
        if args.out:
            args.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
        for m, stems in res["catches"].items():
            print(f"{m:45s} {len(stems):3d}  {' '.join(stems[:6])}")
        return 0
    res = check(names, jobs=args.jobs)
    missed = []
    for name in names:
        r = res[name]
        caught = r.get("caught")
        if caught:
            tag = "CAUGHT"
        else:
            tag = "UNEXERCISABLE" if name in UNEXERCISABLE else "NOT-REACHED" if name in NOT_REACHED else "MISSED"
        print(f"{tag:13s} {name} = {EXIT_MUTANTS[name]:10s} {caught or r.get('error', '')[:200]}")
        if not caught and name not in UNEXERCISABLE and name not in NOT_REACHED:
            missed.append(name)
        if caught and name in UNEXERCISABLE:
            missed.append(name)
    print(f"{len(names) - len(missed)}/{len(names)} mutants behave as documented")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())

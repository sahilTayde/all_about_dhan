"""Synthetic session generator for the backtest gate. NOT market data.

A day is a regime-switching random walk on the index (trend up / trend down / chop / quiet),
with ATM and deep-ITM premiums from intrinsic value plus a decaying time value, optional intrabar
lows, and optional chain cells (premium, low, volume, OI per strike). Each recipe in
`fixtures/recipes.json` is fully determined by its seed and knobs. The days are not committed (with
chain cells they are large); the gate generates them into a temp cache:

    python tools/backtest_gate/synth.py                  # print the cached path of every recipe day
    python tools/backtest_gate/synth.py --write out/     # copy them somewhere to look at

Deterministic for a given CPython on a given libm (random.gauss uses log/cos); CI and the recorded
expected results both use Ubuntu + glibc.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RECIPES = HERE / "fixtures" / "recipes.json"
IST = timezone(timedelta(hours=5, minutes=30))
FIELDS = (
    "ts",
    "idx_close",
    "ce_close",
    "pe_close",
    "atm_strike",
    "itm_ce_close",
    "itm_pe_close",
    "itm_ce_strike",
    "itm_pe_strike",
    "idx_volume",
    "premium_kind",
)
# base level, points per unit of noise, strike step, ITM depth, lot size
SHAPE = {
    "NIFTY": (25000.0, 1.0, 50, 200, 65),
    "BANKNIFTY": (55000.0, 2.2, 100, 300, 35),
    "SENSEX": (80000.0, 3.2, 100, 300, 20),
}
REGIMES = ("up", "down", "chop", "quiet")


def generate(recipe: dict[str, Any]) -> dict[str, Any]:
    """Knobs (all optional except id/underlying/day/seed):

    p_switch  chance per step of a regime change     weights   relative odds of up/down/chop/quiet
    drift     trend points per step (x shape scale)  noise     step noise (x shape scale)
    revert    pull back to the regime's anchor       quiet     noise multiplier in the quiet regime
    wick      mean intrabar low below the close      vol_trend extra index volume while trending
    vol_spike chance per step of a volume spike      tv_open / tv_close  time value at open / close
    premium   "ITM" (ITM + ATM legs) or "ATM" (ATM legs only, no ITM columns)
    wings     add chain cells (strikes ATM +/- WING_STEPS); oi_cover ties OI moves to premium moves
    script    repeating legs [[minutes, regime, drift?, noise?], ...] instead of random switching
    """
    und = recipe["underlying"]
    base, k, step, itm, lot = SHAPE[und]
    rng = random.Random(int(recipe["seed"]))
    step_s = int(recipe.get("step_s", 20))
    p_switch = float(recipe.get("p_switch", 0.01))
    drift = float(recipe.get("drift", 1.0))
    noise = float(recipe.get("noise", 3.0))
    revert = float(recipe.get("revert", 0.05))
    quiet = float(recipe.get("quiet", 0.35))
    wick = float(recipe.get("wick", 0.0))
    vol_trend = float(recipe.get("vol_trend", 400.0))
    vol_spike = float(recipe.get("vol_spike", 0.0))
    weights = [float(w) for w in recipe.get("weights", (1, 1, 1, 1))]
    kind = str(recipe.get("premium", "ITM")).upper()
    tv_open, tv_close = (
        float(recipe.get("tv_open", 60.0)),
        float(recipe.get("tv_close", 30.0)),
    )
    y, m, d = (int(p) for p in recipe["day"].split("-"))
    t0 = int(datetime(y, m, d, 9, 15, tzinfo=IST).timestamp())
    t1 = int(datetime(y, m, d, 15, 30, tzinfo=IST).timestamp())
    wings = bool(recipe.get("wings", False))
    oi_cover = float(recipe.get("oi_cover", 0.0))
    fields = list(FIELDS) + (
        ["ce_low", "pe_low", "itm_ce_low", "itm_pe_low"] if wick > 0 else []
    )
    fields += ["wing_quotes"] if wings else []
    oi_book: dict[tuple[float, str], float] = {}
    prev_px: dict[tuple[float, str], float] = {}
    # script: repeating legs [[minutes, regime, drift?, noise?], ...] instead of random regime switches
    script = [
        (int(leg[0]), str(leg[1]), *(float(x) for x in leg[2:4]))
        for leg in recipe.get("script") or []
    ]
    legs: list[tuple[int, str, float, float]] = []
    if script:
        t = t0
        while t <= t1:
            for leg in script:
                legs.append(
                    (
                        t + leg[0] * 60,  # type: ignore[arg-type,operator]
                        leg[1],  # type: ignore[arg-type]
                        leg[2] if len(leg) > 2 else drift,  # type: ignore[operator]
                        leg[3] if len(leg) > 3 else noise,  # type: ignore[operator]
                    )
                )
                t += leg[0] * 60  # type: ignore[operator]
    idx, regime, anchor, rows = base, rng.choices(REGIMES, weights)[0], base, []
    leg_i, d_now, n_now = 0, drift, noise
    for ts in range(t0, t1 + 1, step_s):
        if legs:
            while ts >= legs[leg_i][0]:
                leg_i += 1
            if legs[leg_i][1] != regime:
                anchor = idx
            regime, d_now, n_now = legs[leg_i][1], legs[leg_i][2], legs[leg_i][3]
        elif rng.random() < p_switch:
            regime, anchor = rng.choices(REGIMES, weights)[0], idx
        if regime == "up":
            move = d_now * k + rng.gauss(0, n_now * k)
        elif regime == "down":
            move = -d_now * k + rng.gauss(0, n_now * k)
        elif regime == "chop":
            move = revert * (anchor - idx) + rng.gauss(0, 1.3 * n_now * k)
        else:
            move = revert * (anchor - idx) + rng.gauss(0, quiet * n_now * k)
        idx += move
        frac = (ts - t0) / (t1 - t0)
        tv = tv_open + (tv_close - tv_open) * frac
        atm = round(idx / step) * step
        itm_tv = tv * 0.66
        ce, pe = (
            max(0.05, max(0.0, idx - atm) + tv),
            max(0.05, max(0.0, atm - idx) + tv),
        )
        ice, ipe = (
            max(0.0, idx - (atm - itm)) + itm_tv,
            max(0.0, (atm + itm) - idx) + itm_tv,
        )
        volume = (
            1000 + rng.randint(0, 500) + (vol_trend if regime in ("up", "down") else 0)
        )
        if vol_spike and rng.random() < vol_spike:
            volume *= 2.5
        row: list[Any] = [ts, round(idx, 2), round(ce, 2), round(pe, 2), float(atm)]
        if kind == "ATM":
            row += [None, None, None, None]
        else:
            row += [round(ice, 2), round(ipe, 2), float(atm - itm), float(atm + itm)]
        row += [float(volume), kind]
        if wick > 0:
            lows = [
                max(0.05, v - abs(rng.gauss(0, wick * k))) for v in (ce, pe, ice, ipe)
            ]
            row += [round(lows[0], 2), round(lows[1], 2)]
            row += (
                [None, None]
                if kind == "ATM"
                else [round(lows[2], 2), round(lows[3], 2)]
            )
        if wings:
            row.append(
                _wing_cells(
                    rng, idx, atm, step, itm, tv, oi_book, prev_px, oi_cover, k, wick
                )
            )
        if not all(math.isfinite(v) for v in row[1:4]):
            raise ValueError("non-finite synthetic price")
        rows.append(row)
    return {
        "note": f"Synthetic {und} session for the backtest gate ({recipe['id']}). Not market data.",
        "underlying": und,
        "session_ist_date": recipe["day"],
        "seed": int(recipe["seed"]),
        "lot_size": lot,
        "recipe": recipe,
        "fields": fields,
        "rows": rows,
    }


WING_STEPS = 4  # strikes each side of ATM; covers the ITM strike (NIFTY 200 = 4 x 50, SENSEX/BANKNIFTY 3 x 100)


def _tv_at(tv: float, strike: float, atm: float, itm: float) -> float:
    """Time value falls by x0.66 per ITM depth away from ATM (ATM = tv, the ITM column = 0.66 tv).
    Repeated multiplication, not pow(), so every platform rounds the same way."""
    steps = abs(strike - atm) / itm
    whole, part = int(steps), steps - int(steps)
    out = tv
    for _ in range(whole):
        out *= 0.66
    return out * (1.0 - 0.34 * part)


def _wing_cells(
    rng: random.Random,
    idx: float,
    atm: float,
    step: int,
    itm: int,
    tv: float,
    oi_book: dict[tuple[float, str], float],
    prev_px: dict[tuple[float, str], float],
    oi_cover: float,
    k: float,
    wick: float,
) -> dict[str, dict[str, float]]:
    """Chain cells around ATM: premium, low, volume, OI per leg. OI moves against premium when
    oi_cover > 0 (short covering / long unwinding) and with it when < 0 (fresh writing)."""
    cells: dict[str, dict[str, float]] = {}
    for n in range(-WING_STEPS, WING_STEPS + 1):
        strike = float(atm + n * step)
        tvk = _tv_at(tv, strike, atm, itm) if abs(strike - atm) != itm else tv * 0.66
        cell: dict[str, float] = {}
        for leg, intrinsic in (
            ("ce", max(0.0, idx - strike)),
            ("pe", max(0.0, strike - idx)),
        ):
            px = max(0.05, intrinsic + tvk)
            key = (strike, leg)
            chg = px - prev_px.get(key, px)
            prev_px[key] = px
            oi = oi_book.get(key, 400000.0 + rng.randint(0, 200000))
            direction = (chg > 0) - (chg < 0)
            oi = max(1000.0, oi + rng.gauss(0, 1500.0) - oi_cover * 4000.0 * direction)
            oi_book[key] = oi
            cell[leg] = round(px, 2)
            cell[f"{leg}_low"] = round(
                max(0.05, px - abs(rng.gauss(0, wick * k))) if wick > 0 else px, 2
            )
            cell[f"{leg}_volume"] = float(
                200 + rng.randint(0, 300) + int(abs(chg) * 150)
            )
            cell[f"{leg}_oi"] = float(round(oi))
        cells[str(int(strike))] = cell
    return cells


def dump(blob: dict[str, Any]) -> str:
    return json.dumps(blob, separators=(",", ":")) + "\n"


def cache_dir() -> Path:
    return Path(
        os.environ.get("BACKTEST_GATE_CACHE")
        or Path(tempfile.gettempdir()) / "backtest_gate_fixtures"
    )


def fixture_path(recipe: dict[str, Any]) -> Path:
    """Generated on demand into a temp cache (never the checkout), keyed by the recipe and this file."""
    key = hashlib.sha256(
        (
            json.dumps(recipe, sort_keys=True)
            + Path(__file__).read_text(encoding="utf-8")
        ).encode()
    ).hexdigest()[:12]
    path = cache_dir() / f"{recipe['id']}.{key}" / f"{recipe['id']}.json"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(dump(generate(recipe)), encoding="utf-8")
        os.replace(tmp, path)
    return path


def load_recipes() -> list[dict[str, Any]]:
    return json.loads(RECIPES.read_text(encoding="utf-8"))["recipes"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tools/backtest_gate/synth.py", description=__doc__.split("\n\n")[0]
    )
    ap.add_argument(
        "--write",
        type=Path,
        help="write every recipe day into this folder for inspection",
    )
    args = ap.parse_args(argv)
    for recipe in load_recipes():
        path = fixture_path(recipe)
        if args.write:
            args.write.mkdir(parents=True, exist_ok=True)
            (args.write / path.name).write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8"
            )
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

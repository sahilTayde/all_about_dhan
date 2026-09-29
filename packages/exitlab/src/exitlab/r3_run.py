"""One-command round-3 miner + walk-forward. Paper / replay only."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from exitlab.clock import IST, as_ist
from exitlab.costs import load_cost_rates
from exitlab.entries import entry_from_dict, history_random_entries, random_entries
from exitlab.fills import SlippageModel
from exitlab.harness import replay_trade
from exitlab.history import HistoryUnavailable, load_index_1m, load_option_week
from exitlab.plans import ExitPlanFn
from exitlab.r3_core import (
    FeatRow,
    Minute,
    clock_bucket,
    features_before,
    first30_regime,
    half_spread_pts,
    hist_minutes,
    labels_for,
    live_minutes,
    mfe_mae,
    minutes_to_series,
    oracle_best_net,
    shift_minutes,
)
from exitlab.r3_mine import (
    FEAT_NAMES,
    combo_pred,
    combo_table,
    fit_simple_models,
    matrix,
    saved_vs_hold,
    split_slices,
    univariate,
)
from exitlab.r3_ml import fit_boost, fit_logit, kmeans, nearest_center
from exitlab.r3_plans import (
    baselines,
    plan_atr_stop,
    plan_clock_window,
    plan_divergence,
    plan_ladder,
    plan_other_side,
    plan_pattern,
    plan_peak_model,
    plan_shape_exit,
    plan_theta_vs_move,
    plan_time_edge,
)
from exitlab.scenarios import group_index_by_session, is_weekend, nifty_weekly_expiry
from exitlab.stats import summarize
from exitlab.tapes import dual_tape_days, load_dual_tape_session
from exitlab.types import Entry, TradeResult


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _expiry(session: str) -> bool:
    d = datetime.fromisoformat(session).date()
    return nifty_weekly_expiry(d).isoformat() == session


def _tag_scenario(base: str, session: str) -> str:
    sc = base or "unknown"
    if _expiry(session) and "expiry" not in sc:
        return f"{sc}_expiry"
    return sc


def _proxy_exit_px(minutes: list[Minute], fire_i: int | None, half: float) -> float | None:
    if fire_i is not None and 0 <= fire_i < len(minutes):
        raw_px = minutes[fire_i].ltp
        if raw_px:
            return float(raw_px) - half
    last = next((m.ltp for m in reversed(minutes) if m.ltp), None)
    return None if last is None else float(last) - half


def _proxy_net(entry: Entry, minutes: list[Minute], fire_i: int | None, half: float) -> float:
    px = _proxy_exit_px(minutes, fire_i, half)
    if px is None:
        return 0.0
    return (px - entry.entry_price) * entry.qty


def _day_index_upto(sess_idx: list[tuple[datetime, float]], now: datetime) -> list[float]:
    cutoff = as_ist(now)
    return [px for ts, px in sess_idx if as_ist(ts) < cutoff]


def build_feat_rows(
    entries: list[Entry],
    paths: dict[str, list[Minute]],
    regime_of: dict[str, str],
    sess_idx: dict[str, list[tuple[datetime, float]]],
) -> list[FeatRow]:
    rows: list[FeatRow] = []
    for e in entries:
        mins = paths.get(e.entry_id) or []
        if len(mins) < 4:
            continue
        hs = half_spread_pts(e.moneyness)
        labs = labels_for(mins, half_spread=hs)
        expiry = _expiry(e.session) or "expiry" in e.scenario
        regime = regime_of.get(e.session) or e.scenario
        day_series = sess_idx.get(e.session) or []
        for i in range(1, len(mins)):
            now = mins[i - 1].available_ts
            day_idx = _day_index_upto(day_series, now)
            if not day_idx:
                day_idx = [float(m.index) for m in mins[:i] if m.index is not None]
            feat = features_before(
                mins, i, entry=e, day_index=day_idx, regime=regime, expiry=expiry
            )
            if not feat:
                continue
            rows.append(
                FeatRow(
                    entry_id=e.entry_id,
                    entry_set=e.entry_set,
                    session=e.session,
                    side=e.side,
                    i=i,
                    ts=as_ist(mins[i].available_ts).isoformat(),
                    label_5=labs["5"][i],
                    label_15=labs["15"][i],
                    label_30=labs["30"][i],
                    label_eod=labs["eod"][i],
                    feats=feat,
                )
            )
    return rows


def _combo_to_checks(spec: str, uni_by: dict[str, dict[str, Any]]) -> list[tuple[str, str, float]]:
    checks: list[tuple[str, str, float]] = []
    for part in spec.split("+")[:3]:
        name, direction = part.split(":")
        u = uni_by.get(name) or {}
        thr = u.get("q75") if direction == "high" else u.get("q25")
        if thr is None:
            continue
        checks.append((name, "ge" if direction == "high" else "le", float(thr)))
    return checks


def _replay(
    entries: list[Entry],
    paths: dict[str, list[Minute]],
    plan: ExitPlanFn,
    rates: dict[str, Any],
    seed: int,
    feat_at: dict[tuple[str, int], dict[str, float | None]],
) -> list[TradeResult]:
    """Quotes only (1 event / minute). Features from minutes strictly before clock.now."""
    out: list[TradeResult] = []
    for e in entries:
        mins = paths.get(e.entry_id) or []
        quotes, _bars = minutes_to_series(mins)
        model = SlippageModel(moneyness=e.moneyness)

        def _wrapped(
            state: Any,
            clock: Any,
            ctx: dict[str, Any],
            _eid: str = e.entry_id,
            _mins: list[Minute] = mins,
            _plan: ExitPlanFn = plan,
        ) -> str:
            i = 0
            now = as_ist(clock.now)
            for k, m in enumerate(_mins):
                if as_ist(m.available_ts) < now:
                    i = k + 1
                else:
                    break
            ctx = dict(ctx)
            ctx["r3_feat"] = feat_at.get((_eid, i), {})
            return _plan.decide(state, clock, ctx)

        wrap = ExitPlanFn(plan.spec, _wrapped)
        out.append(
            replay_trade(
                e,
                wrap,
                quotes=quotes,
                bars=(),
                slippage=model,
                cost_rates=rates,
                ctx_extra={"chop": "chop" in e.scenario, "regime": e.scenario},
                data_source="r3",
                seed=seed,
            )
        )
    return out


def _pack_trades(rows: list[TradeResult], n_variants: int, seed: int) -> dict[str, Any]:
    s = summarize(
        rows,
        plan_id=rows[0].plan_id if rows else "none",
        entry_set=rows[0].entry_set if rows else "none",
        scenario="ALL",
        split="wf",
        n_variants=n_variants,
        data_source="r3",
        seed=seed,
    )
    d = asdict(s)
    for key, pred in (
        ("CE", lambda r: r.side == "CE"),
        ("PE", lambda r: r.side == "PE"),
        ("trend", lambda r: "trend" in r.scenario),
        ("chop", lambda r: "chop" in r.scenario),
        ("expiry", lambda r: "expiry" in r.scenario),
        ("normal", lambda r: "expiry" not in r.scenario),
    ):
        sub = [r for r in rows if pred(r) and r.skipped is None]
        wins = [r.net_inr for r in sub if r.net_inr > 0]
        losses = [r.net_inr for r in sub if r.net_inr <= 0]
        d[f"slice_{key}"] = {
            "n": len(sub),
            "net_inr": round(sum(r.net_inr for r in sub), 2) if sub else 0.0,
            "win_rate": (len(wins) / len(sub)) if sub else None,
            "avg_win": (sum(wins) / len(wins)) if wins else None,
            "avg_loss": (sum(losses) / len(losses)) if losses else None,
        }
    return d


def _feat_map(rows: list[FeatRow]) -> dict[tuple[str, int], dict[str, float | None]]:
    return {(r.entry_id, r.i): r.feats for r in rows}


def _time_grid(
    entries: list[Entry],
    paths: dict[str, list[Minute]],
    n_range: range,
    xmults: tuple[float, ...],
) -> list[tuple[float, float, float]]:
    grid: list[tuple[float, float, float]] = []
    for n in n_range:
        for xmult in xmults:
            tot = 0.0
            for e in entries:
                mins = paths[e.entry_id]
                half = half_spread_pts(e.moneyness)
                x = xmult * (2.0 * half)
                fire = None
                if (
                    n < len(mins)
                    and mins[n].ltp is not None
                    and (float(mins[n].ltp or 0) - e.entry_price < x)
                ):
                    fire = n
                tot += _proxy_net(e, mins, fire, half)
            grid.append((float(n), x, tot))
    grid.sort(key=lambda t: -t[2])
    return grid


def _same_rule(rid: str, pid: str) -> bool:
    return rid == pid or (rid.startswith("time_edge") and pid.startswith("time_edge"))


def _index_from_ticks(ticks: list[dict[str, Any]]) -> list[tuple[datetime, float]]:
    by: dict[datetime, float] = {}
    for t in ticks:
        idx = t.get("index")
        if idx is None:
            continue
        key = as_ist(t["available_ts"]).replace(second=0, microsecond=0)
        by[key] = float(idx)
    return [(k, by[k]) for k in sorted(by)]


def run_round3(
    *,
    data: Path,
    out: Path,
    seed: int = 7,
    reuse_entries: Path | None = None,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    rates = load_cost_rates()
    variants: list[str] = []

    ticks_cache = {p.stem: load_dual_tape_session(p) for p in dual_tape_days(data)}
    live: list[Entry] = []
    if reuse_entries and reuse_entries.is_file():
        loaded = json.loads(reuse_entries.read_text(encoding="utf-8"))
        live = [
            entry_from_dict(x)
            for x in loaded
            if x.get("entry_set") in {"legacy", "v2_boss", "random"}
        ]
    if not any(e.entry_set == "random" for e in live):
        for sess, ticks in ticks_cache.items():
            if is_weekend(sess) or not ticks:
                continue
            live.extend(random_entries(ticks, session=sess, scenario="unknown", seed=seed, n=12))

    hist: list[Entry] = []
    hist_paths: dict[str, list[Minute]] = {}
    regime_of: dict[str, str] = {}
    sess_idx: dict[str, list[tuple[datetime, float]]] = {}
    try:
        index = load_index_1m(data / "index_NIFTY.parquet", since="2025-10-01", until="2026-08-10")
        by_idx = group_index_by_session(index)
        for day, bars in by_idx.items():
            closes = [b.close for b in bars]
            regime_of[day] = first30_regime(closes[:30])
            sess_idx[day] = [(b.available_ts, float(b.close)) for b in bars]
        n_days = 0
        for wp in sorted(data.glob("NIFTY_*.parquet")):
            print(f"r3 load {wp.name}", flush=True)
            opt = load_option_week(wp)
            expiry = wp.stem.replace("NIFTY_", "")
            days = sorted({as_ist(b.ts).date().isoformat() for b in opt})
            by_opt: dict[str, list[Any]] = defaultdict(list)
            for b in opt:
                by_opt[as_ist(b.ts).date().isoformat()].append(b)
            for day in days:
                if is_weekend(day):
                    continue
                sc = _tag_scenario(regime_of.get(day) or "unknown", day)
                ents = history_random_entries(
                    by_idx.get(day) or [],
                    by_opt.get(day) or [],
                    session=day,
                    scenario=sc,
                    seed=seed + n_days,
                    n=6,
                    expiry=expiry,
                )
                for e in ents:
                    mins = hist_minutes(e, by_opt.get(day) or [], by_idx.get(day) or [])
                    if sum(1 for m in mins if m.ltp) < 8:
                        continue
                    hist.append(e)
                    hist_paths[e.entry_id] = mins
                n_days += 1
    except HistoryUnavailable as exc:
        _write(out / "history_skip.json", {"error": str(exc)})

    live_paths: dict[str, list[Minute]] = {}
    tagged_live: list[Entry] = []
    for sess, ticks in ticks_cache.items():
        series = _index_from_ticks(ticks)
        if series:
            sess_idx[sess] = series
            regime_of[sess] = first30_regime([px for _, px in series[:30]])
    for e in live:
        mins = live_minutes(e, ticks_cache.get(e.session) or [])
        live_paths[e.entry_id] = mins
        sc = _tag_scenario(regime_of.get(e.session) or e.scenario, e.session)
        tagged_live.append(replace(e, scenario=sc))
    live = tagged_live

    print(f"r3 feat hist={len(hist)} live={len(live)}", flush=True)
    hist_rows = build_feat_rows(hist, hist_paths, regime_of, sess_idx)
    live_rows = build_feat_rows(live, live_paths, regime_of, sess_idx)
    _write(
        out / "n_minutes.json",
        {
            "hist_rows": len(hist_rows),
            "live_rows": len(live_rows),
            "n_hist_entries": len(hist),
            "n_live_entries": len(live),
        },
    )
    print(f"r3 minutes hist={len(hist_rows)} live={len(live_rows)}", flush=True)

    # Mine on all hist (older than live holdout).
    uni = univariate(hist_rows)
    combos = combo_table(hist_rows, uni)
    models = fit_simple_models(hist_rows)
    uni_by = {u["feat"]: u for u in uni if "q25" in u}
    xs_h, _names = matrix(hist_rows)
    ys_h = [1 if r.label_15 == "GOOD_EXIT" else 0 for r in hist_rows]
    print("r3 fit boost/logit", flush=True)
    boost = fit_boost(xs_h, ys_h, rounds=8, depth=2)
    haz_y = [1 if r.label_5 == "GOOD_EXIT" else 0 for r in hist_rows]
    hazard = fit_logit(xs_h, haz_y)

    shape_rows: list[list[float]] = []
    shape_ids: list[str] = []
    for e in hist:
        mins = [m for m in hist_paths[e.entry_id] if m.ltp]
        if len(mins) < 10:
            continue
        first_px = mins[0].ltp
        p0 = float(first_px) if first_px else 1.0
        shape_rows.append([(float(mins[si].ltp or p0) - p0) / (p0 or 1.0) for si in range(10)])
        shape_ids.append(e.entry_id)
    km = kmeans(shape_rows, 5, seed=seed)
    best_of: dict[int, str] = {}
    if km.get("ok"):
        for cid in range(int(km["k"])):
            ids = [shape_ids[si] for si, asg in enumerate(km["assign"]) if asg == cid]
            nets_now = nets_hold = 0.0
            for eid in ids:
                e = next(x for x in hist if x.entry_id == eid)
                mins = hist_paths[eid]
                half = half_spread_pts(e.moneyness)
                nets_now += _proxy_net(e, mins, min(8, len(mins) - 1), half)
                nets_hold += _proxy_net(e, mins, None, half)
            best_of[cid] = "EXIT_NOW" if nets_now > nets_hold else "HOLD"

    agree3 = agree5 = 0
    n_shape = 0
    if km.get("ok") and km.get("centers"):
        centers: list[list[float]] = km["centers"]
        for row, a10 in zip(shape_rows, km["assign"], strict=False):
            pad3 = (row[:3] + [0.0] * 10)[:10]
            pad5 = (row[:5] + [0.0] * 10)[:10]
            n_shape += 1
            if nearest_center(pad3, centers) == a10:
                agree3 += 1
            if nearest_center(pad5, centers) == a10:
                agree5 += 1
    shape_early = {
        "n": n_shape,
        "agree_min3": (agree3 / n_shape) if n_shape else None,
        "agree_min5": (agree5 / n_shape) if n_shape else None,
    }

    print("r3 time grid", flush=True)
    time_grid = _time_grid(hist, hist_paths, range(1, 11), (0.0, 0.5, 1.0, 1.5, 2.0))
    for n, x, _tot in time_grid:
        variants.append(f"time_edge:{n}:{x}")
    best_time = time_grid[0] if time_grid else (3.0, 0.0, 0.0)

    # Best N by TOD / expiry (item 8).
    time_tod: dict[str, Any] = {}
    def _tod_open(e: Entry) -> bool:
        return as_ist(e.ts).hour < 11

    def _tod_mid(e: Entry) -> bool:
        return 11 <= as_ist(e.ts).hour < 14

    def _tod_late(e: Entry) -> bool:
        return as_ist(e.ts).hour >= 14

    def _tod_exp(e: Entry) -> bool:
        return _expiry(e.session)

    def _tod_norm(e: Entry) -> bool:
        return not _expiry(e.session)

    for label, tod_fn in (
        ("open_before_1100", _tod_open),
        ("mid_1100_1400", _tod_mid),
        ("late_after_1400", _tod_late),
        ("expiry", _tod_exp),
        ("normal", _tod_norm),
    ):
        sub = [e for e in hist if tod_fn(e)]
        if len(sub) < 8:
            time_tod[label] = {"n": len(sub), "note": "DATA_INSUFFICIENT"}
            continue
        g = _time_grid(sub, hist_paths, range(1, 11), (0.0, 1.0, 2.0))
        for n, x, _ in g:
            variants.append(f"time_tod:{label}:{n}:{x}")
        time_tod[label] = {
            "n": len(sub),
            "best_n": g[0][0],
            "best_x": g[0][1],
            "proxy_net": g[0][2],
        }

    for bucket in (
        "open_0915_0930",
        "mid_1130",
        "eu_1330",
        "expiry_1430_1515",
        "freeze_1515_1528",
    ):
        variants.append(f"clock:{bucket}")
    for mult in (0.8, 1.2, 1.8):
        variants.append(f"atr:{mult}")
    variants.extend(["divergence", "other_side", "theta_vs_move", "ladder", "shape_exit"])
    for kind in ("tree", "logit", "boost", "hazard"):
        variants.append(f"peak:{kind}")
    for combo in combos:
        variants.append(f"combo:{combo['feats']}")

    pattern_plans: list[ExitPlanFn] = []
    for n, combo in enumerate(combos[:10]):
        checks = _combo_to_checks(combo["feats"], uni_by)
        if not checks:
            continue
        pattern_plans.append(plan_pattern(f"pat_{n}_{combo['kind']}", checks))
        variants.append(f"pat_{n}_{combo['kind']}")
        if n < 3:
            pattern_plans.append(plan_pattern(f"pat_{n}_partial", checks, partial=True))
            pattern_plans.append(plan_pattern(f"pat_{n}_trail", checks, trail_give=2.0))
            variants.append(f"pat_{n}_partial")
            variants.append(f"pat_{n}_trail")

    extra_plans = [
        plan_time_edge(best_time[0], best_time[1]),
        plan_divergence(),
        plan_other_side(),
        plan_theta_vs_move(),
        plan_atr_stop(1.2),
        plan_ladder(),
        plan_shape_exit(km.get("centers") or [], best_of),
        plan_peak_model("tree", 0.35, models["tree"], FEAT_NAMES),
        plan_peak_model("logit", 0.35, models["logit"], FEAT_NAMES),
        plan_peak_model("boost", 0.25, boost, FEAT_NAMES),
        plan_peak_model("hazard", 0.35, hazard, FEAT_NAMES),
    ]
    for bucket in (
        "open_0915_0930",
        "mid_1130",
        "eu_1330",
        "expiry_1430_1515",
        "freeze_1515_1528",
    ):
        extra_plans.append(plan_clock_window(bucket))

    all_plans = {**baselines(), **{p.plan_id: p for p in pattern_plans + extra_plans}}
    variants.extend(["hold_to_1515", "v2_default"])

    feat_hist = _feat_map(hist_rows)
    feat_live = _feat_map(live_rows)

    sessions = sorted({e.session for e in hist})
    fold_size = max(3, len(sessions) // 14)
    folds: list[dict[str, Any]] = []
    start = max(8, fold_size)
    fold_i = 0
    sess_i = start
    while fold_i < 12 and sess_i < len(sessions):
        train_s = set(sessions[:sess_i])
        test_s = set(sessions[sess_i : sess_i + fold_size])
        if not test_s:
            break
        test_e = [e for e in hist if e.session in test_s]
        train_e = [e for e in hist if e.session in train_s]
        train_rows = [fr for fr in hist_rows if fr.session in train_s]
        print(f"r3 fold {fold_i} train={len(train_e)} test={len(test_e)}", flush=True)
        grid = _time_grid(train_e, hist_paths, range(1, 11), (0.0, 1.0, 2.0))
        for n, x, _ in grid:
            variants.append(f"fold{fold_i}_time:{n}:{x}")
        fold_time = plan_time_edge(grid[0][0], grid[0][1]) if grid else plan_time_edge(3, 0.0)
        uni_f = univariate(train_rows) if train_rows else []
        combos_f = combo_table(train_rows, uni_f) if train_rows else []
        uni_by_f = {u["feat"]: u for u in uni_f if "q25" in u}
        fold_plans: dict[str, ExitPlanFn] = {
            "hold_to_1515": all_plans["hold_to_1515"],
            "v2_default": all_plans["v2_default"],
            fold_time.plan_id: fold_time,
        }
        for n, combo_f in enumerate(combos_f[:5]):
            checks = _combo_to_checks(combo_f["feats"], uni_by_f)
            if checks:
                pat = plan_pattern(f"pat_{n}_{combo_f['kind']}", checks)
                fold_plans[pat.plan_id] = pat
                variants.append(f"fold{fold_i}_{pat.plan_id}:{combo_f['feats']}")
        for name in ("divergence", "other_side", "theta_vs_move", "atr_opt_1.2", "ladder_2step"):
            if name in all_plans:
                fold_plans[name] = all_plans[name]
        cell: dict[str, Any] = {
            "fold": fold_i,
            "train_sessions": [*sorted(train_s)[:3], "..."],
            "test_sessions": sorted(test_s),
            "n_train": len(train_e),
            "n_test": len(test_e),
            "mined_top": [combo_f["feats"] for combo_f in combos_f[:5]],
            "rules": {},
        }
        hold_rows = _replay(test_e, hist_paths, all_plans["hold_to_1515"], rates, seed, feat_hist)
        hold_net = sum(tr.net_inr for tr in hold_rows if tr.skipped is None)
        n_so_far = len(set(variants))
        for pid, plan in fold_plans.items():
            rows = _replay(test_e, hist_paths, plan, rates, seed, feat_hist)
            packed = _pack_trades(rows, n_so_far, seed)
            packed["vs_hold"] = round(packed["net_inr"] - hold_net, 2)
            cell["rules"][pid] = packed
        folds.append(cell)
        fold_i += 1
        sess_i += fold_size

    n_variants = len(set(variants))
    print(f"r3 live holdout n_variants={n_variants} plans={len(all_plans)}", flush=True)

    holdout: dict[str, Any] = {}
    live_hold = _replay(live, live_paths, all_plans["hold_to_1515"], rates, seed, feat_live)
    live_v2 = _replay(live, live_paths, all_plans["v2_default"], rates, seed, feat_live)
    hold_net_l = sum(r.net_inr for r in live_hold if r.skipped is None)
    v2_net_l = sum(r.net_inr for r in live_v2 if r.skipped is None)
    holdout["hold_to_1515"] = _pack_trades(live_hold, n_variants, seed)
    holdout["v2_default"] = _pack_trades(live_v2, n_variants, seed)
    by_plan_trades: dict[str, list[TradeResult]] = {
        "hold_to_1515": live_hold,
        "v2_default": live_v2,
    }
    for pid, plan in all_plans.items():
        if pid in {"hold_to_1515", "v2_default"}:
            continue
        print(f"r3 holdout {pid}", flush=True)
        rows = _replay(live, live_paths, plan, rates, seed, feat_live)
        packed = _pack_trades(rows, n_variants, seed)
        packed["vs_hold"] = round(packed["net_inr"] - hold_net_l, 2)
        packed["vs_v2"] = round(packed["net_inr"] - v2_net_l, 2)
        holdout[pid] = packed
        by_plan_trades[pid] = rows

    oracles = []
    for e in live:
        mins = live_paths[e.entry_id]
        half = half_spread_pts(e.moneyness)
        o = oracle_best_net(mins, e, charges_fn=None, half_spread=half)
        mm = mfe_mae(mins, e)
        oracles.append({"entry_id": e.entry_id, "entry_set": e.entry_set, **o, **mm})
    oracle_gross = 0.0
    for orc in oracles:
        og = orc.get("oracle_gross")
        if isinstance(og, int | float):
            oracle_gross += float(og)
    capture = {}
    for pid, rows in by_plan_trades.items():
        real = sum(r.net_inr for r in rows if r.skipped is None)
        capture[pid] = {
            "realized_net": round(real, 2),
            "oracle_gross": round(oracle_gross, 2),
            "capture": (real / oracle_gross) if oracle_gross > 1e-9 else None,
        }

    scored = [
        (pid, holdout[pid]["net_inr"], holdout[pid].get("vs_hold") or 0)
        for pid in holdout
        if pid not in {"hold_to_1515", "v2_default"}
    ]
    scored.sort(key=lambda t: -t[1])
    best_pid = scored[0][0] if scored else "hold_to_1515"
    worst = sorted(
        [r for r in by_plan_trades.get(best_pid, []) if r.skipped is None],
        key=lambda r: r.net_inr,
    )[:30]
    worst_out = []
    for r in worst:
        mins = live_paths.get(r.entry_id) or []
        candles = [
            {
                "ts": as_ist(m.available_ts).isoformat(),
                "ltp": m.ltp,
                "index": m.index,
                "hole": m.hole,
            }
            for m in mins[:40]
        ]
        worst_out.append(
            {
                "entry_id": r.entry_id,
                "session": r.session,
                "side": r.side,
                "net_inr": r.net_inr,
                "exit_reason": r.exit_reason,
                "entry_price": r.entry_price,
                "exit_price": r.exit_price,
                "candles": candles,
                "note": "path on fixed strike; holes omitted from marks",
            }
        )

    overlap = {}
    for pid, rows in by_plan_trades.items():
        hit_against = hit_cover = 0
        n_against = n_cover = 0
        by_id = {r.entry_id: r for r in rows}
        for e in live:
            if e.entry_set != "legacy":
                continue
            reason = str((e.extra or {}).get("legacy_exit_reason") or "")
            closed = (e.extra or {}).get("legacy_closed_ts")
            rec = by_id.get(e.entry_id)
            if reason == "CANCEL_AGAINST":
                n_against += 1
            if reason == "COVER_LONG_UNWIND":
                n_cover += 1
            if rec is None or rec.exit_ts is None or closed is None:
                continue
            try:
                desk = datetime.fromtimestamp(int(closed), tz=IST)
                lab = datetime.fromisoformat(rec.exit_ts)
                close_sec = abs((as_ist(lab) - as_ist(desk)).total_seconds())
            except (TypeError, ValueError):
                continue
            if close_sec <= 180 and rec.exit_reason not in {"FLATTEN_EOD", "CATASTROPHIC_STOP"}:
                if reason == "CANCEL_AGAINST":
                    hit_against += 1
                if reason == "COVER_LONG_UNWIND":
                    hit_cover += 1
        overlap[pid] = {
            "cancel_against": {"n": n_against, "fired_same_moment": hit_against},
            "cover_unwind": {"n": n_cover, "fired_same_moment": hit_cover},
        }

    combo_detail = []
    for combo in combos[:20]:
        mask = combo_pred(hist_rows, combo["feats"])
        ys15 = [1 if fr.label_15 == "GOOD_EXIT" else 0 for fr in hist_rows]
        combo_detail.append(
            {
                **combo,
                "avg_pts_vs_hold": saved_vs_hold(
                    hist_rows, mask, hist_paths, {e.entry_id: e.entry_price for e in hist}
                ),
                "slices": split_slices(hist_rows, mask, ys15),
            }
        )

    mismatches = 0
    checked = 0
    sample = [e for e in live if len(live_paths.get(e.entry_id) or []) > 12][:40]
    for e in sample:
        mins = live_paths[e.entry_id]
        cut = max(2, len(mins) // 3)
        feat_a = features_before(
            mins,
            cut,
            entry=e,
            day_index=_day_index_upto(sess_idx.get(e.session) or [], mins[cut - 1].available_ts),
            regime=regime_of.get(e.session) or "unknown",
            expiry=_expiry(e.session),
        )
        shuffled = shift_minutes(mins, seed=seed + len(e.entry_id))
        feat_b = features_before(
            shuffled,
            cut,
            entry=e,
            day_index=_day_index_upto(
                sess_idx.get(e.session) or [], shuffled[cut - 1].available_ts
            ),
            regime=regime_of.get(e.session) or "unknown",
            expiry=_expiry(e.session),
        )
        checked += 1
        if feat_a != feat_b:
            mismatches += 1

    # Labels use the future: shuffling the tail must change GOOD_EXIT after the cut.
    label_changed = 0
    label_n = 0
    for e in sample:
        mins = live_paths[e.entry_id]
        hs = half_spread_pts(e.moneyness)
        cut = max(2, len(mins) // 3)
        labs_a = labels_for(mins, half_spread=hs)["15"][cut:]
        labs_b = labels_for(
            shift_minutes(mins, seed=seed + 99 + len(e.entry_id)), half_spread=hs
        )["15"][cut:]
        label_n += 1
        if labs_a != labs_b:
            label_changed += 1
    lift_orig = combos[0]["lift"] if combos else None
    lift_shuf: float | None = None
    if combos and hist_rows:
        shuf_rows: list[FeatRow] = []
        for e in hist[:80]:
            mins = hist_paths[e.entry_id]
            if len(mins) < 8:
                continue
            shuf = shift_minutes(mins, seed=seed + 3)
            hs = half_spread_pts(e.moneyness)
            labs = labels_for(shuf, half_spread=hs)
            for fr in hist_rows:
                if fr.entry_id != e.entry_id:
                    continue
                if fr.i >= len(labs["15"]):
                    continue
                shuf_rows.append(
                    FeatRow(
                        entry_id=fr.entry_id,
                        entry_set=fr.entry_set,
                        session=fr.session,
                        side=fr.side,
                        i=fr.i,
                        ts=fr.ts,
                        label_5=labs["5"][fr.i] if fr.i < len(labs["5"]) else "HOLD",
                        label_15=labs["15"][fr.i],
                        label_30=labs["30"][fr.i] if fr.i < len(labs["30"]) else "HOLD",
                        label_eod=labs["eod"][fr.i] if fr.i < len(labs["eod"]) else "HOLD",
                        feats=fr.feats,
                    )
                )
        if shuf_rows:
            shuf_mask = combo_pred(shuf_rows, combos[0]["feats"])
            ys_shuf = [1 if fr.label_15 == "GOOD_EXIT" else 0 for fr in shuf_rows]
            n_hit = sum(shuf_mask)
            goods = sum(ys_shuf[si] for si in range(len(ys_shuf)) if shuf_mask[si])
            base = (sum(ys_shuf) / len(ys_shuf)) if ys_shuf else 0.0
            hit_p = (goods / n_hit) if n_hit else 0.0
            lift_shuf = (hit_p / base) if base > 1e-12 else None
    lookahead_test = {
        "n": checked,
        "mismatches": mismatches,
        "pass": mismatches == 0,
        "labels_changed_after_cut": label_changed,
        "labels_checked": label_n,
        "top_combo_lift_orig": lift_orig,
        "top_combo_lift_shuffled_future_labels": lift_shuf,
        "note": (
            "features_before(i) ignores minutes[i:]; "
            "shuffled tail must not change feats, must change labels"
        ),
    }

    def _stress_spread(entries: list[Entry]) -> dict[str, float]:
        nets = {}
        for name, model in (
            ("base", SlippageModel()),
            ("spread_x2", SlippageModel(spread_mult=2.0)),
        ):
            s = 0.0
            for e in entries[:40]:
                q, _b = minutes_to_series(live_paths[e.entry_id])
                tr = replay_trade(
                    e,
                    all_plans["hold_to_1515"],
                    quotes=q,
                    bars=(),
                    slippage=model,
                    cost_rates=rates,
                    data_source="r3_stress",
                    seed=seed,
                )
                if tr.skipped is None:
                    s += tr.net_inr
            nets[name] = round(s, 2)
        return nets

    spread_stress = _stress_spread(live)

    clock_hits: dict[str, list[float]] = defaultdict(list)
    for fr in live_rows:
        if fr.label_15 != "GOOD_EXIT":
            continue
        try:
            bucket = clock_bucket(
                datetime.fromisoformat(fr.ts), expiry=(fr.feats.get("expiry") or 0) >= 0.5
            )
        except ValueError:
            bucket = "other"
        clock_hits[bucket].append(1.0)
    n_good = max(1, sum(len(x) for x in clock_hits.values()))
    clock_rate = {
        bk: {"n_good": len(vs), "share": len(vs) / n_good} for bk, vs in clock_hits.items()
    }

    passing: list[str] = []
    for pid, cell in holdout.items():
        if pid in {"hold_to_1515", "v2_default"}:
            continue
        ci_lo = cell.get("net_ci_lo")
        dsr = cell.get("deflated_sharpe")
        wf_pos = 0
        wf_n = 0
        for fold in folds:
            rule_cell = None
            for rid, rc in fold["rules"].items():
                if _same_rule(rid, pid):
                    rule_cell = rc
                    break
            if rule_cell and "vs_hold" in rule_cell:
                wf_n += 1
                if (rule_cell.get("vs_hold") or 0) > 0:
                    wf_pos += 1
        most = wf_n > 0 and wf_pos >= (wf_n * 0.5 + 0.01)
        if most and ci_lo is not None and ci_lo > 0 and dsr is not None and dsr >= 0.9:
            passing.append(pid)

    tables = {
        "command": (
            "python -m exitlab round3 --data .local_data --out /tmp/exitlab-r3 "
            "--seed 7 --reuse-entries /tmp/exitlab-fix/entries.json"
        ),
        "seed": seed,
        "n_variants_tested": n_variants,
        "n_hist_entries": len(hist),
        "n_live_entries": len(live),
        "n_hist_minutes": len(hist_rows),
        "n_live_minutes": len(live_rows),
        "n_hist_sessions": len(sessions),
        "n_folds": len(folds),
        "univariate": uni,
        "top20_combos": combo_detail,
        "tree_rules": models["tree_rules"],
        "logit_weights": models["logit_w"][:12],
        "time_grid_top": [
            {"n_min": n, "x_pts": x, "proxy_net": tot} for n, x, tot in time_grid[:8]
        ],
        "best_time_on_hist": {
            "n_min": best_time[0],
            "x_pts": best_time[1],
            "proxy_net": best_time[2],
        },
        "time_tod": time_tod,
        "walk_forward": folds,
        "holdout_live": holdout,
        "oracle": {
            "n": len(oracles),
            "oracle_gross_sum": round(oracle_gross, 2),
            "capture": capture,
            "sample": oracles[:8],
        },
        "mfe_mae": oracles,
        "worst30": {"rule": best_pid, "trades": worst_out},
        "legacy_overlap": overlap,
        "lookahead_test": lookahead_test,
        "spread_stress": spread_stress,
        "clock_good_share": clock_rate,
        "shape": {
            "k": km.get("k"),
            "best_of": best_of,
            "n": len(shape_rows),
            "early_recognize": shape_early,
        },
        "passing": passing,
        "bar": "pass if positive vs hold in most WF folds AND holdout CI_lo>0 AND DSR>=0.9",
        "note": "NO_PROMOTE. Playbook stays off.",
    }

    _write(out / "tables.json", tables)
    _write(out / "univariate.json", uni)
    _write(out / "combos.json", combo_detail)
    _write(out / "walk_forward.json", folds)
    _write(out / "holdout.json", holdout)
    _write(
        out / "oracle.json",
        {"oracle_gross_sum": oracle_gross, "capture": capture, "mfe_mae": oracles},
    )
    _write(out / "worst30.json", {"rule": best_pid, "trades": worst_out})
    _write(out / "legacy_overlap.json", overlap)
    _write(out / "lookahead_test.json", lookahead_test)
    _write(out / "time_tod.json", time_tod)
    _write_mfe_svg(out / "mfe_mae.svg", oracles)
    return tables


def _write_mfe_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    w, h = 640, 400
    pts = [(r.get("mae_pts"), r.get("mfe_pts")) for r in rows if r.get("mfe_pts") is not None]
    if not pts:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>\n")
        return
    xs = [float(a or 0) for a, _ in pts]
    ys = [float(b or 0) for _, b in pts]
    minx, maxx = min([*xs, -1]), max([*xs, 1])
    miny, maxy = min([*ys, -1]), max([*ys, 1])

    def sx(x: float) -> float:
        return 40 + (x - minx) / (maxx - minx + 1e-9) * (w - 60)

    def sy(y: float) -> float:
        return h - 30 - (y - miny) / (maxy - miny + 1e-9) * (h - 50)

    dots = "".join(
        f"<circle cx='{sx(x):.1f}' cy='{sy(y):.1f}' r='2' fill='#2563eb' opacity='0.5'/>"
        for x, y in zip(xs, ys, strict=False)
    )
    path.write_text(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'>"
        f"<rect width='{w}' height='{h}' fill='white'/>"
        f"<text x='8' y='16' font-size='12'>MFE vs MAE (pts) live holdout</text>"
        f"{dots}</svg>\n"
    )

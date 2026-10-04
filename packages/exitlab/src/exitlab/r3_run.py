"""One-command round-3 miner + walk-forward. Paper / replay only."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from exitlab.clock import IST, as_ist
from exitlab.costs import load_cost_rates
from exitlab.entries import entry_from_dict, history_random_entries, random_entries
from exitlab.fills import SlippageModel
from exitlab.harness import replay_trade
from exitlab.history import (
    HistoryUnavailable,
    iter_last3d_days,
    last3d_dir,
    load_index_1m,
    load_option_week,
)
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
    CLOCK_FEATS,
    FEAT_NAMES,
    combo_pred,
    combo_table,
    fit_simple_models,
    is_clock_spec,
    matrix,
    permute_labels_within_day,
    saved_vs_hold,
    split_slices,
    univariate,
)
from exitlab.r3_ml import (
    auc,
    calibration_table,
    fit_boost,
    fit_logit,
    kmeans,
    nearest_center,
    percentile,
    predict_kind,
)
from exitlab.r3_plans import (
    baselines,
    plan_atr_stop,
    plan_clock_profit,
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
from exitlab.stats import (
    bootstrap_mean_ci,
    deflated_sharpe,
    one_lot_nets,
    pts_per_trade,
    sharpe_ratio,
    summarize,
)
from exitlab.tapes import dual_tape_days, load_dual_tape_session
from exitlab.types import Entry, TradeResult

LIVE_SETS = ("random", "v2_boss", "legacy")
PEAK_X = (5, 10, 20)
CLOCK_PROFIT_T = (5, 15, 30, 45, 60)
MODEL_FIT_CAP = 80_000
LOOKAHEAD_N = 5000


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
    return (px - entry.entry_price) * entry.lot_size  # 1-lot proxy


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
        expiry = bool(e.expiry) or _expiry(e.session) or "expiry" in e.scenario
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


def pack_trades(rows: list[TradeResult], n_variants: int, seed: int) -> dict[str, Any]:
    """As-traded book plus 1-lot (65) rank fields. Rank on net_1lot / pts."""
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
    d["as_traded_net_inr"] = d["net_inr"]
    d["as_traded_avg_net"] = d["avg_net"]
    d["as_traded_dsr"] = d["deflated_sharpe"]
    d["as_traded_ci_lo"] = d["net_ci_lo"]
    d["as_traded_ci_hi"] = d["net_ci_hi"]
    lot_nets = one_lot_nets(rows)
    pts = pts_per_trade(rows)
    sr = sharpe_ratio(lot_nets)
    ci = bootstrap_mean_ci(lot_nets, seed=seed) if lot_nets else None
    wins = [x for x in lot_nets if x > 0]
    losses = [x for x in lot_nets if x <= 0]
    d["net_1lot"] = round(sum(lot_nets), 2)
    d["avg_inr_per_lot"] = (sum(lot_nets) / len(lot_nets)) if lot_nets else None
    d["avg_pts"] = (sum(pts) / len(pts)) if pts else None
    d["pts_sum"] = round(sum(pts), 4) if pts else 0.0
    d["sharpe_1lot"] = sr
    d["deflated_sharpe"] = deflated_sharpe(sr, len(lot_nets), n_variants)
    d["net_ci_lo"] = None if ci is None else round(ci[0], 2)
    d["net_ci_hi"] = None if ci is None else round(ci[1], 2)
    d["win_rate_1lot"] = (len(wins) / len(lot_nets)) if lot_nets else None
    d["avg_win_1lot"] = (sum(wins) / len(wins)) if wins else None
    d["avg_loss_1lot"] = (sum(losses) / len(losses)) if losses else None
    for key, pred in (
        ("CE", lambda r: r.side == "CE"),
        ("PE", lambda r: r.side == "PE"),
        ("trend", lambda r: "trend" in r.scenario),
        ("chop", lambda r: "chop" in r.scenario),
        ("expiry", lambda r: "expiry" in r.scenario),
        ("normal", lambda r: "expiry" not in r.scenario),
    ):
        sub = [r for r in rows if pred(r) and r.skipped is None]
        sub_lot = one_lot_nets(sub)
        sub_pts = pts_per_trade(sub)
        wins_s = [x for x in sub_lot if x > 0]
        losses_s = [x for x in sub_lot if x <= 0]
        d[f"slice_{key}"] = {
            "n": len(sub),
            "net_inr": round(sum(r.net_inr for r in sub), 2) if sub else 0.0,
            "net_1lot": round(sum(sub_lot), 2) if sub_lot else 0.0,
            "avg_pts": (sum(sub_pts) / len(sub_pts)) if sub_pts else None,
            "win_rate": (len(wins_s) / len(sub_lot)) if sub_lot else None,
            "avg_win": (sum(wins_s) / len(wins_s)) if wins_s else None,
            "avg_loss": (sum(losses_s) / len(losses_s)) if losses_s else None,
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
    if rid == pid:
        return True
    if rid.startswith("time_edge") and pid.startswith("time_edge"):
        return True
    if rid.startswith("peak_tree") and pid.startswith("peak_tree"):
        return True
    return rid.startswith("clock_profit") and pid.startswith("clock_profit")


def _index_from_ticks(ticks: list[dict[str, Any]]) -> list[tuple[datetime, float]]:
    by: dict[datetime, float] = {}
    for t in ticks:
        idx = t.get("index")
        if idx is None:
            continue
        key = as_ist(t["available_ts"]).replace(second=0, microsecond=0)
        by[key] = float(idx)
    return [(k, by[k]) for k in sorted(by)]


def _sample_rows(rows: list[FeatRow], *, seed: int, cap: int = MODEL_FIT_CAP) -> list[FeatRow]:
    if len(rows) <= cap:
        return rows
    rng = random.Random(seed)
    pos = [r for r in rows if r.label_15 == "GOOD_EXIT"]
    neg = [r for r in rows if r.label_15 != "GOOD_EXIT"]
    n_pos = min(len(pos), max(1, cap // 5))
    n_neg = min(len(neg), cap - n_pos)
    take_pos = pos if len(pos) <= n_pos else rng.sample(pos, n_pos)
    take_neg = neg if len(neg) <= n_neg else rng.sample(neg, n_neg)
    out = take_pos + take_neg
    rng.shuffle(out)
    return out


def _score_rows(kind: str, model: Any, rows: Sequence[FeatRow]) -> list[float]:
    xs, _names = matrix(list(rows))
    key = "logit" if kind == "hazard" else kind
    return [predict_kind(key, model, row) for row in xs]


def _fingerprint(rows: Sequence[TradeResult]) -> tuple[tuple[str, str | None, str, float], ...]:
    closed = [r for r in rows if r.skipped is None]
    closed.sort(key=lambda r: r.entry_id)
    return tuple(
        (r.entry_id, r.exit_ts, r.exit_reason, round(r.net_inr / max(r.lots, 1), 4)) for r in closed
    )


def n_exits_changed(left: Sequence[TradeResult], right: Sequence[TradeResult]) -> int:
    by_r = {r.entry_id: r for r in right}
    n = 0
    for rec in left:
        other = by_r.get(rec.entry_id)
        if other is None:
            continue
        if rec.exit_ts != other.exit_ts or rec.exit_reason != other.exit_reason:
            n += 1
    return n


def _expiry_folds(weeks: list[str], n_folds: int = 12) -> list[tuple[set[str], set[str]]]:
    n = len(weeks)
    if n < 4:
        return []
    chunk = max(1, (n - 20) // n_folds) if n > 20 else 1
    train_end = max(2, n - n_folds * chunk)
    if train_end + chunk > n:
        train_end = max(2, n - n_folds)
        chunk = 1
    out: list[tuple[set[str], set[str]]] = []
    end = train_end
    for _ in range(n_folds):
        test = weeks[end : end + chunk]
        if not test:
            break
        out.append((set(weeks[:end]), set(test)))
        end += chunk
    return out


def _load_hist(
    data: Path, seed: int
) -> tuple[
    list[Entry],
    dict[str, list[Minute]],
    dict[str, str],
    dict[str, list[tuple[datetime, float]]],
    dict[str, Any],
]:
    hist: list[Entry] = []
    hist_paths: dict[str, list[Minute]] = {}
    regime_of: dict[str, str] = {}
    sess_idx: dict[str, list[tuple[datetime, float]]] = {}
    meta: dict[str, Any] = {"source": None, "days_kept": 0, "days_thin": 0, "n_expiries": 0}
    if last3d_dir(data) is not None:
        meta["source"] = "last3d"
        n_days = 0
        expiries: set[str] = set()
        for day, opt, index, expiry in iter_last3d_days(data):
            if is_weekend(day):
                continue
            closes = [b.close for b in index]
            regime_of[day] = first30_regime(closes[:30])
            sess_idx[day] = [(b.available_ts, float(b.close)) for b in index]
            sc = _tag_scenario(regime_of.get(day) or "unknown", day)
            ents = history_random_entries(
                index,
                opt,
                session=day,
                scenario=sc,
                seed=seed + n_days,
                n=8,
                expiry=expiry,
            )
            kept = 0
            for e in ents:
                mins = hist_minutes(e, opt, index)
                if sum(1 for m in mins if m.ltp) < 8:
                    continue
                hist.append(e)
                hist_paths[e.entry_id] = mins
                kept += 1
            if kept < 5:
                meta["days_thin"] += 1
            else:
                meta["days_kept"] += 1
            expiries.add(expiry)
            n_days += 1
            if n_days % 40 == 0:
                print(f"r3 last3d days={n_days} entries={len(hist)}", flush=True)
        meta["n_expiries"] = len(expiries)
        meta["n_days_scanned"] = n_days
        return hist, hist_paths, regime_of, sess_idx, meta

    meta["source"] = "week_files"
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
        meta["n_days_scanned"] = n_days
    except HistoryUnavailable as exc:
        meta["error"] = str(exc)
    return hist, hist_paths, regime_of, sess_idx, meta


def _lookahead_suite(
    hist: list[Entry],
    live: list[Entry],
    hist_paths: dict[str, list[Minute]],
    live_paths: dict[str, list[Minute]],
    sess_idx: dict[str, list[tuple[datetime, float]]],
    regime_of: dict[str, str],
    seed: int,
    n_want: int = LOOKAHEAD_N,
) -> dict[str, Any]:
    rng = random.Random(seed)
    pool: list[tuple[Entry, list[Minute]]] = []
    for e in hist:
        mins = hist_paths.get(e.entry_id) or []
        if len(mins) >= 12:
            pool.append((e, mins))
    for e in live:
        mins = live_paths.get(e.entry_id) or []
        if len(mins) >= 12:
            pool.append((e, mins))
    mismatches = 0
    checked = 0
    n_hist = 0
    n_live = 0
    tries = 0
    while checked < n_want and pool and tries < n_want * 8:
        tries += 1
        e, mins = pool[rng.randrange(len(pool))]
        cut = max(2, len(mins) // 3)
        if cut < 3:
            continue
        i = rng.randrange(2, cut + 1)
        day_idx = _day_index_upto(sess_idx.get(e.session) or [], mins[i - 1].available_ts)
        feat_a = features_before(
            mins,
            i,
            entry=e,
            day_index=day_idx,
            regime=regime_of.get(e.session) or "unknown",
            expiry=_expiry(e.session),
        )
        shuffled = shift_minutes(mins, seed=seed + checked + len(e.entry_id))
        feat_b = features_before(
            shuffled,
            i,
            entry=e,
            day_index=_day_index_upto(sess_idx.get(e.session) or [], shuffled[i - 1].available_ts),
            regime=regime_of.get(e.session) or "unknown",
            expiry=_expiry(e.session),
        )
        checked += 1
        if e.entry_set.startswith("random_hist") or e.entry_id.startswith("hist-"):
            n_hist += 1
        else:
            n_live += 1
        if feat_a != feat_b:
            mismatches += 1
    return {
        "n": checked,
        "mismatches": mismatches,
        "pass": mismatches == 0 and checked >= n_want,
        "n_hist": n_hist,
        "n_live": n_live,
        "tries": tries,
        "note": (
            "features_before(i) ignores minutes[i:]; "
            f"shuffled tail must not change feats ({n_want}+ checks)"
        ),
    }


def _legacy_overlap(
    by_plan: dict[str, list[TradeResult]],
    live: list[Entry],
    hold_rows: list[TradeResult],
) -> dict[str, Any]:
    hold_by = {r.entry_id: r for r in hold_rows}
    out: dict[str, Any] = {}
    for pid, rows in by_plan.items():
        hit_against = hit_cover = 0
        n_against = n_cover = 0
        total_gain = 0.0
        overlap_gain = 0.0
        total_gain_1lot = 0.0
        overlap_gain_1lot = 0.0
        n_overlap = 0
        by_id = {r.entry_id: r for r in rows}
        for e in live:
            if e.entry_set != "legacy":
                continue
            reason = str((e.extra or {}).get("legacy_exit_reason") or "")
            closed = (e.extra or {}).get("legacy_closed_ts")
            rec = by_id.get(e.entry_id)
            hold = hold_by.get(e.entry_id)
            if reason == "CANCEL_AGAINST":
                n_against += 1
            if reason == "COVER_LONG_UNWIND":
                n_cover += 1
            if rec is None or hold is None or rec.skipped or hold.skipped:
                continue
            gain = rec.net_inr - hold.net_inr
            gain_1 = rec.net_inr / max(rec.lots, 1) - hold.net_inr / max(hold.lots, 1)
            total_gain += gain
            total_gain_1lot += gain_1
            if rec.exit_ts is None or closed is None:
                continue
            try:
                desk = datetime.fromtimestamp(int(closed), tz=IST)
                lab = datetime.fromisoformat(rec.exit_ts)
                close_sec = abs((as_ist(lab) - as_ist(desk)).total_seconds())
            except (TypeError, ValueError):
                continue
            if close_sec <= 180 and rec.exit_reason not in {"FLATTEN_EOD", "CATASTROPHIC_STOP"}:
                n_overlap += 1
                overlap_gain += gain
                overlap_gain_1lot += gain_1
                if reason == "CANCEL_AGAINST":
                    hit_against += 1
                if reason == "COVER_LONG_UNWIND":
                    hit_cover += 1
        out[pid] = {
            "cancel_against": {"n": n_against, "fired_same_moment": hit_against},
            "cover_unwind": {"n": n_cover, "fired_same_moment": hit_cover},
            "n_overlap_180s": n_overlap,
            "total_gain_vs_hold": round(total_gain, 2),
            "overlap_gain_vs_hold": round(overlap_gain, 2),
            "share_of_gain_from_overlap": (
                overlap_gain / total_gain if abs(total_gain) > 1e-9 else None
            ),
            "total_gain_1lot": round(total_gain_1lot, 2),
            "overlap_gain_1lot": round(overlap_gain_1lot, 2),
            "share_of_gain_1lot_from_overlap": (
                overlap_gain_1lot / total_gain_1lot if abs(total_gain_1lot) > 1e-9 else None
            ),
        }
    return out


def _stress_spread(
    entries: list[Entry],
    paths: dict[str, list[Minute]],
    plan: ExitPlanFn,
    rates: dict[str, Any],
    seed: int,
    n: int = 80,
) -> dict[str, Any]:
    nets = {"base": 0.0, "spread_x2": 0.0}
    nets_1lot = {"base": 0.0, "spread_x2": 0.0}
    used = 0
    for e in entries[:n]:
        mins = paths.get(e.entry_id) or []
        q, _b = minutes_to_series(mins)
        if not q:
            continue
        used += 1
        for name, mult in (("base", 1.0), ("spread_x2", 2.0)):
            tr = replay_trade(
                e,
                plan,
                quotes=q,
                bars=(),
                slippage=SlippageModel(moneyness=e.moneyness, spread_mult=mult),
                cost_rates=rates,
                data_source="r3_stress",
                seed=seed,
            )
            if tr.skipped is None:
                nets[name] += tr.net_inr
                nets_1lot[name] += tr.net_inr / max(tr.lots, 1)
    return {
        "n": used,
        "as_traded": {k: round(v, 2) for k, v in nets.items()},
        "per_lot": {k: round(v, 2) for k, v in nets_1lot.items()},
    }


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
    dropped: list[dict[str, str]] = [
        {
            "plan": "pat_*_partial",
            "reason": (
                "1-lot tickets cannot PARTIAL (need remaining_qty >= 2*lot_size); "
                "variant is a no-op versus the pair rule"
            ),
        },
        {
            "plan": "clock_open_0915_0930",
            "reason": "entries start after 09:50; window never fires; identical to hold",
        },
    ]

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

    print("r3 load hist", flush=True)
    hist, hist_paths, regime_of, sess_idx, hist_meta = _load_hist(data, seed)
    if hist_meta.get("error"):
        _write(out / "history_skip.json", hist_meta)

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
    live_by_set = {name: [e for e in live if e.entry_set == name] for name in LIVE_SETS}

    print(f"r3 feat hist={len(hist)} live={len(live)} source={hist_meta.get('source')}", flush=True)
    hist_rows = build_feat_rows(hist, hist_paths, regime_of, sess_idx)
    live_rows = build_feat_rows(live, live_paths, regime_of, sess_idx)
    _write(
        out / "n_minutes.json",
        {
            "hist_rows": len(hist_rows),
            "live_rows": len(live_rows),
            "n_hist_entries": len(hist),
            "n_live_entries": len(live),
            "live_by_set": {k: len(v) for k, v in live_by_set.items()},
            "hist_meta": hist_meta,
        },
    )
    print(f"r3 minutes hist={len(hist_rows)} live={len(live_rows)}", flush=True)

    uni = univariate(hist_rows)
    combos = combo_table(hist_rows, uni)
    fit_rows = _sample_rows(hist_rows, seed=seed)
    models = fit_simple_models(fit_rows)
    uni_by = {u["feat"]: u for u in uni if "q25" in u}
    xs_h, _names = matrix(fit_rows)
    ys_h = [1 if r.label_15 == "GOOD_EXIT" else 0 for r in fit_rows]
    print(f"r3 fit boost/logit n={len(fit_rows)}", flush=True)
    boost = fit_boost(xs_h, ys_h, rounds=8, depth=2)
    haz_y = [1 if r.label_5 == "GOOD_EXIT" else 0 for r in fit_rows]
    hazard = fit_logit(xs_h, haz_y)
    peak_models: dict[str, Any] = {
        "tree": models["tree"],
        "logit": models["logit"],
        "boost": boost,
        "hazard": hazard,
    }

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
            member_ids = [shape_ids[si] for si, asg in enumerate(km["assign"]) if asg == cid]
            nets_now = nets_hold = 0.0
            for eid in member_ids:
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

    time_tod: dict[str, Any] = {}

    def _tod_open(e: Entry) -> bool:
        return as_ist(e.ts).hour < 11

    def _tod_mid(e: Entry) -> bool:
        return 11 <= as_ist(e.ts).hour < 14

    def _tod_late(e: Entry) -> bool:
        return as_ist(e.ts).hour >= 14

    def _tod_exp(e: Entry) -> bool:
        return bool(e.expiry) or _expiry(e.session)

    def _tod_norm(e: Entry) -> bool:
        return not (bool(e.expiry) or _expiry(e.session))

    for label, tod_fn in (
        ("open_before_1100", _tod_open),
        ("mid_1100_1400", _tod_mid),
        ("late_after_1400", _tod_late),
        ("expiry", _tod_exp),
        ("normal", _tod_norm),
    ):
        tod_sub = [e for e in hist if tod_fn(e)]
        if len(tod_sub) < 8:
            time_tod[label] = {"n": len(tod_sub), "note": "DATA_INSUFFICIENT"}
            continue
        g = _time_grid(tod_sub, hist_paths, range(1, 11), (0.0, 1.0, 2.0))
        for n, x, _ in g:
            variants.append(f"time_tod:{label}:{n}:{x}")
        time_tod[label] = {
            "n": len(tod_sub),
            "best_n": g[0][0],
            "best_x": g[0][1],
            "proxy_net_1lot": g[0][2],
        }

    for bucket in ("mid_1130", "eu_1330", "expiry_1430_1515", "freeze_1515_1528"):
        variants.append(f"clock:{bucket}")
    for t_before in CLOCK_PROFIT_T:
        variants.append(f"clock_profit:{t_before}")
    for mult in (0.8, 1.2, 1.8):
        variants.append(f"atr:{mult}")
    variants.extend(["divergence", "other_side", "theta_vs_move", "ladder", "shape_exit"])
    for kind in ("tree", "logit", "boost", "hazard"):
        for x_pct in PEAK_X:
            variants.append(f"peak:{kind}:p{x_pct}")
    for combo in combos:
        variants.append(f"combo:{combo['feats']}")

    pattern_plans: list[ExitPlanFn] = []
    trail_pair_ids: list[tuple[str, str]] = []
    for n, combo in enumerate(combos[:10]):
        checks = _combo_to_checks(combo["feats"], uni_by)
        if not checks:
            continue
        pair = plan_pattern(f"pat_{n}_{combo['kind']}", checks)
        pattern_plans.append(pair)
        variants.append(f"pat_{n}_{combo['kind']}")
        if n < 3:
            trail = plan_pattern(f"pat_{n}_trail", checks, trail_give=2.0)
            pattern_plans.append(trail)
            variants.append(f"pat_{n}_trail")
            trail_pair_ids.append((trail.plan_id, pair.plan_id))

    hist_scores: dict[str, list[float]] = {}
    peak_thresh: dict[str, dict[int, float]] = {}
    for kind, model in peak_models.items():
        hist_scores[kind] = _score_rows(kind, model, hist_rows if hist_rows else fit_rows)
        peak_thresh[kind] = {x_pct: percentile(hist_scores[kind], 100 - x_pct) for x_pct in PEAK_X}

    extra_plans = [
        plan_time_edge(best_time[0], best_time[1]),
        plan_divergence(),
        plan_other_side(),
        plan_theta_vs_move(),
        plan_atr_stop(1.2),
        plan_ladder(),
        plan_shape_exit(km.get("centers") or [], best_of),
    ]
    for t_before in CLOCK_PROFIT_T:
        extra_plans.append(plan_clock_profit(float(t_before)))
    for kind, model in peak_models.items():
        for x_pct in PEAK_X:
            extra_plans.append(
                plan_peak_model(
                    kind,
                    peak_thresh[kind][x_pct],
                    model,
                    FEAT_NAMES,
                    tag=f"p{x_pct}",
                )
            )
    for bucket in ("mid_1130", "eu_1330", "expiry_1430_1515", "freeze_1515_1528"):
        extra_plans.append(plan_clock_window(bucket))

    all_plans = {**baselines(), **{p.plan_id: p for p in pattern_plans + extra_plans}}
    variants.extend(["hold_to_1515", "v2_default"])

    feat_hist = _feat_map(hist_rows)
    feat_live = _feat_map(live_rows)

    weeks = sorted({(e.expiry or e.session) for e in hist})
    fold_specs = _expiry_folds(weeks, 12)
    folds: list[dict[str, Any]] = []
    oos_y: dict[str, list[int]] = {k: [] for k in peak_models}
    oos_s: dict[str, list[float]] = {k: [] for k in peak_models}
    for fold_i, (train_w, test_w) in enumerate(fold_specs):
        test_e = [e for e in hist if (e.expiry or e.session) in test_w]
        train_e = [e for e in hist if (e.expiry or e.session) in train_w]
        train_ids = {e.entry_id for e in train_e}
        test_ids = {e.entry_id for e in test_e}
        train_rows = [fr for fr in hist_rows if fr.entry_id in train_ids]
        test_rows = [fr for fr in hist_rows if fr.entry_id in test_ids]
        print(
            f"r3 fold {fold_i} train={len(train_e)} test={len(test_e)} "
            f"weeks={len(train_w)}/{len(test_w)}",
            flush=True,
        )
        grid = _time_grid(train_e, hist_paths, range(1, 11), (0.0, 1.0, 2.0))
        for n, x, _ in grid:
            variants.append(f"fold{fold_i}_time:{n}:{x}")
        fold_time = plan_time_edge(grid[0][0], grid[0][1]) if grid else plan_time_edge(3, 0.0)
        uni_f = univariate(train_rows) if train_rows else []
        combos_f = combo_table(train_rows, uni_f) if train_rows else []
        uni_by_f = {u["feat"]: u for u in uni_f if "q25" in u}
        fold_fit = _sample_rows(train_rows, seed=seed + fold_i) if train_rows else []
        fold_peak: ExitPlanFn | None = None
        fire_rates: dict[str, Any] = {}
        if fold_fit:
            tree_f = fit_simple_models(fold_fit)["tree"]
            scores_tr = _score_rows("tree", tree_f, train_rows)
            for x_pct in PEAK_X:
                thr = percentile(scores_tr, 100 - x_pct)
                test_s = _score_rows("tree", tree_f, test_rows) if test_rows else []
                n_fired = sum(1 for s in test_s if s >= thr)
                fire_rates[f"p{x_pct}"] = {
                    "thresh": thr,
                    "n_test_min": len(test_s),
                    "fires": n_fired,
                    "fire_rate": (n_fired / len(test_s)) if test_s else None,
                }
            fold_peak = plan_peak_model(
                "tree",
                percentile(scores_tr, 90.0),
                tree_f,
                FEAT_NAMES,
                tag="p10",
            )
            if test_rows:
                oos_y["tree"].extend([1 if r.label_15 == "GOOD_EXIT" else 0 for r in test_rows])
                oos_s["tree"].extend(_score_rows("tree", tree_f, test_rows))
        fold_plans: dict[str, ExitPlanFn] = {
            "hold_to_1515": all_plans["hold_to_1515"],
            "v2_default": all_plans["v2_default"],
            fold_time.plan_id: fold_time,
            "clock_profit_30": plan_clock_profit(30.0),
        }
        if fold_peak is not None:
            fold_plans[fold_peak.plan_id] = fold_peak
        for n, combo_f in enumerate(combos_f[:5]):
            checks = _combo_to_checks(combo_f["feats"], uni_by_f)
            if checks:
                pat = plan_pattern(f"pat_{n}_{combo_f['kind']}", checks)
                fold_plans[pat.plan_id] = pat
                variants.append(f"fold{fold_i}_{pat.plan_id}:{combo_f['feats']}")
        for name in ("divergence", "other_side", "theta_vs_move", "atr_opt_1.2"):
            if name in all_plans:
                fold_plans[name] = all_plans[name]
        cell: dict[str, Any] = {
            "fold": fold_i,
            "train_weeks": [*sorted(train_w)[:3], f"...({len(train_w)})"],
            "test_weeks": sorted(test_w),
            "n_train": len(train_e),
            "n_test": len(test_e),
            "mined_top": [combo_f["feats"] for combo_f in combos_f[:5]],
            "peak_fire": fire_rates,
            "rules": {},
        }
        hold_rows = _replay(test_e, hist_paths, all_plans["hold_to_1515"], rates, seed, feat_hist)
        hold_1 = sum(one_lot_nets(hold_rows))
        n_so_far = len(set(variants))
        for pid, plan in fold_plans.items():
            rows = _replay(test_e, hist_paths, plan, rates, seed, feat_hist)
            packed = pack_trades(rows, n_so_far, seed)
            packed["vs_hold"] = round(packed["net_1lot"] - hold_1, 2)
            cell["rules"][pid] = packed
        folds.append(cell)

    # OOS peak AUC from full-hist models on a later-week slice (last 20%).
    peak_diag: dict[str, Any] = {}
    if weeks:
        cut_w = set(weeks[int(len(weeks) * 0.8) :])
        exp_of = {e.entry_id: (e.expiry or e.session) for e in hist}
        oos_rows = [fr for fr in hist_rows if exp_of.get(fr.entry_id, "") in cut_w]
        for kind, model in peak_models.items():
            scores = _score_rows(kind, model, oos_rows) if oos_rows else []
            ys = [1 if r.label_15 == "GOOD_EXIT" else 0 for r in oos_rows]
            fire_map: dict[str, Any] = {}
            for x_pct in PEAK_X:
                thr = peak_thresh[kind][x_pct]
                n_fire = sum(1 for s in scores if s >= thr)
                fire_map[f"p{x_pct}"] = {
                    "thresh": thr,
                    "fire_rate": (n_fire / len(scores)) if scores else None,
                    "n_fire": n_fire,
                    "n": len(scores),
                }
            peak_diag[kind] = {
                "oos_n": len(scores),
                "oos_auc": auc(ys, scores) if scores else None,
                "calibration": calibration_table(ys, scores) if scores else [],
                "fire": fire_map,
                "score_p50": percentile(scores, 50) if scores else None,
                "score_p90": percentile(scores, 90) if scores else None,
                "wf_oos_auc": (
                    auc(oos_y[kind], oos_s[kind]) if oos_y[kind] and oos_s[kind] else None
                ),
            }

    n_variants = len(set(variants))
    print(f"r3 live holdout n_variants={n_variants} plans={len(all_plans)}", flush=True)

    by_plan_trades: dict[str, list[TradeResult]] = {}
    for pid, plan in all_plans.items():
        print(f"r3 holdout {pid}", flush=True)
        by_plan_trades[pid] = _replay(live, live_paths, plan, rates, seed, feat_live)

    holdout_by_set: dict[str, dict[str, Any]] = {}
    for eset in LIVE_SETS:
        eid_set = {e.entry_id for e in live_by_set[eset]}
        holdout_by_set[eset] = {}
        hold_rows = [r for r in by_plan_trades["hold_to_1515"] if r.entry_id in eid_set]
        v2_rows = [r for r in by_plan_trades["v2_default"] if r.entry_id in eid_set]
        hold_1 = sum(one_lot_nets(hold_rows))
        v2_1 = sum(one_lot_nets(v2_rows))
        for pid, rows in by_plan_trades.items():
            hold_sub = [r for r in rows if r.entry_id in eid_set]
            packed = pack_trades(hold_sub, n_variants, seed)
            packed["vs_hold"] = round(packed["net_1lot"] - hold_1, 2)
            packed["vs_v2"] = round(packed["net_1lot"] - v2_1, 2)
            holdout_by_set[eset][pid] = packed

    as_traded_table: dict[str, Any] = {}
    for eset in LIVE_SETS:
        as_traded_table[eset] = {
            pid: {
                "n": holdout_by_set[eset][pid]["n_trades"],
                "as_traded_net_inr": holdout_by_set[eset][pid]["as_traded_net_inr"],
                "as_traded_dsr": holdout_by_set[eset][pid]["as_traded_dsr"],
            }
            for pid in holdout_by_set[eset]
        }

    noop_found: list[dict[str, Any]] = []
    fps: dict[str, tuple[tuple[str, str | None, str, float], ...]] = {
        pid: _fingerprint(rows) for pid, rows in by_plan_trades.items()
    }
    seen_fp: dict[tuple[tuple[str, str | None, str, float], ...], str] = {}
    for pid, fp in fps.items():
        if pid in {"hold_to_1515", "v2_default"}:
            seen_fp[fp] = pid
            continue
        if fp == fps.get("hold_to_1515"):
            noop_found.append({"plan": pid, "identical_to": "hold_to_1515", "action": "drop"})
            dropped.append(
                {"plan": pid, "reason": "results identical to hold_to_1515 on the live holdout"}
            )
            continue
        other = seen_fp.get(fp)
        if other:
            noop_found.append({"plan": pid, "identical_to": other, "action": "drop"})
            dropped.append(
                {"plan": pid, "reason": f"results identical to {other} on the live holdout"}
            )
            continue
        seen_fp[fp] = pid

    trail_changed: dict[str, int] = {}
    for trail_id, pair_id in trail_pair_ids:
        if trail_id in by_plan_trades and pair_id in by_plan_trades:
            n_ch = n_exits_changed(by_plan_trades[trail_id], by_plan_trades[pair_id])
            trail_changed[trail_id] = n_ch
            if n_ch < 1:
                dropped.append(
                    {
                        "plan": trail_id,
                        "reason": f"trail did not change any exit versus {pair_id}",
                    }
                )

    ranked_by_set: dict[str, list[dict[str, Any]]] = {}
    for eset, holdout in holdout_by_set.items():
        dropped_ids = {d["plan"] for d in dropped}
        scored = [
            {
                "plan": pid,
                "net_1lot": holdout[pid]["net_1lot"],
                "avg_pts": holdout[pid]["avg_pts"],
                "avg_inr_per_lot": holdout[pid]["avg_inr_per_lot"],
                "vs_hold": holdout[pid].get("vs_hold"),
                "dsr": holdout[pid].get("deflated_sharpe"),
                "ci_lo": holdout[pid].get("net_ci_lo"),
            }
            for pid in holdout
            if pid not in dropped_ids
        ]
        scored.sort(key=lambda t: -(t["net_1lot"] or 0))
        ranked_by_set[eset] = scored

    oracles: list[dict[str, Any]] = []
    for e in live:
        mins = live_paths[e.entry_id]
        half = half_spread_pts(e.moneyness)
        o = oracle_best_net(mins, e, charges_fn=None, half_spread=half)
        mm = mfe_mae(mins, e)
        og_raw = o.get("oracle_gross")
        og_1: float | None = None
        if isinstance(og_raw, int | float):
            og_1 = float(og_raw) / max(e.lots, 1)
        oracles.append(
            {
                "entry_id": e.entry_id,
                "entry_set": e.entry_set,
                "lots": e.lots,
                **o,
                "oracle_gross_1lot": og_1,
                **mm,
            }
        )
    oracle_by_set: dict[str, dict[str, float]] = {}
    for eset in LIVE_SETS:
        oracle_sub = [o for o in oracles if o["entry_set"] == eset]
        gross = 0.0
        gross_1 = 0.0
        for rec in oracle_sub:
            og_cell = rec.get("oracle_gross")
            if isinstance(og_cell, int | float):
                gross += float(og_cell)
            o1 = rec.get("oracle_gross_1lot")
            if isinstance(o1, int | float):
                gross_1 += float(o1)
        oracle_by_set[eset] = {
            "n": float(len(oracle_sub)),
            "oracle_gross_sum": round(gross, 2),
            "oracle_gross_1lot": round(gross_1, 2),
        }

    capture: dict[str, Any] = {}
    for eset in LIVE_SETS:
        cap_ids = {e.entry_id for e in live_by_set[eset]}
        og1 = oracle_by_set[eset]["oracle_gross_1lot"]
        og = oracle_by_set[eset]["oracle_gross_sum"]
        capture[eset] = {}
        for pid, rows in by_plan_trades.items():
            cap_sub = [r for r in rows if r.entry_id in cap_ids and r.skipped is None]
            real = sum(r.net_inr for r in cap_sub)
            real_1 = sum(one_lot_nets(cap_sub))
            capture[eset][pid] = {
                "realized_net": round(real, 2),
                "realized_1lot": round(real_1, 2),
                "oracle_gross": og,
                "oracle_gross_1lot": og1,
                "capture_1lot": (real_1 / og1) if og1 > 1e-9 else None,
            }

    worst_set = "random" if live_by_set["random"] else LIVE_SETS[0]
    best_pid = (
        ranked_by_set[worst_set][0]["plan"] if ranked_by_set.get(worst_set) else "hold_to_1515"
    )
    ids_w = {e.entry_id for e in live_by_set[worst_set]}
    worst = sorted(
        [r for r in by_plan_trades.get(best_pid, []) if r.skipped is None and r.entry_id in ids_w],
        key=lambda r: r.net_inr / max(r.lots, 1),
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
                "entry_set": r.entry_set,
                "session": r.session,
                "side": r.side,
                "lots": r.lots,
                "net_inr": r.net_inr,
                "net_1lot": r.net_inr / max(r.lots, 1),
                "pts": (None if r.exit_price is None else r.exit_price - r.entry_price),
                "exit_reason": r.exit_reason,
                "entry_price": r.entry_price,
                "exit_price": r.exit_price,
                "candles": candles,
                "note": "path on fixed strike; holes omitted from marks; ranked on 1-lot",
            }
        )

    overlap = _legacy_overlap(by_plan_trades, live, by_plan_trades["hold_to_1515"])

    combo_detail = []
    for combo in combos[:20]:
        mask = combo_pred(hist_rows, combo["feats"])
        ys15 = [1 if fr.label_15 == "GOOD_EXIT" else 0 for fr in hist_rows]
        combo_detail.append(
            {
                **combo,
                "clock": is_clock_spec(combo["feats"]),
                "avg_pts_vs_hold": saved_vs_hold(
                    hist_rows, mask, hist_paths, {e.entry_id: e.entry_price for e in hist}
                ),
                "slices": split_slices(hist_rows, mask, ys15),
            }
        )

    print("r3 lookahead 5000+", flush=True)
    lookahead_test = _lookahead_suite(
        hist, live, hist_paths, live_paths, sess_idx, regime_of, seed, LOOKAHEAD_N
    )
    label_changed = 0
    label_n = 0
    rng_lab = random.Random(seed + 99)
    lab_pool = [e for e in live if len(live_paths.get(e.entry_id) or []) > 12]
    for _ in range(min(200, len(lab_pool) * 4 or 1)):
        if not lab_pool:
            break
        e = lab_pool[rng_lab.randrange(len(lab_pool))]
        mins = live_paths[e.entry_id]
        hs = half_spread_pts(e.moneyness)
        cut = max(2, len(mins) // 3)
        labs_a = labels_for(mins, half_spread=hs)["15"][cut:]
        labs_b = labels_for(shift_minutes(mins, seed=seed + 99 + label_n), half_spread=hs)["15"][
            cut:
        ]
        label_n += 1
        if labs_a != labs_b:
            label_changed += 1
    lookahead_test["labels_changed_after_cut"] = label_changed
    lookahead_test["labels_checked"] = label_n

    print("r3 label permutation remine", flush=True)
    perm_rows = permute_labels_within_day(hist_rows, seed=seed + 5)
    perm_uni = univariate(perm_rows)
    perm_combos = combo_table(perm_rows, perm_uni)
    perm_top = []
    for combo in perm_combos[:10]:
        perm_top.append(
            {
                **combo,
                "clock": is_clock_spec(combo["feats"]),
                "clock_feats_used": [
                    part.split(":")[0]
                    for part in combo["feats"].split("+")
                    if part.split(":")[0] in CLOCK_FEATS
                ],
            }
        )
    lift_orig = combos[0]["lift"] if combos else None
    lift_perm = perm_combos[0]["lift"] if perm_combos else None
    lookahead_test["top_combo_lift_orig"] = lift_orig
    lookahead_test["top_combo_lift_label_permutation"] = lift_perm
    lookahead_test["permutation_top"] = perm_top
    lookahead_test["permutation_note"] = (
        "GOOD_EXIT shuffled within each day; remine. "
        "Lift should fall to ~1.0 except pure clock features (tod_min, mins_to_1515, age_min)."
    )

    spread_stress = {
        "live": _stress_spread(live, live_paths, all_plans["hold_to_1515"], rates, seed, 80),
        "hist": _stress_spread(hist, hist_paths, all_plans["hold_to_1515"], rates, seed, 80),
    }

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

    passing_by_set: dict[str, list[str]] = {}
    dropped_ids = {d["plan"] for d in dropped}
    for eset, holdout in holdout_by_set.items():
        passing: list[str] = []
        for pid, cell_h in holdout.items():
            if pid in {"hold_to_1515", "v2_default"} or pid in dropped_ids:
                continue
            ci_lo = cell_h.get("net_ci_lo")
            dsr = cell_h.get("deflated_sharpe")
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
        passing_by_set[eset] = passing
    if passing_by_set:
        passing_all = sorted(set.intersection(*(set(v) for v in passing_by_set.values())))
    else:
        passing_all = []

    fold_fire_table = [
        {"fold": f["fold"], "n_test": f["n_test"], "peak_fire": f.get("peak_fire")} for f in folds
    ]

    tables = {
        "command": (
            "python -m exitlab round3 --data .local_data --out /tmp/exitlab-r3b "
            "--seed 7 --reuse-entries /tmp/exitlab-fix/entries.json"
        ),
        "seed": seed,
        "n_variants_tested": n_variants,
        "n_hist_entries": len(hist),
        "n_live_entries": len(live),
        "n_live_by_set": {k: len(v) for k, v in live_by_set.items()},
        "n_hist_minutes": len(hist_rows),
        "n_live_minutes": len(live_rows),
        "n_hist_sessions": len({e.session for e in hist}),
        "n_hist_weeks": len(weeks),
        "n_folds": len(folds),
        "hist_meta": hist_meta,
        "rank_on": "net_1lot / avg_pts (lot_size=65). as_traded table kept separately.",
        "univariate": uni,
        "top20_combos": combo_detail,
        "tree_rules": models["tree_rules"],
        "logit_weights": models["logit_w"][:12],
        "time_grid_top": [
            {"n_min": n, "x_pts": x, "proxy_net_1lot": tot} for n, x, tot in time_grid[:8]
        ],
        "best_time_on_hist": {
            "n_min": best_time[0],
            "x_pts": best_time[1],
            "proxy_net_1lot": best_time[2],
        },
        "time_tod": time_tod,
        "clock_profit_T": list(CLOCK_PROFIT_T),
        "walk_forward": folds,
        "holdout_by_set": holdout_by_set,
        "as_traded_table": as_traded_table,
        "ranked_1lot_by_set": ranked_by_set,
        "peak_models": peak_diag,
        "peak_fire_by_fold": fold_fire_table,
        "peak_thresh_hist": {k: {str(x): v[x] for x in v} for k, v in peak_thresh.items()},
        "dropped_noops": dropped,
        "noop_identical": noop_found,
        "trail_exits_changed": trail_changed,
        "oracle": {
            "by_set": oracle_by_set,
            "capture": capture,
            "sample": oracles[:8],
        },
        "mfe_mae": oracles,
        "worst30": {"rule": best_pid, "entry_set": worst_set, "trades": worst_out},
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
        "passing_by_set": passing_by_set,
        "passing": passing_all,
        "bar": (
            "pass if positive vs hold (1-lot) in most WF folds AND holdout 1-lot CI_lo>0 "
            "AND DSR>=0.9, on every live set"
        ),
        "note": "NO_PROMOTE. Playbook stays off. Rank on 1-lot numbers.",
    }

    _write(out / "tables.json", tables)
    _write(out / "univariate.json", uni)
    _write(out / "combos.json", combo_detail)
    _write(out / "walk_forward.json", folds)
    _write(out / "holdout.json", holdout_by_set)
    _write(out / "as_traded.json", as_traded_table)
    _write(
        out / "oracle.json",
        {"by_set": oracle_by_set, "capture": capture, "mfe_mae": oracles},
    )
    _write(out / "worst30.json", {"rule": best_pid, "entry_set": worst_set, "trades": worst_out})
    _write(out / "legacy_overlap.json", overlap)
    _write(out / "lookahead_test.json", lookahead_test)
    _write(out / "time_tod.json", time_tod)
    _write(out / "peak_models.json", peak_diag)
    _write(out / "dropped_noops.json", {"dropped": dropped, "identical": noop_found})
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

"""Run measurements, entry sets, plan grid, sweeps, stress. Writes JSON tables."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from exitlab.clock import as_ist
from exitlab.costs import load_cost_rates
from exitlab.entries import (
    entry_from_dict,
    history_random_entries,
    legacy_entries_from_replay,
    random_entries,
    v2_selector_entries,
)
from exitlab.fills import SlippageModel
from exitlab.harness import replay_trade
from exitlab.history import (
    HistoryUnavailable,
    index_on_session,
    load_index_1m,
    load_option_week,
    option_path,
)
from exitlab.plans import ExitPlanFn, build_plan, library, sweep_specs
from exitlab.scenarios import group_index_by_session, is_weekend, label_session, prior_close
from exitlab.stats import Summary, summarize
from exitlab.tapes import (
    dual_tape_days,
    load_dual_tape_session,
    premium_quote,
    ticks_to_index_bars,
    wing_ltp,
)
from exitlab.types import Bar, Entry, Quote, TradeResult  # Quote used in stress mutate

TRAIN_UNTIL = "2026-05-31"
TEST_SINCE = "2026-06-01"
LIVE_SINCE = "2026-09-14"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _tod_bucket(ts: datetime) -> str:
    t = as_ist(ts).time()
    return f"{t.hour:02d}:{0 if t.minute < 30 else 30:02d}"


def measure_live_tapes(data: Path) -> dict[str, Any]:
    days = dual_tape_days(data)
    sessions: list[dict[str, Any]] = []
    tod: dict[str, list[float]] = defaultdict(list)
    recover: list[dict[str, Any]] = []
    spreads: list[float] = []
    n_ticks = 0
    freeze_hits = 0
    for path in days:
        ticks = load_dual_tape_session(path)
        n_ticks += len(ticks)
        idx_bars = ticks_to_index_bars(ticks)
        ivs = [t["atm_ce_iv"] for t in ticks if t.get("atm_ce_iv")]
        atm_iv = (sum(ivs) / len(ivs)) if ivs else None
        freeze = any(
            as_ist(t["available_ts"]).hour == 15 and as_ist(t["available_ts"]).minute >= 15
            for t in ticks
        )
        if freeze:
            freeze_hits += 1
        label = label_session(
            path.stem,
            idx_bars,
            prev_close=None,
            atm_iv=atm_iv,
            feed_freeze=freeze,
            data_source="legacy_dual_tape",
        )
        sessions.append(asdict(label) | {"n_ticks": len(ticks), "n_index_bars": len(idx_bars)})
        # noise: 15m adverse premium move after a 10:00/11:00/14:00 ATM CE print
        for t in ticks:
            if not t.get("atm_ce") or not t.get("index"):
                continue
            tod[_tod_bucket(t["available_ts"])].append(float(t["atm_ce"]))
        # recovery: after ATM CE drops 8 pts, does it get back +8 before 15:15?
        ces = [(t["available_ts"], t["atm_ce"]) for t in ticks if t.get("atm_ce")]
        for i, (ts0, px0) in enumerate(ces):
            if as_ist(ts0).time().hour < 10:
                continue
            if i + 8 >= len(ces):
                break
            later = ces[i + 1 : i + 40]
            if not later:
                continue
            trough = min(p for _, p in later)
            if px0 - trough < 8:
                continue
            rec = any(p >= px0 + 8 for _, p in later if _ >= ts0)
            recover.append({"session": path.stem, "recovered": rec, "drop": px0 - trough})
    tod_stats = {}
    for bucket, xs in sorted(tod.items()):
        if len(xs) < 4:
            continue
        rets = [xs[i] - xs[i - 1] for i in range(1, len(xs))]
        neg = sorted(-x for x in rets if x < 0)
        tod_stats[bucket] = {
            "n": len(xs),
            "mae_p50": neg[len(neg) // 2] if neg else None,
            "mae_p80": neg[int(0.8 * (len(neg) - 1))] if neg else None,
        }
    n_rec = len(recover)
    n_ok = sum(1 for r in recover if r["recovered"])
    return {
        "data_source": "legacy_dual_tape",
        "n_files": len(days),
        "n_ticks": n_ticks,
        "n_sessions_labelled": len(sessions),
        "freeze_session_count": freeze_hits,
        "sessions": sessions,
        "tod_mae": tod_stats,
        "recovery_after_minus_8": {
            "n": n_rec,
            "n_recovered_to_plus_8": n_ok,
            "rate": (n_ok / n_rec) if n_rec else None,
            "note": ("ATM CE path on live dual-tape. Not a trade. 40 prints after a print."),
        },
        "v2_spread_sample": spreads,
    }


def measure_history(data: Path) -> dict[str, Any]:
    idx_path = data / "index_NIFTY.parquet"
    try:
        index = load_index_1m(idx_path, since="2025-10-01", until="2026-08-31")
    except HistoryUnavailable as exc:
        return {"data_source": "opt1m_sample", "ok": False, "error": str(exc)}
    by_day = group_index_by_session(index)
    weeks = sorted(data.glob("NIFTY_*.parquet"))
    week_meta = []
    for wp in weeks:
        try:
            bars = load_option_week(wp)
        except HistoryUnavailable as exc:
            week_meta.append({"file": wp.name, "ok": False, "error": str(exc)})
            continue
        days = sorted({as_ist(b.ts).date().isoformat() for b in bars})
        week_meta.append(
            {
                "file": wp.name,
                "ok": True,
                "n_bars": len(bars),
                "n_sessions": len(days),
                "first": days[0] if days else None,
                "last": days[-1] if days else None,
                "expiry": wp.stem.replace("NIFTY_", ""),
            }
        )
    labels = []
    for day, bars in by_day.items():
        if day < "2025-10-01" or day > "2026-08-31":
            continue
        if is_weekend(day):
            continue
        labels.append(
            asdict(
                label_session(
                    day,
                    bars,
                    prev_close=prior_close(by_day, day),
                    atm_iv=None,
                    feed_freeze=False,
                    data_source="index_NIFTY.parquet",
                )
            )
        )
    return {
        "data_source": "opt1m_sample + index_NIFTY.parquet",
        "n_index_bars": len(index),
        "n_index_sessions": len(by_day),
        "weeks": week_meta,
        "n_labelled_sessions": len(labels),
        "scenario_counts": _count([x["scenario"] for x in labels]),
        "labels_sample": labels[:8],
        "labels": labels,
    }


def _count(xs: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


# Brief exit categories → library plan that replays them.
CATEGORY_TO_PLAN: dict[str, str] = {
    "pretrade_implied_move_straddle": "implied_move",
    "pretrade_atr_stop": "atr_stop",
    "pretrade_premium_vs_index_stop": "index_stop",
    "pretrade_time_budget": "time_and_stop",
    "pretrade_mae_budget": "noise_band",
    "pretrade_skip_wide_spread_iv_near_square": "implied_move",
    "after_hard_stop_premium": "fixed_stop_target",
    "after_hard_stop_index_pts": "index_stop",
    "after_hard_stop_atr": "atr_stop",
    "after_structure_swing": "structure_stop",
    "after_vol_adjusted_noise": "noise_band",
    "after_time_stop": "time_and_stop",
    "after_no_progress": "legacy_overlay",
    "after_stall": "legacy_overlay",
    "after_breakeven": "breakeven_move",
    "after_trail_chandelier": "chandelier",
    "after_trail_mfe": "mfe_trail",
    "after_trail_step": "step_trail",
    "after_trail_index": "index_trail",
    "after_scale_out": "scale_out",
    "after_target_extend": "target_extend",
    "after_reversal": "reversal",
    "after_momentum_fade_vwap_slope": "momentum_fade",
    "after_iv_crush": "iv_crush",
    "after_iv_spike": "iv_spike",
    "after_theta_bleed": "theta_budget",
    "after_expiry_cliff": "expiry_cliff",
    "after_lunch_chop": "lunch_chop",
    "after_gap": "gap_against",
    "after_stale_feed": "stale_and_flat",
    "after_1515_freeze": "hold_to_1515",
    "after_max_loss_trade": "v2_default",
    "after_max_loss_day": "day_loss",
    "own_quote_persistence": "quote_persistence",
    "own_tod_two_speed": "tod_two_speed",
    "own_elasticity_die": "elasticity_die",
}


def _category_coverage(results: list[TradeResult]) -> dict[str, Any]:
    by_plan: dict[str, int] = {}
    for r in results:
        by_plan[r.plan_id] = by_plan.get(r.plan_id, 0) + 1
    rows = []
    for cat, plan_id in CATEGORY_TO_PLAN.items():
        rows.append(
            {
                "category": cat,
                "plan_id": plan_id,
                "n_replayed": by_plan.get(plan_id, 0),
                "replayed": by_plan.get(plan_id, 0) > 0,
            }
        )
    skipped = [
        {
            "category": "pretrade_har_realised_vol",
            "reason": "No HAR estimator in-repo; used ATR + implied straddle instead.",
        },
        {
            "category": "pretrade_position_size_from_stop",
            "reason": "Live/legacy lots are given (25 / 2 / 1). Not resized in this run.",
        },
        {
            "category": "after_reentry_after_stop",
            "reason": "Re-entry is an entry rule. Not generated as a new ticket in this run.",
        },
        {
            "category": "after_order_not_filled",
            "reason": "Entries are already filled tickets. Rejects run only in stress.reject_p15.",
        },
    ]
    return {"mapped": rows, "not_a_replayed_plan": skipped}


def _series_for_live(
    entry: Entry, ticks: list[dict[str, Any]]
) -> tuple[list[Quote], list[Bar], list[Bar]]:
    quotes: list[Quote] = []
    for t in ticks:
        if as_ist(t["available_ts"]) < as_ist(entry.ts):
            continue
        ltp = wing_ltp(t, side=entry.side, strike=entry.strike)
        if ltp is None:
            q = premium_quote(
                t, side=entry.side, moneyness="ITM" if entry.moneyness.startswith("ITM") else "ATM"
            )
        else:
            q = Quote(
                available_ts=t["available_ts"],
                bid=None,
                ask=None,
                ltp=ltp,
                index=t.get("index"),
                strike=entry.strike,
                side=entry.side,
                source="legacy_dual_tape",
            )
        quotes.append(q)
    return quotes, [], ticks_to_index_bars(ticks)


def _series_for_hist(
    entry: Entry, opt: list[Bar], index: list[Bar]
) -> tuple[list[Quote], list[Bar], list[Bar]]:
    path = option_path(opt, side=entry.side, strike=entry.strike, session=entry.session)
    return [], path, index_on_session(index, entry.session)


def run_research(
    *,
    data: Path,
    out: Path,
    seed: int = 7,
    max_hist_days: int = 40,
    extra_seeds: tuple[int, ...] = (11, 19),
    reuse_entries: Path | None = None,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    rates = load_cost_rates()
    live_measure = measure_live_tapes(data)
    hist_measure = measure_history(data)
    _write_json(out / "measure_live.json", live_measure)
    _write_json(out / "measure_history.json", hist_measure)

    labels_by_day = {s["session"]: s for s in live_measure.get("sessions") or []}
    tod_mae = live_measure.get("tod_mae") or {}
    default_mae = 8.0
    for row in tod_mae.values():
        if row.get("mae_p80"):
            default_mae = float(row["mae_p80"])
            break

    entries: list[Entry] = []
    legacy_meta: list[dict[str, Any]] = []
    if reuse_entries is not None and reuse_entries.is_file():
        loaded = json.loads(reuse_entries.read_text(encoding="utf-8"))
        entries = [entry_from_dict(x) for x in loaded if x.get("entry_set") != "random_hist"]
        hist_from_file = [entry_from_dict(x) for x in loaded if x.get("entry_set") == "random_hist"]
        legacy_meta.append({"reused": str(reuse_entries), "n": len(entries)})
    else:
        hist_from_file = []
        for path in dual_tape_days(data):
            session = path.stem
            if is_weekend(session):
                continue
            ticks = load_dual_tape_session(path)
            if not ticks:
                continue
            scen = (labels_by_day.get(session) or {}).get("scenario") or "unknown"
            expiry = next((t.get("expiry") for t in ticks if t.get("expiry")), None)
            rnd = random_entries(
                ticks,
                session=session,
                scenario=scen,
                seed=seed,
                n=18,
                expiry=str(expiry) if expiry else None,
            )
            entries.extend(rnd)
            try:
                v2 = v2_selector_entries(
                    ticks, session=session, scenario=scen, expiry=str(expiry) if expiry else None
                )
                entries.extend(v2)
            except Exception as exc:
                legacy_meta.append({"session": session, "v2_error": str(exc)})
            leg, meta = legacy_entries_from_replay(path, session=session, scenario=scen)
            entries.extend(leg)
            legacy_meta.append(meta)

    # Extra random seeds (brief: many seeds). Separate from the sweep-choose seed.
    ticks_cache: dict[str, list[dict[str, Any]]] = {}
    for path in dual_tape_days(data):
        ticks_cache[path.stem] = load_dual_tape_session(path)
    have_ids = {e.entry_id for e in entries}
    for extra in extra_seeds:
        if extra == seed:
            continue
        for path in dual_tape_days(data):
            session = path.stem
            if is_weekend(session):
                continue
            ticks = ticks_cache.get(session) or []
            if not ticks:
                continue
            scen = (labels_by_day.get(session) or {}).get("scenario") or "unknown"
            expiry = next((t.get("expiry") for t in ticks if t.get("expiry")), None)
            for e in random_entries(
                ticks,
                session=session,
                scenario=scen,
                seed=extra,
                n=8,
                expiry=str(expiry) if expiry else None,
            ):
                if e.entry_id not in have_ids:
                    entries.append(e)
                    have_ids.add(e.entry_id)

    # History random entries on a time-ordered subset of sessions.
    hist_entries: list[Entry] = list(hist_from_file)
    if not hist_entries:
        try:
            index = load_index_1m(
                data / "index_NIFTY.parquet", since="2025-10-01", until="2026-08-10"
            )
            by_day = group_index_by_session(index)
            hist_labels = {row["session"]: row for row in hist_measure.get("labels") or []}
            weeks = sorted(data.glob("NIFTY_*.parquet"))
            n_hist_days = 0
            for wp in weeks:
                opt = load_option_week(wp)
                expiry = wp.stem.replace("NIFTY_", "")
                days = sorted({as_ist(b.ts).date().isoformat() for b in opt})
                for day in days:
                    if is_weekend(day):
                        continue
                    if n_hist_days >= max_hist_days:
                        break
                    scen = (hist_labels.get(day) or {}).get("scenario") or "unknown"
                    hist_entries.extend(
                        history_random_entries(
                            by_day.get(day) or [],
                            [b for b in opt if as_ist(b.ts).date().isoformat() == day],
                            session=day,
                            scenario=scen,
                            seed=seed + n_hist_days,
                            n=8,
                            expiry=expiry,
                        )
                    )
                    n_hist_days += 1
                if n_hist_days >= max_hist_days:
                    break
        except HistoryUnavailable as exc:
            _write_json(out / "history_skip.json", {"error": str(exc)})

    _write_json(out / "entries.json", [asdict(e) for e in entries + hist_entries])
    _write_json(out / "legacy_replay_meta.json", legacy_meta)

    plans = library()
    sweeps = sweep_specs()
    n_variants = len(plans) + len(sweeps)
    results: list[TradeResult] = []

    def ctx_for(entry: Entry) -> dict[str, Any]:
        bucket = _tod_bucket(entry.ts)
        mae = (tod_mae.get(bucket) or {}).get("mae_p80") or default_mae
        return {
            "tod_mae": mae,
            "chop": "chop" in entry.scenario,
            "regime": entry.scenario,
            "atr": 12.0,
            "day_pnl": 0.0,
            "index_gap_pct": None,
        }

    for entry in entries:
        ticks = ticks_cache.get(entry.session) or []
        quotes, bars, index_bars = _series_for_live(entry, ticks)
        for plan in plans.values():
            results.append(
                replay_trade(
                    entry,
                    plan,
                    quotes=quotes,
                    bars=bars,
                    index_bars=index_bars,
                    cost_rates=rates,
                    ctx_extra=ctx_for(entry),
                    data_source="legacy_dual_tape",
                    seed=seed,
                )
            )

    # Sweeps on train-like live days (choose) vs later live days (report).
    live_days = sorted({e.session for e in entries})
    cut = live_days[len(live_days) // 2] if live_days else LIVE_SINCE
    choose_entries = [e for e in entries if e.session <= cut and e.entry_set == "random"]
    report_entries = [e for e in entries if e.session > cut and e.entry_set == "random"]
    sweep_choose: dict[str, float] = {}
    for spec in sweeps:
        plan = build_plan(spec)
        nets = 0.0
        for entry in choose_entries:
            ticks = ticks_cache.get(entry.session) or []
            quotes, bars, index_bars = _series_for_live(entry, ticks)
            tr = replay_trade(
                entry,
                plan,
                quotes=quotes,
                bars=bars,
                index_bars=index_bars,
                cost_rates=rates,
                ctx_extra=ctx_for(entry),
                data_source="legacy_dual_tape",
                seed=seed,
            )
            nets += tr.net_inr
        sweep_choose[spec.plan_id] = nets
    best_id = max(sweep_choose, key=lambda k: sweep_choose[k]) if sweep_choose else ""
    oos_rows: list[TradeResult] = []
    if best_id:
        best = build_plan(next(s for s in sweeps if s.plan_id == best_id))
        for entry in report_entries:
            ticks = ticks_cache.get(entry.session) or []
            quotes, bars, index_bars = _series_for_live(entry, ticks)
            oos_rows.append(
                replay_trade(
                    entry,
                    best,
                    quotes=quotes,
                    bars=bars,
                    index_bars=index_bars,
                    cost_rates=rates,
                    ctx_extra=ctx_for(entry),
                    data_source="legacy_dual_tape",
                    seed=seed,
                )
            )

    # History OOS: replay core baselines on hist random (if any).
    hist_opt_cache: dict[str, list[Bar]] = {}
    hist_index = None
    try:
        hist_index = load_index_1m(
            data / "index_NIFTY.parquet", since="2025-10-01", until="2026-08-10"
        )
        for wp in sorted(data.glob("NIFTY_*.parquet")):
            hist_opt_cache[wp.stem] = load_option_week(wp)
    except HistoryUnavailable:
        hist_index = None
    if hist_index is not None and hist_entries:
        core = list(plans.values())
        by_day_opt: dict[str, list[Bar]] = defaultdict(list)
        for bars in hist_opt_cache.values():
            for b in bars:
                by_day_opt[as_ist(b.ts).date().isoformat()].append(b)
        for entry in hist_entries:
            opt = by_day_opt.get(entry.session) or []
            quotes, bars, index_bars = _series_for_hist(entry, opt, hist_index)
            split_src = "opt1m_sample_train" if entry.session <= TRAIN_UNTIL else "opt1m_sample_oos"
            for plan in core:
                results.append(
                    replay_trade(
                        entry,
                        plan,
                        quotes=quotes,
                        bars=bars,
                        index_bars=index_bars,
                        cost_rates=rates,
                        ctx_extra=ctx_for(entry),
                        data_source=split_src,
                        seed=seed,
                    )
                )

    stress = _stress(entries, ticks_cache, plans["regime_router"], rates, seed, ctx_for)

    summaries: list[Summary] = []
    grouped: dict[tuple[str, str, str, str], list[TradeResult]] = defaultdict(list)
    for r in results:
        grouped[(r.plan_id, r.entry_set, r.scenario, r.data_source)].append(r)
        grouped[(r.plan_id, r.entry_set, "ALL", r.data_source)].append(r)
    for (plan_id, eset, scen, src), rows in grouped.items():
        split = (
            "oos"
            if "oos" in src or (src == "legacy_dual_tape" and rows and rows[0].session > cut)
            else "all"
        )
        summaries.append(
            summarize(
                rows,
                plan_id=plan_id,
                entry_set=eset,
                scenario=scen,
                split=split,
                n_variants=n_variants,
                data_source=src,
                seed=seed,
            )
        )
    if oos_rows:
        summaries.append(
            summarize(
                oos_rows,
                plan_id=f"sweep_winner_{best_id}",
                entry_set="random",
                scenario="ALL",
                split="oos_live_later",
                n_variants=n_variants,
                data_source="legacy_dual_tape",
                seed=seed,
            )
        )

    tables = {
        "n_variants_tested": n_variants,
        "n_entries_live": len(entries),
        "n_entries_hist": len(hist_entries),
        "n_trade_results": len(results),
        "live_day_cut_for_sweep": cut,
        "sweep_choose_net": sweep_choose,
        "sweep_winner": best_id,
        "summaries": [asdict(s) for s in summaries],
        "stress": stress,
        "legacy_meta": legacy_meta,
        "tod_mae": tod_mae,
        "category_coverage": _category_coverage(results),
        "extra_seeds": list(extra_seeds),
        "n_low_confidence_cells": sum(1 for s in summaries if s.low_confidence),
    }
    _write_json(out / "tables.json", tables)
    _write_json(out / "trades.json", [asdict(r) for r in results])
    _write_json(out / "oos_sweep.json", [asdict(r) for r in oos_rows])
    return tables


def _drop_gap(quotes: list[Quote], start: datetime, width_s: float) -> list[Quote]:
    return [
        q
        for q in quotes
        if not (0 <= (as_ist(q.available_ts) - as_ist(start)).total_seconds() <= width_s)
    ]


def _mutate_quotes(
    quotes: list[Quote],
    *,
    iv_mult: float | None = None,
    prem_mult: float | None = None,
    index_gap_pct: float | None = None,
) -> list[Quote]:
    out: list[Quote] = []
    for q in quotes:
        bid = q.bid
        ask = q.ask
        ltp = q.ltp
        if prem_mult is not None:
            bid = None if bid is None else bid * prem_mult
            ask = None if ask is None else ask * prem_mult
            ltp = None if ltp is None else ltp * prem_mult
        idx = q.index
        if index_gap_pct is not None and idx is not None:
            idx = idx * (1.0 + index_gap_pct)
        iv = q.iv
        if iv_mult is not None and iv is not None:
            iv = iv * iv_mult
        out.append(
            Quote(
                available_ts=q.available_ts,
                bid=bid,
                ask=ask,
                ltp=ltp,
                index=idx,
                iv=iv,
                strike=q.strike,
                side=q.side,
                spread=q.spread,
                source=q.source + "_synthetic",
            )
        )
    return out


def _stress(
    entries: list[Entry],
    ticks_cache: dict[str, list[dict[str, Any]]],
    plan: ExitPlanFn,
    rates: dict[str, Any],
    seed: int,
    ctx_for: Any,
) -> dict[str, Any]:
    sample = [e for e in entries if e.entry_set == "random"][:80]
    if not sample:
        return {"note": "DATA_INSUFFICIENT: no random live entries for stress"}
    cases: dict[str, list[TradeResult]] = {}

    def _run(
        name: str,
        subset: list[Entry],
        *,
        model: SlippageModel | None = None,
        reject_prob: float = 0.0,
        partial_fill_frac: float = 1.0,
        quotes_fn: Any = None,
        extra_ctx: dict[str, Any] | None = None,
        data_source: str = "stress",
    ) -> None:
        rows = []
        for e in subset:
            q, b, i = _series_for_live(e, ticks_cache.get(e.session) or [])
            if quotes_fn is not None:
                q = quotes_fn(e, q)
            ctx = dict(ctx_for(e))
            if extra_ctx:
                ctx.update(extra_ctx)
            rows.append(
                replay_trade(
                    e,
                    plan,
                    quotes=q,
                    bars=b,
                    index_bars=i,
                    slippage=model,
                    cost_rates=rates,
                    ctx_extra=ctx,
                    data_source=data_source,
                    reject_prob=reject_prob,
                    partial_fill_frac=partial_fill_frac,
                    seed=seed,
                )
            )
        cases[name] = rows

    _run("base", sample, model=SlippageModel())
    _run("spread_x2", sample, model=SlippageModel(spread_mult=2.0, slip_mult=1.0))
    _run("slip_x2", sample, model=SlippageModel(slip_mult=2.0))
    _run(
        "gap_1s_synthetic",
        sample[:40],
        quotes_fn=lambda e, qs: _drop_gap(qs, e.ts, 1.0),
        data_source="stress_gap1s_synthetic",
    )
    _run(
        "gap_2s_synthetic",
        sample[:40],
        quotes_fn=lambda e, qs: _drop_gap(qs, e.ts, 2.0),
        data_source="stress_gap2s_synthetic",
    )
    _run(
        "gap_30s_synthetic",
        sample[:40],
        quotes_fn=lambda e, qs: _drop_gap(qs, e.ts, 30.0),
        data_source="stress_gap30s_synthetic",
    )
    _run("partial_fill_half", sample[:40], partial_fill_frac=0.5)
    _run("reject_p15", sample[:40], reject_prob=0.15)
    _run(
        "index_gap_1pct_synthetic",
        sample[:40],
        quotes_fn=lambda e, qs: _mutate_quotes(qs, prem_mult=0.85, index_gap_pct=-0.01),
        extra_ctx={"index_gap_pct": -0.01},
        data_source="stress_gap1pct_synthetic",
    )
    _run(
        "iv_crush_20_synthetic",
        sample[:40],
        quotes_fn=lambda e, qs: _mutate_quotes(qs, iv_mult=0.80, prem_mult=0.88),
        data_source="stress_ivcrush20_synthetic",
    )

    base_nets = [r.net_inr for r in cases["base"] if r.skipped is None]
    rng = random.Random(seed)
    mc: list[float] = []
    if base_nets:
        for _ in range(200):
            mc.append(sum(base_nets[rng.randrange(len(base_nets))] for _ in base_nets))
        mc.sort()

    def _pack(rows: list[TradeResult]) -> dict[str, Any]:
        closed = [r for r in rows if r.skipped is None]
        return {
            "n": len(rows),
            "n_closed": len(closed),
            "n_skipped": sum(1 for r in rows if r.skipped),
            "net_inr": round(sum(r.net_inr for r in closed), 2),
            "reasons": _count([r.exit_reason for r in rows]),
        }

    return {
        "n_sample": len(sample),
        "plan_id": plan.plan_id,
        "cases": {k: _pack(v) for k, v in cases.items()},
        "nets": {k: _pack(v)["net_inr"] for k, v in cases.items()},
        "mc_resample_net": {
            "n": 200,
            "p05": mc[int(0.05 * len(mc))] if mc else None,
            "p50": mc[len(mc) // 2] if mc else None,
            "p95": mc[int(0.95 * (len(mc) - 1))] if mc else None,
        },
        "label": (
            "gap_1s/2s/30s, 1% index gap, and IV crush 20% are SYNTHETIC "
            "(quotes mutated or dropped). partial_fill_half and reject_p15 use harness flags."
        ),
    }

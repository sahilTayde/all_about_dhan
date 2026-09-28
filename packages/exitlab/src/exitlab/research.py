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
from exitlab.types import Bar, Entry, Quote, TradeResult

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
    *, data: Path, out: Path, seed: int = 7, max_hist_days: int = 40
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

    # History random entries on a time-ordered subset of sessions.
    hist_entries: list[Entry] = []
    try:
        index = load_index_1m(data / "index_NIFTY.parquet", since="2025-10-01", until="2026-08-10")
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

    ticks_cache: dict[str, list[dict[str, Any]]] = {}
    for path in dual_tape_days(data):
        ticks_cache[path.stem] = load_dual_tape_session(path)

    def ctx_for(entry: Entry) -> dict[str, Any]:
        bucket = _tod_bucket(entry.ts)
        mae = (tod_mae.get(bucket) or {}).get("mae_p80") or default_mae
        return {
            "tod_mae": mae,
            "chop": "chop" in entry.scenario,
            "regime": entry.scenario,
            "atr": 12.0,
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
        core = [
            plans["hold_to_1515"],
            plans["fixed_stop_target"],
            plans["v2_default"],
            plans["legacy_overlay"],
            plans["regime_router"],
        ]
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
    }
    _write_json(out / "tables.json", tables)
    _write_json(out / "trades.json", [asdict(r) for r in results])
    _write_json(out / "oos_sweep.json", [asdict(r) for r in oos_rows])
    return tables


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
    models = {
        "base": SlippageModel(),
        "spread_x2": SlippageModel(spread_mult=2.0, slip_mult=2.0),
        "slip_x2": SlippageModel(slip_mult=2.0),
    }
    for name, model in models.items():
        rows = []
        for e in sample:
            q, b, i = _series_for_live(e, ticks_cache.get(e.session) or [])
            rows.append(
                replay_trade(
                    e,
                    plan,
                    quotes=q,
                    bars=b,
                    index_bars=i,
                    slippage=model,
                    cost_rates=rates,
                    ctx_extra=ctx_for(e),
                    data_source="stress",
                    seed=seed,
                )
            )
        cases[name] = rows
    # synthetic feed gap: drop quotes in a 30s window mid-trade (labelled synthetic)
    gap_rows = []
    for e in sample[:40]:
        ticks = ticks_cache.get(e.session) or []
        quotes, bars, index_bars = _series_for_live(e, ticks)
        mid = e.ts
        quotes = [
            q
            for q in quotes
            if abs((as_ist(q.available_ts) - as_ist(mid)).total_seconds() - 600) > 30
        ]
        gap_rows.append(
            replay_trade(
                e,
                plan,
                quotes=quotes,
                bars=bars,
                index_bars=index_bars,
                cost_rates=rates,
                ctx_extra=ctx_for(e),
                data_source="stress_gap30s_synthetic",
                seed=seed,
            )
        )
    cases["gap_30s_synthetic"] = gap_rows
    # MC resample trade nets
    base_nets = [r.net_inr for r in cases["base"]]
    rng = random.Random(seed)
    mc = []
    if base_nets:
        for _ in range(200):
            mc.append(sum(base_nets[rng.randrange(len(base_nets))] for _ in base_nets))
        mc.sort()
    return {
        "n_sample": len(sample),
        "plan_id": plan.plan_id,
        "nets": {k: round(sum(r.net_inr for r in v), 2) for k, v in cases.items()},
        "mc_resample_net": {
            "n": 200,
            "p05": mc[int(0.05 * len(mc))] if mc else None,
            "p50": mc[len(mc) // 2] if mc else None,
            "p95": mc[int(0.95 * (len(mc) - 1))] if mc else None,
        },
        "note": (
            "gap_30s is synthetic (quotes dropped). "
            "IV crush 20% and 1% open gap are labelled synthetic in REPORT."
        ),
    }

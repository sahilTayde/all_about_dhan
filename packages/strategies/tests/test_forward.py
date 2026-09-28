"""V2-20a forward-test harness acceptance. Synthetic tape only; no secrets."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from brokers.fills import fcmeas_half_spread
from contracts.clock import IST
from ledger.charges import load_rates, order_charges

from strategies.forward.bars import (
    DATA_INSUFFICIENT,
    KILLED,
    NET_POSITIVE_NOT_SIGNIFICANT,
    PASS_TO_REVIEW,
    PROMISING,
    RUNNING,
    FwdBars,
    bar_state,
    deflated_sharpe,
)
from strategies.forward.eval import evaluate_session, last_quote, load_tape_quotes
from strategies.forward.report import format_report
from strategies.forward.spec import (
    SpecError,
    SpecRefused,
    compute_lock_digest,
    exit_params_hash,
    load_lock,
    load_spec,
    plugin_source,
    verify_lock,
)

ATM = "NSE_FNO:NIFTY:2026-09-29:24500:CE"
ATM_NEW = "NSE_FNO:NIFTY:2026-09-29:24600:CE"
ITM100 = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
ITM200 = "NSE_FNO:NIFTY:2026-09-29:24300:CE"
INDEX = "NSE_IDX:NIFTY"
SESSION = "2026-09-28"
PLUGIN = "strategies.plugins.test_cross"
SESSION_MINUTES = 375  # 09:15-15:30 IST regular session


def _ts(hour: int, minute: int, second: int = 0) -> str:
    return datetime(2026, 9, 28, hour, minute, second, tzinfo=IST).isoformat()


def _row(
    inst: str,
    hh: int,
    mm: int,
    ltp: float,
    bid: float | None,
    ask: float | None,
    bucket: str,
) -> str:
    return json.dumps(
        {
            "instrument_id": inst,
            "ltp": ltp,
            "bid": bid,
            "ask": ask,
            "ltq": 1,
            "volume": 1,
            "oi": 100,
            "bucket": bucket,
            "exchange_ts": _ts(hh, mm),
        }
    )


def _session_fill_lines() -> list[str]:
    """Two-sided depth on every regular-session minute for the spec strikes."""
    start = datetime(2026, 9, 28, 9, 15, tzinfo=IST)
    defaults = {
        ATM: (100.0, 99.80, 100.20, "ATM"),
        ITM100: (150.0, 149.70, 150.30, "ITM100"),
        ITM200: (200.0, 199.65, 200.35, "ITM200"),
    }
    special = {
        (10, 0): {
            ATM: (100.0, 99.80, 100.20),
            ITM100: (150.0, 149.70, 150.30),
            ITM200: (200.0, 199.65, 200.35),
        },
        (10, 15): {
            ATM: (110.0, 109.80, 110.20),
            ITM100: (155.0, 154.70, 155.30),
            ITM200: (198.0, 197.65, 198.35),
        },
        (15, 15): {ATM: (108.0, 107.80, 108.20)},
    }
    lines: list[str] = []
    for i in range(SESSION_MINUTES):
        ts = start + timedelta(minutes=i)
        overlay = special.get((ts.hour, ts.minute), {})
        for inst, (ltp, bid, ask, bucket) in defaults.items():
            if inst in overlay:
                ltp, bid, ask = overlay[inst]
            lines.append(_row(inst, ts.hour, ts.minute, ltp, bid, ask, bucket))
    return lines


def _synth_tape(path: Path, *, extra: list[str] | None = None, thin: bool = False) -> Path:
    lines = _session_fill_lines()
    if extra:
        lines.extend(extra)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    del thin
    return path


def _spec_body() -> dict[object, object]:
    return {
        "spec_id": "FWD-SYNTH-001",
        "strategy_id": "TEST-CROSS",
        "plugin": PLUGIN,
        "version": "1.0.0",
        "stage": "shadow",
        "start_session": SESSION,
        "cost_model": "depth",
        "coefficients": {},
        "params": {
            "fast_period": 5,
            "slow_period": 20,
            "exit_plan": {"catastrophic": {"max_loss": 30000}, "flat_by_ist": "15:15"},
            "strike_router": {"chosen": "ATM"},
            "entry_action": "CHASE",
        },
        "bars": {"n_kill": 30, "n_promising": 60, "n_pass": 120, "t_crit": 2.13},
        "placebos": ["side_flip", "random_minute"],
        "signals": [
            {
                "signal_id": "sg_fwd_1",
                "decision_ts": _ts(10, 0),
                "exit_ts": _ts(10, 15),
                "exit_ts_round11": _ts(15, 15),
                "side": "CE",
                "underlying": "NIFTY",
                "lots": 1,
                "lot_size": 65,
                "chosen": "ATM",
                "instrument_id": ATM,
                "alternatives": {"ATM": ATM, "ITM100": ITM100, "ITM200": ITM200},
            }
        ],
    }


def _write_spec(path: Path, body: dict[object, object] | None = None) -> Path:
    raw = body if body is not None else _spec_body()
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def _write_lock(path: Path, spec_path: Path, *, trials: int = 4621) -> Path:
    spec = load_spec(spec_path)
    digest = compute_lock_digest(spec.raw, plugin_source(spec.plugin), spec.coefficients)
    lock = {
        "cumulative_trials": trials,
        "specs": {
            spec.spec_id: {
                "sha256": digest,
                "exit_sha256": exit_params_hash(spec.params),
                "registered_at": "2026-09-28T00:00:00+05:30",
            }
        },
    }
    path.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
    return path


def _net(entry: float, exit_px: float, qty: int = 65) -> tuple[float, float]:
    rates = load_rates(by_exchange=True)
    gross = (exit_px - entry) * qty
    buy = float(order_charges("BUY", qty, entry, rates, exchange="NSE")["total"])
    sell = float(order_charges("SELL", qty, exit_px, rates, exchange="NSE")["total"])
    return gross, gross - buy - sell


def test_spec_schema_rejects_win_rate_field(tmp_path: Path) -> None:
    body = _spec_body()
    body["win_rate"] = 0.99
    path = tmp_path / "bad.yaml"
    _write_spec(path, body)
    try:
        load_spec(path)
    except SpecError as exc:
        assert "win rates" in str(exc)
    else:
        raise AssertionError("expected SpecError")


def test_spec_hash_mismatch_vs_prereg_lock_refused(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path / "s.yaml")
    lock_path = _write_lock(tmp_path / "prereg.lock", spec_path)
    lock = load_lock(lock_path)
    spec = load_spec(spec_path)
    assert verify_lock(spec, lock)
    spec.raw["params"] = dict(spec.raw["params"])
    spec.raw["params"]["fast_period"] = 99
    try:
        verify_lock(spec, lock)
    except SpecRefused as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("expected SpecRefused")


def test_evaluator_reproduces_hand_computed_pnl_chosen_and_alternatives(tmp_path: Path) -> None:
    tape = _synth_tape(tmp_path / "day.jsonl")
    spec_path = _write_spec(tmp_path / "s.yaml")
    lock_path = _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    report, trades = evaluate_session(spec, tape, SESSION, lock=load_lock(lock_path))
    assert report.state != DATA_INSUFFICIENT
    assert report.kernel_envelopes > 0
    qty = 65
    exp = {
        "chosen": _net(100.30, 109.80, qty),
        "strike:ATM": _net(100.30, 109.80, qty),
        "strike:ITM100": _net(150.40, 154.70, qty),
        "strike:ITM200": _net(200.45, 197.65, qty),
        "entry:CHASE": _net(100.30, 109.80, qty),
        "entry:LIMIT:fvg": _net(100.20, 109.80, qty),
        "entry:WAIT": (0.0, 0.0),
        "exit:own": _net(100.30, 109.80, qty),
        "exit:round11": _net(100.30, 107.80, qty),
    }
    for name, (gross, net) in exp.items():
        got = report.legs[name]
        assert abs(got["gross_inr"] - gross) < 1e-9, name
        assert abs(got["net_depth_inr"] - net) < 1e-9, name
    q_in = last_quote(load_tape_quotes(tape), ATM, datetime.fromisoformat(_ts(10, 0)))
    q_out = last_quote(load_tape_quotes(tape), ATM, datetime.fromisoformat(_ts(10, 15)))
    assert q_in is not None and q_out is not None and q_in.ltp and q_out.ltp
    slip_in = fcmeas_half_spread("ATM", q_in.available_ts)
    slip_out = fcmeas_half_spread("ATM", q_out.available_ts)
    _, fc_net = _net(q_in.ltp + slip_in, q_out.ltp - slip_out, qty)
    assert abs(report.legs["chosen"]["net_fcmeas_inr"] - fc_net) < 1e-9
    assert {t["leg"] for t in trades} >= set(exp)
    assert report.headline_total_net == report.legs["chosen"]["net_depth_inr"]


def test_bar_running_to_killed_at_n30_when_gross_le_0() -> None:
    assert bar_state(n=29, gross=-29.0, nets=[-1.0] * 29) == RUNNING
    assert bar_state(n=30, gross=-30.0, nets=[-1.0] * 30) == KILLED
    assert bar_state(n=30, gross=0.0, nets=[0.0] * 30) == KILLED
    # High win rate is not a pass criterion: 29 tiny wins and one large loss still KILLED.
    mixed = [0.01] * 29 + [-100.0]
    assert bar_state(n=30, gross=sum(mixed), nets=mixed) == KILLED


def test_bar_promising_and_pass_to_review_per_bars() -> None:
    promising = [1.0] * 30 + [1.0] * 30
    assert bar_state(n=60, gross=120.0, nets=promising) == PROMISING
    strong = [10.0] * 120
    assert bar_state(n=120, gross=1200.0, nets=strong) == PASS_TO_REVIEW
    assert bar_state(n=120, gross=1200.0, nets=strong, bars=FwdBars()) == PASS_TO_REVIEW


def test_depth_coverage_below_95_data_insufficient(tmp_path: Path) -> None:
    lines = []
    start = datetime(2026, 9, 28, 10, 0, tzinfo=IST)
    for i in range(20):
        ts = (start + timedelta(minutes=i)).isoformat()
        lines.append(
            json.dumps(
                {
                    "instrument_id": ATM,
                    "ltp": 100.0,
                    "bid": None,
                    "ask": None,
                    "bucket": "ATM",
                    "exchange_ts": ts,
                }
            )
        )
    lines.append(_row(ATM, 10, 20, 100.0, 99.8, 100.2, "ATM"))
    tape = tmp_path / "thin.jsonl"
    tape.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec_path = _write_spec(tmp_path / "s.yaml")
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    report, trades = evaluate_session(spec, tape, SESSION, lock=load_lock(tmp_path / "prereg.lock"))
    assert report.state == DATA_INSUFFICIENT
    assert report.n == 0
    assert trades == []


def test_net_positive_not_significant_stays_shadow() -> None:
    nets = [100.0, -99.0] * 60
    assert sum(nets) > 0
    state = bar_state(n=120, gross=sum(nets) + 120.0, nets=nets)
    assert state == NET_POSITIVE_NOT_SIGNIFICANT
    assert state != PASS_TO_REVIEW


def test_report_headline_total_net_deflated_sharpe_and_trial_count(tmp_path: Path) -> None:
    tape = _synth_tape(tmp_path / "day.jsonl")
    spec_path = _write_spec(tmp_path / "s.yaml")
    _write_lock(tmp_path / "prereg.lock", spec_path, trials=4621)
    spec = load_spec(spec_path)
    report, _ = evaluate_session(spec, tape, SESSION, lock=load_lock(tmp_path / "prereg.lock"))
    line = format_report(report)
    assert line.startswith("FWD-SYNTH-001: headline_total_net=")
    assert "deflated_sharpe=" in line
    assert "cumulative_trials=4621" in line
    assert report.headline_total_net == report.legs["chosen"]["net_depth_inr"]
    assert report.cumulative_trials == 4621
    assert report.stage == "shadow"
    assert deflated_sharpe([1.0, 2.0, -0.5], 4621) != 0.0


def test_random_cut_causality_no_lookahead(tmp_path: Path) -> None:
    poison = _row(ATM, 15, 20, 1.0, 0.5, 1.5, "ATM")
    full = _synth_tape(tmp_path / "full.jsonl", extra=[poison])
    spec_path = _write_spec(tmp_path / "s.yaml")
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    lock = load_lock(tmp_path / "prereg.lock")
    full_rep, _ = evaluate_session(spec, full, SESSION, lock=lock)
    rng = random.Random(11)
    for _ in range(8):
        cut = datetime(2026, 9, 28, 10, 16, tzinfo=IST) + timedelta(minutes=rng.randint(0, 70))
        kept = [
            ln
            for ln in full.read_text(encoding="utf-8").splitlines()
            if ln and datetime.fromisoformat(json.loads(ln)["exchange_ts"]) <= cut
        ]
        cut_path = tmp_path / f"cut-{cut.minute}.jsonl"
        cut_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        cut_rep, _ = evaluate_session(spec, cut_path, SESSION, lock=lock)
        if cut_rep.state != DATA_INSUFFICIENT:
            assert cut_rep.legs["chosen"]["gross_inr"] == full_rep.legs["chosen"]["gross_inr"]
            assert (
                cut_rep.legs["entry:CHASE"]["gross_inr"]
                == full_rep.legs["entry:CHASE"]["gross_inr"]
            )
        assert 1.5 not in {
            last_quote(
                load_tape_quotes(cut_path), ATM, datetime(2026, 9, 28, 10, 0, tzinfo=IST)
            ).ask  # type: ignore[union-attr]
        }
    late = last_quote(load_tape_quotes(full), ATM, datetime(2026, 9, 28, 10, 0, tzinfo=IST))
    assert late is not None and late.ask == 100.20


def test_one_deep_quote_empty_session_coverage_is_one_over_calendar_minutes(
    tmp_path: Path,
) -> None:
    """Issue 1: denominator is all 09:15-15:30 minutes, not observed minutes only."""
    tape = tmp_path / "one.jsonl"
    tape.write_text(_row(ATM, 9, 15, 100.0, 99.80, 100.20, "ATM") + "\n", encoding="utf-8")
    spec_path = _write_spec(tmp_path / "s.yaml")
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    lock = load_lock(tmp_path / "prereg.lock")
    report, trades = evaluate_session(spec, tape, SESSION, lock=lock)
    assert abs(report.depth_coverage - 1 / SESSION_MINUTES) < 1e-12
    assert 0.002 < report.depth_coverage < 0.004
    assert report.state == DATA_INSUFFICIENT
    assert trades == []
    held, _ = evaluate_session(spec, tape, SESSION, lock=lock, prior_nets=[12.0], prior_gross=12.0)
    assert held.state == DATA_INSUFFICIENT
    assert held.n == 1


def test_coverage_uses_spec_instruments_not_tape_index_or_ltp_only(tmp_path: Path) -> None:
    """Issue 2: index quotes and LTP-only ATM must not raise coverage."""
    start = datetime(2026, 9, 28, 9, 15, tzinfo=IST)
    lines: list[str] = []
    for i in range(SESSION_MINUTES):
        ts = (start + timedelta(minutes=i)).isoformat()
        lines.append(
            json.dumps(
                {
                    "instrument_id": INDEX,
                    "ltp": 24500.0,
                    "bid": 24499.9,
                    "ask": 24500.1,
                    "bucket": "INDEX",
                    "exchange_ts": ts,
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "instrument_id": ATM,
                    "ltp": 100.0,
                    "bid": None,
                    "ask": None,
                    "bucket": "ATM",
                    "exchange_ts": ts,
                }
            )
        )
    lines.append(_row(ATM, 9, 15, 100.0, 99.80, 100.20, "ATM"))
    tape = tmp_path / "index.jsonl"
    tape.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec_path = _write_spec(tmp_path / "s.yaml")
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    report, _ = evaluate_session(spec, tape, SESSION, lock=load_lock(tmp_path / "prereg.lock"))
    assert abs(report.depth_coverage - 1 / SESSION_MINUTES) < 1e-12
    assert report.state == DATA_INSUFFICIENT
    assert report.n == 0


def test_late_exchange_ts_sorted_not_crash_and_counted(tmp_path: Path) -> None:
    """Issue 3: late file rows are sorted; older-than-watermark rows are dropped."""
    lines = [
        _row(ATM, 10, 0, 100.0, 99.80, 100.20, "ATM"),
        _row(ATM, 10, 15, 110.0, 109.80, 110.20, "ATM"),
        _row(ATM, 10, 5, 105.0, 104.80, 105.20, "ATM"),
        _row(ATM, 9, 0, 90.0, 89.80, 90.20, "ATM"),
    ]
    tape = tmp_path / "late.jsonl"
    tape.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec_path = _write_spec(tmp_path / "s.yaml")
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    report, _ = evaluate_session(spec, tape, SESSION, lock=load_lock(tmp_path / "prereg.lock"))
    assert report.events_reordered >= 1
    assert report.events_late_dropped >= 1
    assert report.kernel_envelopes > 0
    q_in = last_quote(load_tape_quotes(tape), ATM, datetime.fromisoformat(_ts(10, 0)))
    assert q_in is not None and q_in.ask == 100.20


def _fill_minutes(
    insts: dict[str, tuple[float, float, float, str]],
    *,
    start_hh: int = 9,
    start_mm: int = 15,
    n: int = SESSION_MINUTES,
) -> list[str]:
    start = datetime(2026, 9, 28, start_hh, start_mm, tzinfo=IST)
    lines: list[str] = []
    for i in range(n):
        ts = start + timedelta(minutes=i)
        for inst, (ltp, bid, ask, bucket) in insts.items():
            lines.append(_row(inst, ts.hour, ts.minute, ltp, bid, ask, bucket))
    return lines


def _restrike_body() -> dict[object, object]:
    body = _spec_body()
    morning = dict(body["signals"][0])  # type: ignore[arg-type]
    morning.update(
        {
            "signal_id": "sg_am",
            "decision_ts": _ts(10, 0),
            "exit_ts": _ts(10, 15),
            "instrument_id": ATM,
            "alternatives": {"ATM": ATM, "ITM100": ITM100, "ITM200": ITM200},
        }
    )
    afternoon = dict(morning)
    afternoon.update(
        {
            "signal_id": "sg_pm",
            "decision_ts": _ts(14, 0),
            "exit_ts": _ts(14, 15),
            "instrument_id": ATM_NEW,
            "alternatives": {"ATM": ATM_NEW, "ITM100": ITM100, "ITM200": ITM200},
        }
    )
    body["signals"] = [morning, afternoon]
    return body


def test_dropped_preopen_quote_cannot_change_leg_pnl(tmp_path: Path) -> None:
    """Dropped ts < watermark quotes must not price a 09:15 trade."""
    insts = {
        ATM: (100.0, 99.80, 100.20, "ATM"),
        ITM100: (150.0, 149.70, 150.30, "ITM100"),
        ITM200: (200.0, 199.65, 200.35, "ITM200"),
    }
    # Session quotes start 09:16: no in-session print at the 09:15 decision.
    in_order = _fill_minutes(insts, start_hh=9, start_mm=16, n=SESSION_MINUTES - 1)
    clean = tmp_path / "inorder.jsonl"
    clean.write_text("\n".join(in_order) + "\n", encoding="utf-8")
    dirty = tmp_path / "dropped.jsonl"
    dirty.write_text(
        _row(ATM, 9, 0, 50.0, 49.0, 51.0, "ATM") + "\n" + "\n".join(in_order) + "\n",
        encoding="utf-8",
    )
    body = _spec_body()
    body["signals"][0]["decision_ts"] = _ts(9, 15)  # type: ignore[index]
    body["signals"][0]["exit_ts"] = _ts(10, 15)  # type: ignore[index]
    spec_path = _write_spec(tmp_path / "s.yaml", body)
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    lock = load_lock(tmp_path / "prereg.lock")
    clean_rep, _ = evaluate_session(spec, clean, SESSION, lock=lock)
    dirty_rep, _ = evaluate_session(spec, dirty, SESSION, lock=lock)
    assert dirty_rep.events_late_dropped >= 1
    assert clean_rep.legs == dirty_rep.legs
    assert "chosen" not in clean_rep.legs
    assert "chosen" not in dirty_rep.legs


def test_restrike_old_strike_only_is_data_insufficient(tmp_path: Path) -> None:
    """Morning 24500 / afternoon 24600: only the old strike quoted -> DATA_INSUFFICIENT."""
    insts = {ATM: (100.0, 99.80, 100.20, "ATM")}
    tape = tmp_path / "old.jsonl"
    tape.write_text("\n".join(_fill_minutes(insts)) + "\n", encoding="utf-8")
    spec_path = _write_spec(tmp_path / "s.yaml", _restrike_body())
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    report, _ = evaluate_session(spec, tape, SESSION, lock=load_lock(tmp_path / "prereg.lock"))
    assert report.state == DATA_INSUFFICIENT
    assert report.n == 0
    assert report.depth_coverage < 0.95


def test_restrike_swapped_tape_is_not_covered(tmp_path: Path) -> None:
    """24600 in the morning and 24500 in the afternoon does not cover the schedule."""
    start = datetime(2026, 9, 28, 9, 15, tzinfo=IST)
    switch = datetime(2026, 9, 28, 14, 0, tzinfo=IST)
    lines: list[str] = []
    for i in range(SESSION_MINUTES):
        ts = start + timedelta(minutes=i)
        inst = ATM_NEW if ts < switch else ATM
        bucket = "ATM"
        lines.append(_row(inst, ts.hour, ts.minute, 100.0, 99.80, 100.20, bucket))
    tape = tmp_path / "swap.jsonl"
    tape.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec_path = _write_spec(tmp_path / "s.yaml", _restrike_body())
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    report, _ = evaluate_session(spec, tape, SESSION, lock=load_lock(tmp_path / "prereg.lock"))
    assert report.depth_coverage < 0.95
    assert report.state == DATA_INSUFFICIENT
    assert report.n == 0


def test_random_cut_before_exit_with_coverage_fires_pnl(tmp_path: Path) -> None:
    """Cut before exit_ts, still >=95% calendar coverage, so P&L asserts run."""
    body = _spec_body()
    body["signals"][0]["exit_ts"] = _ts(15, 20)  # type: ignore[index]
    spec_path = _write_spec(tmp_path / "s.yaml", body)
    _write_lock(tmp_path / "prereg.lock", spec_path)
    spec = load_spec(spec_path)
    lock = load_lock(tmp_path / "prereg.lock")
    poison = _row(ATM, 15, 20, 1.0, 0.5, 1.5, "ATM")
    full = _synth_tape(tmp_path / "full.jsonl", extra=[poison])
    full_rep, _ = evaluate_session(spec, full, SESSION, lock=lock)
    assert full_rep.state != DATA_INSUFFICIENT
    assert "chosen" in full_rep.legs
    rng = random.Random(7)
    fired = 0
    for _ in range(6):
        cut = datetime(2026, 9, 28, 15, 11, tzinfo=IST) + timedelta(minutes=rng.randint(0, 8))
        assert cut < datetime(2026, 9, 28, 15, 20, tzinfo=IST)
        kept = [
            ln
            for ln in full.read_text(encoding="utf-8").splitlines()
            if ln and datetime.fromisoformat(json.loads(ln)["exchange_ts"]) <= cut
        ]
        cut_path = tmp_path / f"pre-exit-{cut.minute}.jsonl"
        cut_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        cut_rep, _ = evaluate_session(spec, cut_path, SESSION, lock=lock)
        assert cut_rep.depth_coverage >= 0.95, cut
        assert cut_rep.state != DATA_INSUFFICIENT
        assert "chosen" in cut_rep.legs
        q_in = last_quote(load_tape_quotes(cut_path), ATM, datetime.fromisoformat(_ts(10, 0)))
        q_out = last_quote(load_tape_quotes(cut_path), ATM, datetime.fromisoformat(_ts(15, 20)))
        assert q_in is not None and q_out is not None and q_out.ask != 1.5
        exp_gross, _ = _net(q_in.ask + 0.10, q_out.bid)  # type: ignore[operator]
        assert abs(cut_rep.legs["chosen"]["gross_inr"] - exp_gross) < 1e-9
        assert cut_rep.legs["chosen"]["gross_inr"] != full_rep.legs["chosen"]["gross_inr"]
        fired += 1
    assert fired == 6

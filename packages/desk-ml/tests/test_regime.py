"""Regime service, adaptive weights, overlay and shadow wiring (PR-012 / PR-024). Synthetic data only."""

from __future__ import annotations

import json
import math
import random
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

import desk_ml.paper_scalp as ps
from desk_ml.event_parity import fixture_replay_kwargs, load_fixture
from desk_ml.picker import Vote, picker_majority
from desk_ml.regime import (
    LabelConfig, RegimeConfig, RegimeLabeller, RegimeShadow, WeightConfig, WeightState, cap_shares,
    intermarket_regime, label_bars, load_config, overlay_decision, regime_for_session, use_runner,
    weighted_picker,
)
from desk_ml.regime.labels import IST
from desk_ml.regime.report import board_fingerprint
from desk_ml.regime.weights import StateVersionConflict

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_session_nifty.json"
DAY = 86400


def synthetic_bars(n: int = 375, seed: int = 3, day: str = "2026-09-15", volume: bool = True) -> list[dict]:
    rng = random.Random(seed)
    y, m, d = (int(p) for p in day.split("-"))
    t0 = int(datetime(y, m, d, 9, 15, tzinfo=IST).timestamp())
    px, drift, out = 25000.0, 0.0, []
    for i in range(n):
        if rng.random() < 0.03:
            drift = rng.choice([-4.0, 0.0, 0.0, 4.0])
        sigma = 12.0 if (i // 60) % 3 == 2 else 4.0  # vol regimes
        o = px
        c = o + drift + rng.gauss(0, sigma)
        h, l = max(o, c) + abs(rng.gauss(0, sigma / 2)), min(o, c) - abs(rng.gauss(0, sigma / 2))
        vol = float(rng.randint(100, 900))
        out.append({"ts": t0 + 60 * i, "open": o, "high": h, "low": l, "close": c, "volume": vol if volume else None})
        px = c
    return out


@pytest.fixture()
def fx_patched(monkeypatch):
    fx = load_fixture(FIXTURE)
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (int(fx["lot_size"]), "fixture"))
    return fx


def _replay(fx, runner=None, triples=None, root=None, **kw):
    fx = {**fx, "triples": triples if triples is not None else fx["triples"]}
    with tempfile.TemporaryDirectory() as tmp:
        with use_runner(runner):
            board = ps.replay_paper_scalp(**fixture_replay_kwargs(fx, Path(root or tmp)), write=False, **kw)
    return board


def _runner(**cfg_over) -> RegimeShadow:
    cfg = RegimeConfig.from_dict({**{"mode": "shadow"}, **cfg_over})
    return RegimeShadow(cfg, state=WeightState(cfg.weights), keep_records=True)


# ------------------------------------------------------------------ look-ahead


@pytest.mark.parametrize("volume", [True, False])
def test_minute_label_uses_only_data_up_to_t(volume):
    """Label at minute t from the full session == label from bars[:t+1], and bars after t cannot move it."""
    bars = synthetic_bars(volume=volume)
    kw = dict(prior_close=24850.0, expiry_dates=["2026-09-15", "2026-09-22"])
    full = label_bars(bars, **kw)
    assert {r["primary"] for r in full} >= {"trend_up", "trend_down", "range", "unknown"}
    assert {r["vol"] for r in full} >= {"vol_expansion", "vol_compression"}
    for t in range(len(bars)):
        assert label_bars(bars[: t + 1], **kw)[-1] == full[t], f"minute {t} changed when truncated"
    rng = random.Random(9)
    for t in (0, 30, 120, 250):
        wild = [dict(b, close=b["close"] * rng.uniform(0.9, 1.1), high=b["high"] * 1.2, low=b["low"] * 0.8,
                     volume=1e9) for b in bars[t + 1:]]
        assert label_bars(bars[: t + 1] + wild, **kw)[: t + 1] == full[: t + 1]


def test_shadow_records_are_identical_when_the_tape_is_cut_at_t(fx_patched):
    """End to end: every label / weight / shadow decision before tick k is the same whether or not the
    replay ever sees ticks from k on. Weights therefore never used an outcome from the future."""
    full_r = _runner()
    _replay(fx_patched, full_r)
    assert full_r.working_state("NIFTY").applied, "the fixture must mature outcomes, else weights are never exercised"
    strip = lambda r: {k: v for k, v in r.items() if k not in ("trade_id", "outcome")}  # noqa: E731
    for k in (350, 800):
        cut_r = _runner()
        _replay(fx_patched, cut_r, triples=fx_patched["triples"][:k])
        cut = fx_patched["triples"][k - 1].ts
        a = [strip(r) for r in full_r.records if r["ts"] < cut]
        b = [strip(r) for r in cut_r.records if r["ts"] < cut]
        assert len(a) == len(b) > 100 and a == b
    assert any(r.get("weights") and set(r["weights"].values()) != {1.0} for r in full_r.records), \
        "adaptive weights must actually move off static in this fixture"


def test_outcomes_are_applied_no_earlier_than_they_exist(fx_patched):
    runner = _runner()
    board = _replay(fx_patched, runner)
    runner.finalize()
    closed = {r["trade_id"]: r for r in board["closed_trades"] if r.get("filled")}
    trade_ids = [k for k in runner.state.applied if k.startswith("trade:")]
    assert trade_ids
    for k in trade_ids:
        assert runner.state.applied[k] == int(closed[k[len("trade:"):]]["closed_ts"])
    horizon = runner.cfg.weights.vote_horizon_min * 60
    for k, ts in runner.state.applied.items():
        if k.startswith("vote:"):
            assert ts >= int(k.rsplit(":", 1)[1]) + horizon + 60


def test_weights_never_see_an_outcome_after_the_tick_across_indices(monkeypatch, tmp_path):
    """Replay walks NIFTY's whole day, then SENSEX from 09:15: SENSEX weights must not use NIFTY's later outcomes."""
    from desk_ml.event_parity import synthetic_triples
    from desk_ml.founder_session import save_founder_book

    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: ({"NIFTY": 65, "SENSEX": 20}.get(und, 30), "t"))
    seen = {"calls": 0, "future": 0}
    real = WeightState.weights

    def checked(self, roster, bucket, now_ts):  # counted, not raised: the hook swallows exceptions
        seen["future"] += int(max(self.applied.values(), default=0) > now_ts)
        seen["calls"] += 1
        return real(self, roster, bucket, now_ts)

    monkeypatch.setattr(WeightState, "weights", checked)
    tbu = {"NIFTY": synthetic_triples(seed=5), "SENSEX": synthetic_triples(seed=9, underlying="SENSEX")}
    save_founder_book(list(tbu), root=tmp_path)
    runner = _runner()
    with use_runner(runner):
        board = ps.replay_paper_scalp(root=tmp_path, underlyings=tuple(tbu), triples_by_und=tbu,
                                      session_ist_date="2026-09-10", write=False)
    runner.finalize()
    assert seen["calls"] > 1000 and seen["future"] == 0, seen
    assert {r["underlying"] for r in board["closed_trades"] if r.get("filled")} == {"NIFTY", "SENSEX"}
    assert any(k.startswith("trade:paper-") and "SENSEX" in k for k in runner.state.applied)
    assert any("NIFTY" in k for k in runner.state.applied)  # merged into the shared state at finalize


def test_intermarket_reads_only_days_before_the_session(tmp_path):
    folder = tmp_path / "data" / "recon" / "global_markets"
    folder.mkdir(parents=True)

    def day(ymd, **px):
        (folder / f"{ymd}.jsonl").write_text(
            "".join(json.dumps({"symbol": s, "close": c}) + "\n" for s, c in px.items()), encoding="utf-8")

    for n, ymd in enumerate(["20260908", "20260909", "20260910", "20260911", "20260914", "20260915"]):
        day(ymd, **{"USDINR=X": 83.0 + 0.2 * n, "CL=F": 70.0 + 2 * n, "^VIX": 14.0 + n})
    before = regime_for_session(tmp_path, "2026-09-16")
    assert before["daily"]["label"] == "risk_off" and before["weekly"]["label"] == "risk_off"
    assert before["inputs_missing"] == ["us_futures"]  # degrades: scored on what exists
    day("20260916", **{"USDINR=X": 70.0, "CL=F": 20.0, "^VIX": 5.0})  # same-day and future prints
    day("20260917", **{"USDINR=X": 70.0, "CL=F": 20.0, "^VIX": 5.0})
    assert regime_for_session(tmp_path, "2026-09-16") == before


# ------------------------------------------------------------------ labeller


def test_session_flags_and_config():
    bars = synthetic_bars(n=40)
    lab = label_bars(bars, prior_close=bars[0]["open"] * 1.01, expiry_dates=["2026-09-15"])
    assert all(r["gap_day"] and r["expiry_day"] for r in lab)
    assert lab[-1]["features"]["tte_min"] == pytest.approx(375 - 40, abs=1)
    no_ctx = label_bars(bars)
    assert not any(r["gap_day"] or r["expiry_day"] for r in no_ctx)
    loose = LabelConfig.from_dict({"version": "lab-v1", "adx_trend_min": 0.0, "vwap_confirm_bps": 0.0})
    assert label_bars(bars, loose)[-1]["version"] == "lab-v1"
    with pytest.raises(ValueError):
        LabelConfig.from_dict({"adx_min_typo": 1})
    lab_obj = RegimeLabeller()
    lab_obj.update(bars[0])
    with pytest.raises(ValueError):
        lab_obj.update(bars[0])


def test_repo_config_loads_in_shadow_mode_with_overlay_off():
    cfg = load_config()
    assert cfg.mode == "shadow" and cfg.overlay.get("enabled") is False
    with pytest.raises(ValueError):
        RegimeConfig.from_dict({"mode": "live"})


# ------------------------------------------------------------------ weights


def _votes(rng: random.Random, n: int) -> list[Vote]:
    out = []
    for i in range(n):
        if rng.random() < 0.3:
            out.append(Vote(source=f"a{i}", side=None, reason_class="SILENT", silent=True))
        else:
            out.append(Vote(source=f"a{i}", side=rng.choice(["CE", "PE"]),
                            reason_class=rng.choice(["CONFIRM", "TREND", "GREEKS"]), silent=False))
    return out


def test_weighted_picker_with_unit_weights_is_the_static_picker():
    rng = random.Random(1)
    extra = {"note", "weighted", "w_ce", "w_pe"}
    for _ in range(3000):
        votes = _votes(rng, rng.randint(0, 20))
        cl = {"direction": rng.choice([None, "UP", "DOWN", "FLAT"])}
        a = picker_majority(votes, classified=cl)
        b = weighted_picker(votes, {}, classified=cl)
        assert {k: v for k, v in a.items() if k != "note"} == {k: v for k, v in b.items() if k not in extra}


def test_weighted_picker_can_break_a_tie():
    votes = [Vote("good", "CE", "CONFIRM", False), Vote("bad", "PE", "CONFIRM", False)]
    assert picker_majority(votes)["action"] == "HOLD"
    assert weighted_picker(votes, {"good": 1.4, "bad": 0.6})["side"] == "CE"


def test_shrinkage_min_samples_caps_floors_and_decay():
    cfg = WeightConfig(min_samples=10, prior_strength=10, regime_prior_strength=5, half_life_days=5)
    st = WeightState(cfg)
    t0 = 1_790_000_000
    for i in range(9):
        st.apply_outcome(f"o{i}", t0, "trend_up", [("sharp", True), ("dull", False)], 1.0)
    assert st.multiplier("sharp", "trend_up", t0)["mult"] == 1.0  # below min_samples: static
    for i in range(9, 200):
        st.apply_outcome(f"o{i}", t0, "trend_up", [("sharp", True), ("dull", False)], 1.0)
    up, down = st.multiplier("sharp", "trend_up", t0), st.multiplier("dull", "trend_up", t0)
    assert up["mult"] == cfg.cap and down["mult"] == cfg.floor
    assert st.multiplier("sharp", "range", t0)["why"] == "pooled"  # no regime samples: pooled estimate
    h0, _ = st.counts("sharp", "trend_up", t0)
    h1, _ = st.counts("sharp", "trend_up", t0 + 5 * DAY)
    assert h1 == pytest.approx(h0 / 2)
    few = WeightState(WeightConfig(min_samples=1, prior_strength=100, cap=10, floor=0.1))
    for i in range(5):
        few.apply_outcome(f"f{i}", t0, "range", [("x", True)], 1.0)
    assert 1.0 < few.multiplier("x", "range", t0)["mult"] < 1.1  # heavy prior shrinks a small sample
    assert not st.apply_outcome("o3", t0, "trend_up", [("sharp", False)], 1.0)  # idempotent


def test_max_share_cap():
    w = cap_shares({"a": 10.0, "b": 1.0, "c": 1.0, "d": 1.0, "e": 1.0}, 0.25)
    assert max(w.values()) / sum(w.values()) == pytest.approx(0.25)
    assert w["b"] == 1.0
    assert cap_shares({"a": 5.0, "b": 1.0}, 0.25) == {"a": 5.0, "b": 1.0}  # infeasible: unchanged
    st = WeightState(WeightConfig(min_samples=1, cap=100.0, max_share=0.3))
    for i in range(50):
        st.apply_outcome(str(i), 0, "range", [("star", True)] + [(f"x{j}", False) for j in range(5)], 1.0)
    ws = st.weights(["star"] + [f"x{j}" for j in range(5)], "range", 0)
    assert ws["star"] / sum(ws.values()) <= 0.3 + 1e-9


def test_state_persists_atomically_with_versions(tmp_path):
    path = tmp_path / "state.json"
    st = WeightState()
    st.apply_outcome("trade:1", 1_790_000_000, "range", [("a", True)], 1.0)
    assert st.save(path) == 1
    loaded = WeightState.load(path)
    assert loaded.version == 1 and loaded.buckets == st.buckets and loaded.applied == st.applied
    loaded.apply_outcome("trade:2", 1_790_000_100, "range", [("a", False)], 1.0)
    assert loaded.save(path) == 2
    with pytest.raises(StateVersionConflict):
        st.save(path)  # stale writer (still at v1)
    assert json.loads(path.read_text())["version"] == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json", "state.json.lock"]  # no temp files left
    path.write_text(json.dumps({"schema": 99}))
    with pytest.raises(ValueError):
        WeightState.load(path)


# ------------------------------------------------------------------ overlay


def test_overlay_is_off_by_default_and_prefers_pe_in_a_risk_off_week():
    reg = intermarket_regime({"USDINR=X": [("2026-09-%02d" % d, 83 + 0.3 * d) for d in range(1, 12)],
                              "CL=F": [("2026-09-%02d" % d, 70 + 3 * d) for d in range(1, 12)]})
    assert reg["weekly"]["label"] == "risk_off"
    assert overlay_decision("CE", reg)["veto"] is False
    cfg = {"enabled": True, "use": "weekly", "risk_off": {"prefer": "PE", "veto_other_side": True, "size_mult": 0.5}}
    ce, pe = overlay_decision("CE", reg, cfg), overlay_decision("PE", reg, cfg)
    assert ce["veto"] and ce["reason"] == "OVERLAY_RISK_OFF_PREFER_PE"
    assert not pe["veto"] and pe["size_mult"] == 0.5
    assert overlay_decision("CE", intermarket_regime({}), cfg)["veto"] is False  # no inputs: unknown, no-op


# ------------------------------------------------------------------ shadow wiring


def test_shadow_mode_leaves_the_legacy_replay_byte_identical(fx_patched):
    off = _replay(fx_patched, False)
    runner = _runner()
    shadow = _replay(fx_patched, runner)
    assert len(off["closed_trades"]) >= 5
    assert board_fingerprint(off) == board_fingerprint(shadow)
    assert json.dumps(off["closed_trades"], sort_keys=True) == json.dumps(shadow["closed_trades"], sort_keys=True)
    assert sum(runner.day_report(fx_patched["session_ist_date"], "NIFTY", shadow["closed_trades"])["flips"].values()) > 0


def test_default_hook_runs_in_shadow_from_repo_config(fx_patched, caplog):
    caplog.set_level("INFO", logger="desk_ml.regime")
    board = _replay(fx_patched, None, triples=fx_patched["triples"][:300])
    assert any("regime" in r.getMessage() for r in caplog.records if r.name == "desk_ml.regime")
    assert board_fingerprint(board) == board_fingerprint(_replay(fx_patched, False, triples=fx_patched["triples"][:300]))


def test_apply_mode_uses_the_weighted_decision(fx_patched):
    runner = _runner(mode="apply", weights={"min_samples": 1, "prior_strength": 1, "cap": 3.0, "floor": 0.2})
    applied = _replay(fx_patched, runner)
    assert any(r["flip"] for r in runner.records)
    assert board_fingerprint(applied) != board_fingerprint(_replay(fx_patched, False))


def test_event_path_publishes_labels_and_shadow_decisions(fx_patched):
    from desk_ml.event_path import EventSession

    session = EventSession()
    try:
        board = _replay(fx_patched, _runner(), triples=fx_patched["triples"][:400], event_session=session)
    finally:
        session.close()
    ev = board["event_bus"]["events"]
    assert ev["REGIME_LABEL"] > 1 and ev["BOSS_SHADOW"] > 0
    assert board["event_bus"]["handler_errors"] == []
    plain = _replay(fx_patched, False, triples=fx_patched["triples"][:400])
    assert board["closed_trades"] == plain["closed_trades"]


def test_hook_never_breaks_the_desk(fx_patched, monkeypatch):
    runner = _runner()
    monkeypatch.setattr(runner, "observe", lambda *a, **k: 1 / 0)
    assert board_fingerprint(_replay(fx_patched, runner, triples=fx_patched["triples"][:200])) == board_fingerprint(
        _replay(fx_patched, False, triples=fx_patched["triples"][:200]))


def test_labels_have_no_nan():
    for r in label_bars(synthetic_bars(n=5)):
        for v in r["features"].values():
            assert not (isinstance(v, float) and math.isnan(v))


# ------------------------------------------------------------------ review round 2


CONFIG = Path(__file__).resolve().parents[3] / "config" / "regime.yaml"


def _count_future_lookups(monkeypatch) -> dict:
    """Count weight lookups where any scored outcome, or any bucket the roster would read, is after the tick."""
    seen = {"calls": 0, "future": 0}
    real = WeightState.weights

    def checked(self, roster, bucket, now_ts):  # counted, not raised: the hook swallows exceptions
        rows = [r[2] for a in roster for r in (self.buckets.get(a) or {}).values()]
        latest = max([*self.applied.values(), *rows, int(self.last_outcome_ts or 0)], default=0)
        seen["future"] += int(latest > now_ts)
        seen["calls"] += 1
        return real(self, roster, bucket, now_ts)

    monkeypatch.setattr(WeightState, "weights", checked)
    return seen


def test_saved_state_from_a_later_day_is_not_used_to_replay_an_earlier_day(monkeypatch, tmp_path, caplog):
    """Blocker from the Sep 17-25 review: save after day N, replay day N-2 with the saved state loaded."""
    from desk_ml.event_parity import fixture_replay_kwargs, synthetic_triples
    from desk_ml.regime.report import _fixture_patches, main, run_report, synthetic_days

    args = ["--synthetic", "3", "--root", str(tmp_path), "--config", str(CONFIG)]
    assert main(args + ["--fresh-state", "--save-state"]) == 0
    cfg = load_config(tmp_path, CONFIG)
    state_path = tmp_path / cfg.weights.state_path
    saved = WeightState.load(state_path, cfg.weights)
    day_n, day_early = synthetic_days(3)[-1], synthetic_days(3)[0]
    assert saved.version == 1 and datetime.fromtimestamp(saved.last_outcome_ts, IST).date().isoformat() == day_n

    def replay_early(runner):
        fx = {"underlying": "NIFTY", "session_ist_date": day_early, "lot_size": 65,
              "triples": synthetic_triples(day=day_early, seed=100)}
        with tempfile.TemporaryDirectory() as tmp, _fixture_patches(65):
            return run_report([(day_early, fixture_replay_kwargs(fx, Path(tmp)))], runner)["days"][0]

    seen = _count_future_lookups(monkeypatch)
    caplog.set_level("WARNING", logger="desk_ml.regime")
    loaded = RegimeShadow(cfg, root=tmp_path)  # default: loads the saved state
    assert loaded.state.version == 1
    rep_loaded = replay_early(loaded)
    assert seen["calls"] > 1000 and seen["future"] == 0, seen
    assert loaded.stale_state and loaded.stale_state["version"] == 1
    assert any("ignored for this replay" in r.getMessage() for r in caplog.records)
    rep_fresh = replay_early(RegimeShadow(cfg, root=tmp_path, state=WeightState(cfg.weights)))
    assert rep_loaded["flips_actionable"] == rep_fresh["flips_actionable"]
    # the CLI refuses to overwrite the newer saved state with a replay of an older day
    before = state_path.read_bytes()
    monkeypatch.setattr("desk_ml.regime.report.synthetic_days", lambda n: [day_early])
    assert main(args + ["--save-state"]) == 1
    assert state_path.read_bytes() == before


def test_lookup_ignores_a_bucket_updated_after_the_decision_time():
    st = WeightState(WeightConfig(min_samples=1, prior_strength=1))
    t1 = 1_790_000_000
    for i in range(20):
        st.apply_outcome(f"o{i}", t1, "range", [("a", True)], 1.0)
    assert st.multiplier("a", "range", t1 - 1)["mult"] == 1.0 and st.future_blocked > 0
    assert st.multiplier("a", "range", t1)["mult"] > 1.0
    assert not st.usable_before(t1) and st.usable_before(t1 + 1)


def test_broken_regime_module_logs_once_and_keeps_the_static_decision(fx_patched, monkeypatch, caplog):
    import sys

    monkeypatch.setattr(ps, "_REGIME_HOOK_DOWN", {})
    monkeypatch.setitem(sys.modules, "desk_ml.regime.shadow", None)  # any import of it raises ImportError
    caplog.set_level("ERROR", logger="desk_ml.regime")
    broken = _replay(fx_patched, None, triples=fx_patched["triples"][:300])
    assert sum("regime hook unavailable" in r.getMessage() for r in caplog.records) == 1
    monkeypatch.delitem(sys.modules, "desk_ml.regime.shadow")
    assert board_fingerprint(broken) == board_fingerprint(_replay(fx_patched, False, triples=fx_patched["triples"][:300]))


def test_failed_setup_is_cached_not_retried_every_tick(fx_patched, monkeypatch, tmp_path):
    import desk_ml.regime.shadow as sh

    calls = {"n": 0}

    def boom(root=None, path=None):
        calls["n"] += 1
        raise OSError("config unreadable")

    monkeypatch.setattr(sh, "_setup_failed", {})
    monkeypatch.setattr(sh, "load_config", boom)
    board = _replay(fx_patched, None, triples=fx_patched["triples"][:300], root=tmp_path)
    assert calls["n"] == 1
    _replay(fx_patched, None, triples=fx_patched["triples"][:100], root=tmp_path)  # a new engine inside the minute: no retry
    assert calls["n"] == 1
    sh._setup_failed[str(tmp_path)] -= 61  # a minute later: one retry, then cached again
    _replay(fx_patched, None, triples=fx_patched["triples"][:100], root=tmp_path)
    assert calls["n"] == 2
    assert board_fingerprint(board) == board_fingerprint(_replay(fx_patched, False, triples=fx_patched["triples"][:300]))


def test_state_write_locks_fsyncs_file_and_dir_and_cleans_orphans(tmp_path, monkeypatch):
    import fcntl
    import os
    import threading
    import time as _t

    path = tmp_path / "state.json"
    orphan = tmp_path / "state.json.abc123.tmp"
    orphan.write_text("half a write")
    st = WeightState.load(path)  # start: orphan removed
    assert not orphan.exists()
    synced = []
    real_fsync = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (synced.append(fd), real_fsync(fd)))
    st.apply_outcome("t1", 1, "range", [("a", True)], 1.0)
    assert st.save(path) == 1 and len(synced) >= 2  # temp file + directory
    orphan.write_text("crashed writer")
    lock = open(path.with_name("state.json.lock"), "a+")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    done = []
    worker = threading.Thread(target=lambda: done.append(st.save(path)))
    worker.start()
    _t.sleep(0.3)
    assert worker.is_alive() and not done  # waits for the lock before the version check
    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    lock.close()
    worker.join(5)
    assert done == [2] and not orphan.exists()
    assert json.loads(path.read_text())["version"] == 2


def test_live_loop_re_replay_does_not_re_log_the_same_bars(fx_patched, monkeypatch):
    import desk_ml.regime.shadow as sh
    from desk_ml.event_path import EventSession
    from events import EventAuditLog

    monkeypatch.setattr(sh, "_emitted", {})
    audit = EventAuditLog(":memory:")
    triples = fx_patched["triples"]

    def heartbeat(n, live=True):
        session = EventSession(audit=audit, live_loop=live)
        try:
            _replay(fx_patched, None, triples=triples[:n], event_session=session)
        finally:
            session.close()
        c = audit.counts()
        return c.get("REGIME_LABEL", 0), c.get("BOSS_SHADOW", 0)

    first = heartbeat(300)
    assert first[0] > 1 and first[1] > 0
    assert heartbeat(300) == first  # same session re-replayed: nothing new on the audit log
    grown = heartbeat(400)
    assert grown[0] > first[0] or grown[1] > first[1]  # only the new bars/ticks are added
    assert heartbeat(400) == grown
    control = heartbeat(300, live=False)  # plain replays are not deduped
    assert control[1] > grown[1]

"""Startup self-check, live risk-config selection, and shadow analysts that do not change trades."""

import builtins
from pathlib import Path

import pytest
import yaml

import desk_ml.paper_scalp as ps
from desk_ml.event_parity import compare_boards, fixture_replay_kwargs, synthetic_triples
from desk_ml.event_path import (
    EventBusStartupError,
    EventSession,
    require_event_packages,
    resolve_risk_config,
)

REPO = Path(__file__).resolve().parents[3]


def test_require_event_packages_passes_when_installed():
    require_event_packages()


def test_missing_package_fails_once_with_an_install_message(monkeypatch):
    for key in list(__import__("sys").modules):
        if key == "boss" or key.startswith("boss."):
            monkeypatch.delitem(__import__("sys").modules, key, raising=False)
    real = builtins.__import__

    def fake(name, *args, **kwargs):
        if name == "boss" or str(name).startswith("boss."):
            raise ImportError("No module named 'boss'")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake)
    with pytest.raises(EventBusStartupError) as caught:
        require_event_packages()
    msg = str(caught.value)
    assert "USE_EVENT_BUS is on" in msg
    assert "boss" in msg and "packages/boss" in msg
    assert "pip install -e packages/ledger" in msg
    assert "-e packages/brokers" in msg and "-e packages/risk-engine" in msg
    assert "-e packages/trading_agents_india" in msg
    assert "-e packages/events" in msg and "-e packages/desk" in msg
    assert "stops here" in msg


def test_run_loop_stops_before_replay_when_a_package_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv(ps.USE_EVENT_BUS_ENV, "1")

    def boom():
        raise EventBusStartupError("USE_EVENT_BUS is on but these packages are not installed:\n  - events (packages/events)")

    monkeypatch.setattr("desk_ml.event_path.require_event_packages", boom)
    calls = {"n": 0}

    def replay(**_kw):
        calls["n"] += 1
        raise AssertionError("replay must not start when the startup check fails")

    monkeypatch.setattr(ps, "replay_paper_scalp", replay)
    with pytest.raises(EventBusStartupError, match="not installed"):
        ps.run_loop(root=tmp_path, max_ticks=3, sleep_fn=lambda _s: None)
    assert calls["n"] == 0


def test_live_risk_config_defaults_to_the_strict_file_and_replay_stays_loose():
    live, explicit = resolve_risk_config(live_session=True, settings={})
    assert live.name == "risk_limits.yaml" and explicit is False
    named, named_explicit = resolve_risk_config(
        live_session=True, settings={"live_risk_config": "config/risk_limits_replay.yaml"}
    )
    assert named.name == "risk_limits_replay.yaml" and named_explicit is True
    replay, replay_explicit = resolve_risk_config(live_session=False, settings={})
    assert replay.name == "risk_limits_replay.yaml" and replay_explicit is False
    documented = yaml.safe_load((REPO / "config" / "event_path.yaml").read_text())
    assert documented["live_risk_config"].endswith("risk_limits.yaml")
    strict = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())["modes"]["paper"]
    loose = yaml.safe_load((REPO / "config" / "risk_limits_replay.yaml").read_text())["modes"]["paper"]
    assert strict["max_loss_per_trade"] > loose["max_loss_per_trade"]


def test_live_paper_loop_refuses_a_silent_replay_risk_config(monkeypatch, tmp_path):
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "t"))
    monkeypatch.setattr(
        "desk_ml.event_path.resolve_risk_config",
        lambda **_k: (Path("config/risk_limits_replay.yaml"), False),
    )
    with pytest.raises(RuntimeError, match="risk_limits_replay"):
        ps.replay_paper_scalp(
            root=tmp_path, underlyings=("NIFTY",), triples_by_und={"NIFTY": []},
            live_session=True, use_event_bus=True, write=False,
        )


def test_live_paper_loop_uses_the_strict_risk_file(monkeypatch, tmp_path):
    """The event-bus live loop constructs RiskEngine from risk_limits.yaml, not the replay file."""
    import risk_engine.engine as eng

    seen: list[Path] = []
    orig = eng.RiskEngine.__init__

    def wrapped(self, ledger=None, config_path=eng.DEFAULT_CONFIG_PATH):
        seen.append(Path(config_path))
        return orig(self, ledger, config_path)

    monkeypatch.setattr(eng.RiskEngine, "__init__", wrapped)
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "fixture"))
    triples = synthetic_triples()[:12]
    fx = {"underlying": "NIFTY", "session_ist_date": "2026-09-10", "triples": triples, "lot_size": 65}
    ps.replay_paper_scalp(**fixture_replay_kwargs(fx, tmp_path), live_session=True, use_event_bus=True, write=False)
    assert seen, "live event path never built a risk engine"
    assert all(p.name == "risk_limits.yaml" for p in seen)
    assert all("risk_limits_replay" not in p.name for p in seen)

    seen.clear()
    ps.replay_paper_scalp(**fixture_replay_kwargs(fx, tmp_path), live_session=False, use_event_bus=False, write=False)
    assert seen == []


def _legacy_analysts_yaml(tmp_path: Path) -> Path:
    cfg = yaml.safe_load((REPO / "config" / "analysts.yaml").read_text())
    keys = []
    for item in cfg["analysts"]:
        if isinstance(item, str):
            keys.append(item)
        elif not item.get("shadow"):
            keys.append(item["key"])
    path = tmp_path / "legacy_analysts.yaml"
    path.write_text(yaml.safe_dump({"timeout_ms": cfg["timeout_ms"], "analysts": keys}))
    return path


def test_shadow_analysts_do_not_change_trades(monkeypatch, tmp_path):
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "fixture"))
    triples = synthetic_triples()[:700]
    fx = {"underlying": "NIFTY", "session_ist_date": "2026-09-10", "triples": triples, "lot_size": 65}
    kw = fixture_replay_kwargs(fx, tmp_path)
    with_shadow = EventSession()
    without = EventSession(analysts_config=_legacy_analysts_yaml(tmp_path))
    try:
        board_on = ps.replay_paper_scalp(**kw, event_session=with_shadow, write=False)
        board_off = ps.replay_paper_scalp(**kw, event_session=without, write=False)
    finally:
        with_shadow.close()
        without.close()
    assert compare_boards(board_on, board_off) == []
    assert board_on["closed_trades"], "fixture slice must actually trade"
    on_ids = set(with_shadow.summary()["analysts"])
    off_ids = set(without.summary()["analysts"])
    assert "rng60_atr" in on_ids and "gex" in on_ids
    assert "rng60_atr" not in off_ids
    votes = with_shadow.audit.rows("ANALYST_VOTE", limit=5000)
    shadow_votes = [r for r in votes if (r["payload"].get("metadata") or {}).get("shadow")]
    assert shadow_votes
    assert all(r["payload"].get("signal") == "ABSTAIN" for r in shadow_votes)
    assert "value" in shadow_votes[0]["payload"] and "flag" in shadow_votes[0]["payload"]


def test_model_log_is_written_only_through_a_session_sink(tmp_path):
    from desk_ml.paper_scalp import LOG_JSONL_NAME, _MODEL_LOGS, append_model_log
    from desk_ml.reliability import ModelLogSink

    append_model_log(tmp_path, {"event": "CLOSE", "trade_id": "t"})  # no write=True replay: no sink
    assert not (tmp_path / "data" / "recon" / LOG_JSONL_NAME).exists()
    assert not (tmp_path / "data" / "recon" / "model_log").exists()
    sink = ModelLogSink(tmp_path, "2026-09-10")
    token = _MODEL_LOGS.set(sink)
    try:
        sink.set_tick("NIFTY", 1_000)
        append_model_log(tmp_path, {"event": "CLOSE", "trade_id": "t"})
        sink.flush()
    finally:
        _MODEL_LOGS.reset(token)
    assert "CLOSE" in sink.path.read_text(encoding="utf-8")
    assert not (tmp_path / "data" / "recon" / LOG_JSONL_NAME).exists()

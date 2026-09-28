"""V2-20b Round 8 shadow specs. One test per acceptance bullet. Synthetic only."""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

import yaml
from contracts.clock import IST

from strategies.api import Bar, SessionContext
from strategies.forward.eval import evaluate_session
from strategies.forward.spec import (
    SpecRefused,
    compute_lock_digest,
    load_lock,
    load_spec,
    plugin_source,
    verify_lock,
)
from strategies.plugins.r8_e1_coil_side import CoilSidePlugin
from strategies.plugins.r8_e1_coil_side import strategy as e1
from strategies.plugins.r8_e2_p5_hv import P5HvPlugin
from strategies.plugins.r8_e2_p5_hv import strategy as e2
from strategies.plugins.r8_e3_hv_gate import HvGatePlugin
from strategies.plugins.r8_e3_hv_gate import strategy as e3
from strategies.registry import RegistryEntry, load_registry
from strategies.runtime import StrategyRuntimeError, load_strategy

ROOT = Path(__file__).resolve().parents[3]
SPECS = ROOT / "config" / "v2" / "forward" / "specs"
LOCK = ROOT / "config" / "v2" / "forward" / "prereg.lock"
SESSION = "2026-09-28"
ATM = "NSE_FNO:NIFTY:2026-09-29:24500:CE"
ITM100 = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
PLUGINS = (e1, e2, e3)

TEST_E1 = {
    "prereg_status": "TEST",
    "sha256": "test-e1-not-lab",
    "weights": {"range_over_em": 1.0},
    "intercept": 0.0,
    "q90": 0.8,
    "q10": 0.2,
}


class _View:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None:
        del instrument, tf
        return self.values.get(name)


def _bar(hh: int, mm: int, close: float = 24500.0) -> Bar:
    ts = datetime(2026, 9, 28, hh, mm, tzinfo=IST).isoformat()
    return Bar(
        instrument_id="NSE_IDX:NIFTY",
        open=close,
        high=close + 5,
        low=close - 5,
        close=close,
        volume=1000,
        timestamp=ts,
        available_ts=ts,
    )


def _e1_view(*, lean: float, coil: str = "c1") -> _View:
    return _View(
        {
            "coil_active": True,
            "coil_age_min": 7.0,
            "coil_id": coil,
            "box_high": 24620.0,
            "box_low": 24400.0,
            "spot": 24500.0,
            "em30": 27.0,
            "range_over_em": lean,
            "volume_trend": 0.0,
            "oi_ce_chg_lagged": 0.0,
            "oi_pe_chg_lagged": 0.0,
            "oi_pc_chg_lagged": 0.0,
            "twap_slope": 0.0,
            "tod_frac": 0.4,
            "prior_trend": 0.0,
            "dte": 3.0,
            "oi_ce_chg": 99.0,
            "hari_0959": 0.99,
        }
    )


def _e2_hist(top: bool) -> list[float]:
    return ([0.001] * 200 + [0.012] * 50) if top else ([0.012] * 200 + [0.001] * 50)


def _e2_view(*, top: bool, poison: float = 0.99) -> _View:
    return _View(
        {
            "har_forecast_preopen": 0.02 if top else 0.001,
            "har_trailing_250": _e2_hist(top),
            "session_open": 24600.0,
            "prev_close": 24500.0,
            "atr14_daily": 200.0,
            "em30": 40.0,
            "dte": 3.0,
            "hari_0959": poison,
            "hari_intraday": poison,
        }
    )


def _row(inst: str, hh: int, mm: int, ltp: float, bid: float, ask: float, bucket: str) -> str:
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
            "exchange_ts": datetime(2026, 9, 28, hh, mm, tzinfo=IST).isoformat(),
        }
    )


def _synth_tape(path: Path) -> Path:
    lines = [
        _row(ATM, 9, 30, 100.0, 99.80, 100.20, "ATM"),
        _row(ITM100, 9, 30, 150.0, 149.70, 150.30, "ITM100"),
        _row(ATM, 10, 1, 102.0, 101.80, 102.20, "ATM"),
        _row(ITM100, 10, 1, 152.0, 151.70, 152.30, "ITM100"),
        _row(ATM, 15, 15, 101.0, 100.80, 101.20, "ATM"),
        _row(ITM100, 15, 15, 151.0, 150.70, 151.30, "ITM100"),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_plugin_refuses_to_load_if_params_hash_differs_from_preregistered() -> None:
    registry = load_registry()
    for sid in ("R8-E1-COIL-SIDE", "R8-E2-P5-HV", "R8-E3-HV-GATE"):
        row = registry[sid]
        broken = {
            sid: RegistryEntry(
                strategy_id=sid,
                module_path=row.module_path,
                version=row.version,
                params_hash="deadbeefdeadbeef",
                stage="shadow",
            )
        }
        try:
            load_strategy(sid, broken)
        except StrategyRuntimeError as exc:
            assert "params hash differs from the preregistered one" in str(exc)
        else:
            raise AssertionError(f"{sid} loaded with a bad params hash")


def test_plugin_refuses_to_load_until_lab_hash_recorded_pending_lab() -> None:
    registry = load_registry()
    for sid in ("R8-E1-COIL-SIDE", "R8-E2-P5-HV", "R8-E3-HV-GATE"):
        try:
            load_strategy(sid, registry)
        except StrategyRuntimeError as exc:
            assert "PENDING_LAB" in str(exc)
            assert "refuses to load" in str(exc)
        else:
            raise AssertionError(f"{sid} loaded without a lab hash")


def test_random_cut_causality_on_every_plugin() -> None:
    rng = random.Random(8)
    coil = CoilSidePlugin(TEST_E1)
    coil.on_session_start(SessionContext(SESSION, "IN_INDEX_OPT", {}))
    p5 = P5HvPlugin()
    p5.on_session_start(SessionContext(SESSION, "IN_INDEX_OPT", {}))
    gate = HvGatePlugin()
    gate.on_session_start(
        SessionContext(
            SESSION,
            "IN_INDEX_OPT",
            {"har_forecast_preopen": 0.001, "har_trailing_250": _e2_hist(False)},
        )
    )

    series: list[tuple[Bar, _View, _View]] = []
    for i in range(40):
        hh, mm = 10, i
        if i == 0:
            series.append((_bar(9, 30), _e1_view(lean=3.0), _e2_view(top=True)))
        series.append((_bar(hh, mm), _e1_view(lean=3.0 if i % 7 == 0 else 0.0), _e2_view(top=True)))

    def run(prefix: list[tuple[Bar, _View, _View]]) -> tuple[list[str], list[str], bool]:
        a = CoilSidePlugin(TEST_E1)
        a.on_session_start(SessionContext(SESSION, "IN_INDEX_OPT", {}))
        b = P5HvPlugin()
        b.on_session_start(SessionContext(SESSION, "IN_INDEX_OPT", {}))
        c = HvGatePlugin()
        c.on_session_start(
            SessionContext(
                SESSION,
                "IN_INDEX_OPT",
                {"har_forecast_preopen": 0.001, "har_trailing_250": _e2_hist(False)},
            )
        )
        e1s: list[str] = []
        e2s: list[str] = []
        for bar, v1, v2 in prefix:
            e1s.append(",".join(s.side for s in a.on_bar(bar, v1)))
            e2s.append(",".join(s.side for s in b.on_bar(bar, v2)))
            assert c.on_bar(bar, _View({"hari_0959": 0.99})) == []
        return e1s, e2s, c.flag()

    full = run(series)
    cut = rng.randint(5, 20)
    assert run(series[:cut]) == (full[0][:cut], full[1][:cut], full[2])
    assert gate.flag() is True
    del coil, p5


def test_e2_p5_hv_ignores_0959_hari_lookahead() -> None:
    ctx = SessionContext(SESSION, "IN_INDEX_OPT", {})
    bar = _bar(9, 30)
    good = P5HvPlugin()
    good.on_session_start(ctx)
    sigs = good.on_bar(bar, _e2_view(top=True, poison=0.99))
    assert [s.side for s in sigs] == ["PE"]
    assert "hari_0959" not in sigs[0].features
    quiet = P5HvPlugin()
    quiet.on_session_start(ctx)
    assert quiet.on_bar(bar, _e2_view(top=False, poison=0.99)) == []


def test_each_spec_runs_through_v2_20a_forward_eval_on_synthetic_day(tmp_path: Path) -> None:
    tape = _synth_tape(tmp_path / "day.jsonl")
    lock = load_lock(LOCK)
    lines = []
    for name in ("R8-E1-COIL-SIDE", "R8-E2-P5-HV", "R8-E3-HV-GATE"):
        spec = load_spec(SPECS / f"{name}.yaml")
        assert spec.stage == "shadow"
        assert spec.raw.get("prereg_status") == "PENDING_LAB"
        assert verify_lock(spec, lock)
        report, _trades = evaluate_session(spec, tape, SESSION, lock=lock)
        assert report.spec_id == name
        assert report.stage == "shadow"
        assert report.kernel_envelopes >= 0
        lines.append(f"{name} state={report.state} n={report.n} stage={report.stage}")
        body = yaml.safe_load((SPECS / f"{name}.yaml").read_text(encoding="utf-8"))
        body["signals"] = [
            {
                "signal_id": f"sg_{name}_synth",
                "decision_ts": datetime(2026, 9, 28, 10, 1, tzinfo=IST).isoformat(),
                "exit_ts": datetime(2026, 9, 28, 15, 15, tzinfo=IST).isoformat(),
                "side": "CE",
                "underlying": "NIFTY",
                "lots": 1,
                "lot_size": 65,
                "chosen": "ITM100",
                "instrument_id": ITM100,
                "alternatives": {"ATM": ATM, "ITM100": ITM100, "ITM200": ITM100},
            }
        ]
        tmp = tmp_path / f"{name}.yaml"
        tmp.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
        priced = load_spec(tmp)
        digest = compute_lock_digest(priced.raw, plugin_source(priced.plugin), priced.coefficients)
        priced_lock = {
            "cumulative_trials": 4621,
            "specs": {priced.spec_id: {"sha256": digest, "exit_sha256": ""}},
        }
        priced_rep, priced_trades = evaluate_session(priced, tape, SESSION, lock=priced_lock)
        assert priced_rep.stage == "shadow"
        assert priced_rep.state != ""
        lines.append(f"{name}+signal state={priced_rep.state} trades={len(priced_trades)}")
        spec.raw["coefficients"] = {"invented": 1}
        try:
            verify_lock(spec, lock)
        except SpecRefused as exc:
            assert "hash mismatch" in str(exc)
        else:
            raise AssertionError(f"{name} accepted invented coefficients")
    out = tmp_path / "v2_20b_demo.log"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert out.read_text(encoding="utf-8").count("R8-") >= 3


def test_no_plugin_leaves_shadow() -> None:
    for plugin in PLUGINS:
        assert plugin.meta.stage == "shadow"
        assert plugin.on_session_end()["stage"] == "shadow"
    for name in ("R8-E1-COIL-SIDE", "R8-E2-P5-HV", "R8-E3-HV-GATE"):
        assert load_spec(SPECS / f"{name}.yaml").stage == "shadow"


def test_nothing_can_place_orders() -> None:
    banned = ("DhanBroker", "place_order", "submit_order", "place_live")
    for plugin in PLUGINS:
        rel = plugin.__class__.__module__.replace(".", "/") + ".py"
        text = (ROOT / "packages" / "strategies" / "src" / rel).read_text(encoding="utf-8")
        for token in banned:
            assert token not in text
        assert not hasattr(plugin, "place_order")
        assert not hasattr(plugin, "broker")
    e4_py = ROOT / "packages/strategies/src/strategies/plugins/r8_e4_quiet_expiry.py"
    assert not e4_py.exists()
    assert not (SPECS / "R8-E4-QUIET-EXPIRY.yaml").exists()


def test_e4_stays_out() -> None:
    assert list(SPECS.glob("*E4*")) == []
    registry = load_registry()
    assert "R8-E4-QUIET-EXPIRY" not in registry

"""V2-06 strategy runtime acceptance tests. Synthetic fixtures only; no secrets."""

from __future__ import annotations

import random
import sys
import threading
import types
from datetime import date
from pathlib import Path

import pytest
from contracts.payloads import CatastrophicStop, ExitPlan, Level, TimeStop

from strategies.api import Bar, EntryPolicy, SessionContext, StrategyMeta
from strategies.onboarding import check_registry
from strategies.onboarding import main as onboarding_main
from strategies.params_hash import (
    ROUND11_DEFAULTS_SHA256,
    ExitPlanLoadError,
    compute_params_hash,
    config_hash,
    exit_plan_hash,
    load_exit_defaults,
    resolve_exit_plan,
)
from strategies.plugins.test_cross import CrossPlugin
from strategies.plugins.test_cross import strategy as test_cross
from strategies.registry import (
    RegistryEntry,
    basket_for,
    load_basket,
    load_basket_json,
    load_registry,
)
from strategies.runtime import (
    SessionRuntime,
    StrategyRuntimeError,
    StrategyTimeoutError,
    disable_strategy,
    load_strategy,
    strategy_call_budget,
)

FIXTURE_DEFAULTS = Path(__file__).parent / "fixtures" / "exit_defaults_main.yaml"


def _meta(**overrides: object) -> StrategyMeta:
    base: dict[str, object] = {
        "strategy_id": "TEST-A",
        "version": "1.0.0",
        "params_hash": "abc123abc123abcd",
        "markets": ("IN_INDEX_OPT",),
        "underlyings": ("NIFTY",),
        "inputs": ("bars:1m",),
        "features": ("ema_5",),
        "stage": "shadow",
        "entry_policy": EntryPolicy(),
        "legacy_logic_from": (),
    }
    base.update(overrides)
    return StrategyMeta(**base)  # type: ignore[arg-type]


def _install_plugin(module_path: str, instance: object) -> None:
    module = types.ModuleType(module_path)
    module.strategy = instance  # type: ignore[attr-defined]
    sys.modules[module_path] = module


def _plugin(meta: StrategyMeta, exit_plan: ExitPlan | object | None = "default") -> object:
    class _P:
        def __init__(self) -> None:
            self.meta = meta
            if exit_plan == "default":
                self.exit_plan = ExitPlan(
                    catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0))
                )
            else:
                self.exit_plan = exit_plan  # type: ignore[assignment]

    return _P()


def _bar(n: int = 0) -> Bar:
    return Bar(
        instrument_id="NSE_IDX:NIFTY",
        open=24500.0,
        high=24550.0,
        low=24480.0,
        close=24520.0,
        volume=1000,
        timestamp=f"2026-09-27T09:2{n}:00+05:30",
        available_ts=f"2026-09-27T09:2{n}:00+05:30",
    )


class _View:
    def __init__(self, values: dict[str, float]) -> None:
        self.values = values

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None:
        del instrument, tf
        return self.values.get(name)


class TestParamsHash:
    def test_changing_exit_field_changes_hash(self) -> None:
        exit1 = ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)),
            flat_by_ist="15:15",
        )
        exit2 = ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)),
            flat_by_ist="15:00",
        )
        exit3 = ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=25000.0)),
            flat_by_ist="15:15",
        )
        assert exit_plan_hash(exit1) != exit_plan_hash(exit2)
        assert exit_plan_hash(exit1) != exit_plan_hash(exit3)

    def test_time_stops_in_hash(self) -> None:
        exit1 = ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)),
            time_stops=(),
        )
        exit2 = ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)),
            time_stops=(TimeStop(after_s=180, when="always"),),
        )
        assert exit_plan_hash(exit1) != exit_plan_hash(exit2)

    def test_params_and_config_hash_reg13a(self) -> None:
        plan = ExitPlan(catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)))
        params = {"coef": 1.5, "exit_plan": plan}
        h0 = compute_params_hash(params)
        assert compute_params_hash(params) == h0
        assert len(h0) == 16
        edited = ExitPlan(catastrophic=CatastrophicStop(level=Level(kind="premium", price=29000.0)))
        assert compute_params_hash({"coef": 1.5, "exit_plan": edited}) != h0
        defaults, digest = load_exit_defaults(FIXTURE_DEFAULTS)
        assert digest == ROUND11_DEFAULTS_SHA256
        c0 = config_hash(exit_defaults=defaults)
        bumped = dict(defaults)
        bumped["catastrophic"] = {"max_loss": 29999}
        assert config_hash(exit_defaults=bumped) != c0


class TestExitDefaults:
    def test_load_main_defaults_and_inherit_catastrophic(self) -> None:
        defaults, digest = load_exit_defaults(FIXTURE_DEFAULTS)
        assert defaults["catastrophic"]["max_loss"] == 30000
        assert defaults["structural"]["enabled"] is True
        assert defaults["atr"] is None
        plan = resolve_exit_plan({}, defaults=defaults, defaults_sha256=digest)
        assert plan.catastrophic.level.price == 30000.0
        assert plan.defaults_from == f"exit_defaults@{digest}"

    def test_reg18d_refuses_plan_without_catastrophic(self) -> None:
        with pytest.raises(ExitPlanLoadError, match="REG-18d"):
            resolve_exit_plan({})


class TestRegistry:
    def test_load_registry_from_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "registry.yaml"
        path.write_text(
            """
strategies:
  - strategy_id: "TEST-A"
    module_path: "test.plugin_a"
    version: "1.0.0"
    params_hash: "abc123"
    stage: "shadow"
    legacy_logic_from: []
  - strategy_id: "TEST-B"
    module_path: "test.plugin_b"
    version: "2.1.0"
    params_hash: "def456"
    stage: "paper"
"""
        )
        registry = load_registry(path)
        assert set(registry) == {"TEST-A", "TEST-B"}
        assert registry["TEST-A"].module_path == "test.plugin_a"
        assert registry["TEST-A"].legacy_logic_from == ()

    def test_load_registry_missing_file_warns(self, tmp_path: Path) -> None:
        with pytest.warns(UserWarning, match="Registry file not found"):
            assert load_registry(tmp_path / "missing.yaml") == {}

    def test_load_registry_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "registry.yaml"
        path.write_text("")
        assert load_registry(path) == {}


class TestBasket:
    def test_load_basket_from_yaml(self, tmp_path: Path) -> None:
        (tmp_path / "2026-09-27.yaml").write_text(
            """
session: "2026-09-27"
market: "IN_INDEX_OPT"
entries:
  - strategy_id: "TEST-A"
    underlyings: ["NIFTY", "SENSEX"]
    weight: 1.5
    max_lots: 10
    stage: "shadow"
"""
        )
        basket = load_basket(date(2026, 9, 27), "IN_INDEX_OPT", tmp_path)
        assert basket is not None
        assert basket.entries[0].underlyings == ("NIFTY", "SENSEX")
        assert basket_for(date(2026, 9, 27), "IN_INDEX_OPT", tmp_path) == basket

    def test_load_basket_missing_file_returns_none(self, tmp_path: Path) -> None:
        with pytest.warns(UserWarning, match="Basket file not found"):
            assert load_basket(date(2026, 9, 27), "IN_INDEX_OPT", tmp_path) is None

    def test_load_basket_session_mismatch_warns(self, tmp_path: Path) -> None:
        (tmp_path / "2026-09-27.yaml").write_text(
            'session: "2026-09-28"\nmarket: "IN_INDEX_OPT"\nentries: []\n'
        )
        with pytest.warns(UserWarning, match="session mismatch"):
            assert load_basket(date(2026, 9, 27), "IN_INDEX_OPT", tmp_path) is None

    def test_basket_hash_deterministic(self, tmp_path: Path) -> None:
        (tmp_path / "2026-09-27.yaml").write_text(
            """
session: "2026-09-27"
market: "IN_INDEX_OPT"
entries:
  - strategy_id: "TEST-A"
    underlyings: ["NIFTY"]
    weight: 1.0
    max_lots: 10
    stage: "shadow"
"""
        )
        a = load_basket(date(2026, 9, 27), "IN_INDEX_OPT", tmp_path)
        b = load_basket(date(2026, 9, 27), "IN_INDEX_OPT", tmp_path)
        assert a is not None and b is not None
        assert a.basket_hash == b.basket_hash

    def test_basket_json_adapter_k6(self, tmp_path: Path) -> None:
        (tmp_path / "basket_india.json").write_text(
            '{"market":"IN_INDEX_OPT","entries":['
            '{"strategy_id":"TEST-CROSS","underlyings":["NIFTY"],'
            '"weight":1.0,"max_lots":2,"stage":"shadow"}]}'
        )
        basket = load_basket_json(date(2026, 9, 27), "IN_INDEX_OPT", config_dir=tmp_path)
        assert basket is not None
        assert basket.source.startswith("json:")
        assert basket.entries[0].strategy_id == "TEST-CROSS"


class TestStrategyLoader:
    def test_load_strategy_validates_meta_matches_registry(self) -> None:
        meta = _meta(version="9.9.9")
        _install_plugin("tests.plugins.mismatch", _plugin(meta))
        registry = {
            "TEST-A": RegistryEntry(
                strategy_id="TEST-A",
                module_path="tests.plugins.mismatch",
                version="1.0.0",
                params_hash=meta.params_hash,
                stage="shadow",
            )
        }
        with pytest.raises(StrategyRuntimeError, match="version mismatch"):
            load_strategy("TEST-A", registry)

    def test_load_strategy_checks_features(self) -> None:
        meta = _meta(features=("ema_5", "missing_feature"))
        _install_plugin("tests.plugins.features", _plugin(meta))
        registry = {
            "TEST-A": RegistryEntry(
                strategy_id="TEST-A",
                module_path="tests.plugins.features",
                version="1.0.0",
                params_hash=meta.params_hash,
                stage="shadow",
            )
        }
        with pytest.raises(StrategyRuntimeError, match="features not available"):
            load_strategy("TEST-A", registry, available_features={"ema_5"})

    def test_load_strategy_refuses_fx_spot_in_india_basket(self) -> None:
        meta = _meta(markets=("FX_SPOT",))
        _install_plugin("tests.plugins.fx", _plugin(meta))
        registry = {
            "TEST-A": RegistryEntry(
                strategy_id="TEST-A",
                module_path="tests.plugins.fx",
                version="1.0.0",
                params_hash=meta.params_hash,
                stage="shadow",
            )
        }
        with pytest.raises(StrategyRuntimeError, match="refuses to load into IN_INDEX_OPT"):
            load_strategy("TEST-A", registry, required_market="IN_INDEX_OPT")


class TestPluginIsolation:
    def test_raising_plugin_disabled_for_session(self) -> None:
        good = CrossPlugin()
        good.on_session_start(SessionContext("2026-09-27", "IN_INDEX_OPT", {}))

        class _Boom:
            def on_bar(self, bar: Bar, view: _View) -> list[object]:
                del bar, view
                raise RuntimeError("planted")

        from strategies.runtime import LoadedStrategy

        session = SessionRuntime(
            loaded={
                "GOOD": LoadedStrategy(strategy=good, registry_entry=None, enabled=True),
                "BAD": LoadedStrategy(strategy=_Boom(), registry_entry=None, enabled=True),
            }
        )
        session.on_bar(_bar(0), _View({"ema_5": 90.0, "ema_20": 95.0}))
        session.on_bar(_bar(1), _View({"ema_5": 100.0, "ema_20": 95.0}))
        assert session.loaded["BAD"].enabled is False
        assert session.loaded["GOOD"].enabled is True
        assert any(s.side == "CE" for s in session.signals)

    def test_over_budget_plugin_disabled(self) -> None:
        with pytest.raises(StrategyTimeoutError), strategy_call_budget(0.01):
            import time

            time.sleep(0.05)

    def test_non_list_return_disables_only_that_strategy(self) -> None:
        good = CrossPlugin()
        good.on_session_start(SessionContext("2026-09-27", "IN_INDEX_OPT", {}))

        class _BadType:
            def on_bar(self, bar: Bar, view: _View) -> object:
                del bar, view
                return 7

        from strategies.runtime import LoadedStrategy

        session = SessionRuntime(
            loaded={
                "GOOD": LoadedStrategy(strategy=good, registry_entry=None, enabled=True),
                "BAD": LoadedStrategy(strategy=_BadType(), registry_entry=None, enabled=True),
            }
        )
        session.on_bar(_bar(0), _View({"ema_5": 90.0, "ema_20": 95.0}))
        session.on_bar(_bar(1), _View({"ema_5": 100.0, "ema_20": 95.0}))
        assert session.loaded["BAD"].enabled is False
        assert "TypeError" in (session.loaded["BAD"].disabled_reason or "")
        assert session.loaded["GOOD"].enabled is True
        assert any(s.side == "CE" for s in session.signals)

    def test_systemexit_and_keyboardinterrupt_are_isolated(self) -> None:
        good = CrossPlugin()
        good.on_session_start(SessionContext("2026-09-27", "IN_INDEX_OPT", {}))

        class _Exit:
            def on_bar(self, bar: Bar, view: _View) -> list[object]:
                del bar, view
                raise SystemExit("planted exit")

        class _Interrupt:
            def on_bar(self, bar: Bar, view: _View) -> list[object]:
                del bar, view
                raise KeyboardInterrupt("planted interrupt")

        from strategies.runtime import LoadedStrategy

        session = SessionRuntime(
            loaded={
                "GOOD": LoadedStrategy(strategy=good, registry_entry=None, enabled=True),
                "EXIT": LoadedStrategy(strategy=_Exit(), registry_entry=None, enabled=True),
                "INT": LoadedStrategy(strategy=_Interrupt(), registry_entry=None, enabled=True),
            }
        )
        session.on_bar(_bar(0), _View({"ema_5": 90.0, "ema_20": 95.0}))
        session.on_bar(_bar(1), _View({"ema_5": 100.0, "ema_20": 95.0}))
        assert session.loaded["EXIT"].enabled is False
        assert session.loaded["INT"].enabled is False
        assert session.loaded["GOOD"].enabled is True
        assert any(s.side == "CE" for s in session.signals)

    def test_off_main_thread_does_not_disable_healthy_strategies(self) -> None:
        good = CrossPlugin()
        good.on_session_start(SessionContext("2026-09-27", "IN_INDEX_OPT", {}))
        from strategies.runtime import LoadedStrategy

        session = SessionRuntime(
            loaded={"GOOD": LoadedStrategy(strategy=good, registry_entry=None, enabled=True)}
        )
        errors: list[BaseException] = []

        def _run() -> None:
            try:
                session.on_bar(_bar(0), _View({"ema_5": 90.0, "ema_20": 95.0}))
                session.on_bar(_bar(1), _View({"ema_5": 100.0, "ema_20": 95.0}))
            except BaseException as exc:
                errors.append(exc)

        worker = threading.Thread(target=_run)
        worker.start()
        worker.join(2.0)
        assert not worker.is_alive()
        assert errors == []
        assert session.loaded["GOOD"].enabled is True
        assert any(s.side == "CE" for s in session.signals)

    def test_non_shadow_without_forward_spec_does_not_emit(self) -> None:
        class _Paper:
            meta = _meta(strategy_id="PAPER-X", stage="paper")

            def on_bar(self, bar: Bar, view: _View) -> list[object]:
                del bar, view
                return [object()]

        from strategies.runtime import LoadedStrategy

        entry = RegistryEntry(
            strategy_id="PAPER-X",
            module_path="tests.plugins.paper_x",
            version="1.0.0",
            params_hash="abc123abc123abcd",
            stage="paper",
        )
        session = SessionRuntime(
            loaded={
                "PAPER-X": LoadedStrategy(strategy=_Paper(), registry_entry=entry, enabled=True)
            }
        )
        out = session.on_bar(_bar(0), _View({}))
        assert out == []
        assert session.signals == []
        assert session.loaded["PAPER-X"].enabled is True

    def test_fixture_basket_is_not_in_real_config_dir(self) -> None:
        real = Path("config/v2/baskets/2026-09-27.yaml")
        fixture = Path(__file__).parent / "fixtures" / "2026-09-27.yaml"
        assert not real.is_file()
        assert fixture.is_file()
        basket = load_basket(date(2026, 9, 27), "IN_INDEX_OPT", fixture.parent)
        assert basket is not None
        assert basket.entries[0].strategy_id == "TEST-CROSS"


class TestCausality:
    def test_random_cut_causality_on_signals(self) -> None:
        rng = random.Random(7)
        series: list[tuple[float, float]] = []
        fast, slow = 100.0, 100.0
        for _ in range(40):
            fast += rng.uniform(-2.0, 2.0)
            slow += rng.uniform(-0.4, 0.4)
            series.append((fast, slow))

        def run(prefix: list[tuple[float, float]]) -> list[tuple[str, ...]]:
            plugin = CrossPlugin()
            plugin.on_session_start(SessionContext("2026-09-27", "IN_INDEX_OPT", {}))
            out: list[tuple[str, ...]] = []
            for i, (f, s) in enumerate(prefix):
                sigs = plugin.on_bar(_bar(i % 9), _View({"ema_5": f, "ema_20": s}))
                out.append(tuple(sig.side for sig in sigs))
            return out

        full = run(series)
        cut = rng.randint(8, 30)
        assert run(series[:cut]) == full[:cut]


class TestTestCrossPlugin:
    def test_test_cross_meta(self) -> None:
        assert test_cross.meta.strategy_id == "TEST-CROSS"
        assert test_cross.meta.stage == "shadow"
        assert "IN_INDEX_OPT" in test_cross.meta.markets
        assert test_cross.meta.entry_policy.mode == "chase"
        assert test_cross.meta.legacy_logic_from == ()
        assert test_cross.exit_plan.catastrophic.level.price == 30000.0

    def test_test_cross_never_live(self) -> None:
        assert test_cross.meta.stage == "shadow"

    def test_test_cross_emits_signals(self) -> None:
        plugin = CrossPlugin()
        plugin.on_session_start(SessionContext("2026-09-27", "IN_INDEX_OPT", {}))
        assert plugin.on_bar(_bar(0), _View({"ema_5": 90.0, "ema_20": 95.0})) == []
        signals = plugin.on_bar(_bar(1), _View({"ema_5": 100.0, "ema_20": 95.0}))
        assert len(signals) == 1
        assert signals[0].side == "CE"


class TestCIOnboardingCheck:
    def test_strategy_without_catastrophic_stop_refuses_to_load(self) -> None:
        meta = _meta()
        _install_plugin("tests.plugins.no_stop", _plugin(meta, exit_plan=None))
        registry = {
            "TEST-A": RegistryEntry(
                strategy_id="TEST-A",
                module_path="tests.plugins.no_stop",
                version="1.0.0",
                params_hash=meta.params_hash,
                stage="shadow",
            )
        }
        with pytest.raises(StrategyRuntimeError, match="REG-18d"):
            load_strategy("TEST-A", registry)

    def test_k9_registry_entries_pass(self) -> None:
        from strategies.plugins.test_cross import PARAMS_HASH

        registry = {
            "TEST-CROSS": RegistryEntry(
                strategy_id="TEST-CROSS",
                module_path="strategies.plugins.test_cross",
                version="1.0.0",
                params_hash=PARAMS_HASH,
                stage="shadow",
            )
        }
        assert check_registry(registry, collected_nodeids=[]) == []
        assert onboarding_main([]) == 0


def test_disable_strategy_keeps_others() -> None:
    from strategies.runtime import LoadedStrategy

    loaded = {
        "GOOD": LoadedStrategy(strategy=object(), registry_entry=None, enabled=True),
        "BAD": LoadedStrategy(strategy=object(), registry_entry=None, enabled=True),
    }
    disable_strategy(loaded, "BAD", "RAISED_EXCEPTION")
    assert loaded["BAD"].enabled is False
    assert loaded["GOOD"].enabled is True

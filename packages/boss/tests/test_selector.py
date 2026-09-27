"""V2-07 boss selector acceptance. Synthetic fixtures only; no secrets, no broker."""

from __future__ import annotations

import ast
import random
from datetime import datetime
from pathlib import Path

import pytest
from contracts.clock import IST, SimClock
from contracts.instruments import India
from contracts.payloads import CatastrophicStop, ExitPlan, Level, StrikeChoice, StrikeQuote
from strategies.api import Signal
from strategies.registry import Basket, BasketEntry

from boss.selector import (
    HOLD_ATM_EXPIRY,
    HOLD_BELOW_MIN_LOTS,
    HOLD_CONFLICT,
    HOLD_EVENT_DAY,
    HOLD_FEED_DOWN,
    HOLD_FEED_STALE,
    HOLD_FOUNDER_PAUSE,
    HOLD_FOUNDER_STOP,
    HOLD_NEWS,
    HOLD_NOT_IN_BASKET,
    HOLD_RECON,
    HOLD_STAGE,
    BarContext,
    BasketFrozenError,
    BossSelector,
    EngineConfig,
    LookAheadError,
    SessionBasketGate,
    caplots,
    evaluate_holds,
    load_engine_config,
    size_lots,
    volsize,
)

REPO_ENGINE = Path("config/v2/engine.yaml")
SELECTOR_SRC = Path("packages/boss/src/boss/selector.py")


def _ist(hour: int, minute: int, day: int = 28) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=IST)


def _choice(rule: str = "ITM100") -> StrikeChoice:
    quote = StrikeQuote(
        rule=rule,
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        bid=140.0,
        ask=141.0,
        mid=140.5,
        spread=1.0,
        quote_age_ms=200,
        est_delta=0.65,
        est_round_trip_pts=2.0,
    )
    return StrikeChoice(
        chosen=rule,
        reason="TEST_ROUTER",
        rule_version="router-test",
        alternatives=(quote,),
    )


def _plan() -> ExitPlan:
    return ExitPlan(catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)))


def _signal(
    *,
    sid: str = "PAPER-A",
    signal_id: str = "sg_a",
    side: str = "CE",
    ts: datetime | None = None,
    rule: str = "ITM100",
) -> Signal:
    when = ts or _ist(10, 5)
    return Signal(
        signal_id=signal_id,
        strategy_id=sid,
        underlying="NIFTY",
        side=side,
        strike_rule="ROUTER",
        strike_choice=_choice(rule),
        decision_ts=when.isoformat(),
        confidence=0.6,
        exit_plan=_plan(),
        reasons=("TEST",),
        features={"ema_5": 1.0},
    )


def _basket(*rows: tuple[str, float, int]) -> SessionBasketGate:
    entries = tuple(
        BasketEntry(
            strategy_id=sid,
            underlyings=("NIFTY",),
            weight=weight,
            max_lots=max_lots,
            stage="paper",
        )
        for sid, weight, max_lots in rows
    )
    payload = Basket(
        session="2026-09-28",
        market="IN_INDEX_OPT",
        entries=entries,
        source="test",
        basket_hash="testhash07",
    )
    return SessionBasketGate(basket=payload)


def _cfg() -> EngineConfig:
    return load_engine_config(REPO_ENGINE)


def _selector(
    clock: SimClock,
    basket: SessionBasketGate | None = None,
    cfg: EngineConfig | None = None,
) -> BossSelector:
    return BossSelector(
        clock=clock,
        config=cfg or _cfg(),
        basket=basket or _basket(("PAPER-A", 1.0, 25), ("PAPER-B", 1.0, 25)),
    )


def _ctx(
    now: datetime,
    **overrides: object,
) -> BarContext:
    base: dict[str, object] = {
        "underlying": "NIFTY",
        "bar_ts": now,
        "available_ts": now,
        "feed_status": "UP",
        "em30": 40.294117647058826,
        "delta": 0.5,
        "stop": 50.0,
        "regime_label": "trend_up",
        "signal_stages": {"PAPER-A": "paper", "PAPER-B": "paper", "SHADOW-X": "shadow"},
    }
    base.update(overrides)
    return BarContext(**base)  # type: ignore[arg-type]


class TestEngineConfig:
    def test_loads_repo_yaml(self) -> None:
        cfg = _cfg()
        assert cfg.timezone == IST
        assert cfg.min_lots == 2
        assert cfg.volsize_ref_em30 == 27.4
        assert cfg.regime_mode == "shadow"
        assert [w.id for w in cfg.windows] == ["OPEN_NO_BUY", "LATE_ENTRY"]
        assert cfg.paper_stages == ("paper", "live_eligible")


class TestHoldTable:
    """One row per hold reason (V2-07 acceptance)."""

    @pytest.mark.parametrize(
        ("kwargs", "expect"),
        [
            ({"founder_pause": True}, HOLD_FOUNDER_PAUSE),
            ({"founder_stop": True}, HOLD_FOUNDER_STOP),
            ({"event_day": True}, HOLD_EVENT_DAY),
            ({"news_hold": True}, HOLD_NEWS),
            ({"recon_ok": False}, HOLD_RECON),
            ({"feed_status": "DOWN"}, HOLD_FEED_DOWN),
            ({"feed_status": "STALE"}, HOLD_FEED_STALE),
        ],
    )
    def test_state_holds(self, kwargs: dict[str, object], expect: str) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        out = sel.decide([_signal()], _ctx(clock.now(), **kwargs))
        assert out.decisions[0].decision == "HOLD"
        assert expect in list(out.decisions[0].holds)

    def test_open_no_buy_window(self) -> None:
        clock = SimClock(_ist(9, 20))
        sel = _selector(clock)
        out = sel.decide([_signal(ts=_ist(9, 20))], _ctx(clock.now()))
        assert out.decisions[0].decision == "HOLD"
        assert "OPEN_NO_BUY" in list(out.decisions[0].holds)

    def test_open_window_except_spec_prices_it(self, tmp_path: Path) -> None:
        path = tmp_path / "engine.yaml"
        path.write_text(
            REPO_ENGINE.read_text(encoding="utf-8").replace(
                "except_specs: []",
                'except_specs: ["PAPER-A"]',
                1,
            ),
            encoding="utf-8",
        )
        clock = SimClock(_ist(9, 20))
        sel = _selector(clock, cfg=load_engine_config(path))
        out = sel.decide([_signal(ts=_ist(9, 20))], _ctx(clock.now()))
        assert out.decisions[0].decision == "ENTER"
        assert "OPEN_NO_BUY" not in list(out.decisions[0].holds)

    def test_late_entry_window(self) -> None:
        clock = SimClock(_ist(14, 50))
        sel = _selector(clock)
        out = sel.decide([_signal(ts=_ist(14, 50))], _ctx(clock.now()))
        assert out.decisions[0].decision == "HOLD"
        assert "LATE_ENTRY" in list(out.decisions[0].holds)

    def test_atm_on_expiry(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        out = sel.decide([_signal(rule="ATM")], _ctx(clock.now(), is_expiry=True))
        assert out.decisions[0].decision == "HOLD"
        assert HOLD_ATM_EXPIRY in list(out.decisions[0].holds)

    def test_evaluate_holds_table_covers_yaml_windows(self) -> None:
        cfg = _cfg()
        ctx = _ctx(_ist(10, 5))
        assert evaluate_holds(cfg, ctx, _ist(10, 5)) == []
        assert "OPEN_NO_BUY" in evaluate_holds(cfg, ctx, _ist(9, 15))
        assert "LATE_ENTRY" in evaluate_holds(cfg, ctx, _ist(14, 45))


class TestConflictsAndBasket:
    def test_opposite_sides_hold_conflict(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        out = sel.decide(
            [
                _signal(side="CE", signal_id="sg_ce"),
                _signal(sid="PAPER-B", signal_id="sg_pe", side="PE"),
            ],
            _ctx(clock.now()),
        )
        assert out.decisions[0].decision == "HOLD"
        assert HOLD_CONFLICT in list(out.decisions[0].holds)

    def test_priority_weight_breaks_conflict(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock, basket=_basket(("PAPER-A", 1.0, 25), ("PAPER-B", 2.0, 25)))
        out = sel.decide(
            [
                _signal(side="CE", signal_id="sg_ce"),
                _signal(sid="PAPER-B", signal_id="sg_pe", side="PE"),
            ],
            _ctx(clock.now()),
        )
        assert out.decisions[0].decision == "ENTER"
        assert out.decisions[0].signal_ids == ["sg_pe"]

    def test_same_side_merges_contributors(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        out = sel.decide(
            [_signal(signal_id="sg_a"), _signal(sid="PAPER-B", signal_id="sg_b")],
            _ctx(clock.now()),
        )
        assert out.decisions[0].decision == "ENTER"
        assert set(out.decisions[0].signal_ids) == {"sg_a", "sg_b"}

    def test_not_in_basket_hold(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock, basket=_basket(("PAPER-A", 1.0, 25)))
        out = sel.decide([_signal(sid="OTHER", signal_id="sg_x")], _ctx(clock.now()))
        assert out.decisions[0].decision == "HOLD"
        assert HOLD_NOT_IN_BASKET in list(out.decisions[0].holds)

    def test_shadow_stage_never_enters(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock, basket=_basket(("SHADOW-X", 1.0, 25)))
        out = sel.decide([_signal(sid="SHADOW-X")], _ctx(clock.now()))
        assert out.decisions[0].decision == "HOLD"
        assert HOLD_STAGE in list(out.decisions[0].holds)

    def test_basket_remove_then_signal_dropped(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        first = sel.decide([_signal()], _ctx(clock.now()))
        assert first.decisions[0].decision == "ENTER"
        sel.basket_remove("PAPER-A")
        second = sel.decide([_signal(signal_id="sg_2")], _ctx(clock.now()))
        assert second.decisions[0].decision == "HOLD"
        assert HOLD_NOT_IN_BASKET in list(second.decisions[0].holds)

    def test_basket_add_rejected(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        extra = BasketEntry("NEW-X", ("NIFTY",), 1.0, 10, "paper")
        with pytest.raises(BasketFrozenError, match="K5"):
            sel.basket_add(extra)


class TestSizing:
    """Round 8 §3.0 fixtures. Lot size from the instrument master."""

    def test_volsize_matches_hand_computed(self) -> None:
        cfg = _cfg()
        assert volsize(27.4, cfg) == 25
        assert volsize(40.294117647058826, cfg) == 17
        assert volsize(685.0, cfg) == 1
        assert volsize(342.5, cfg) == 2

    def test_caplots_matches_hand_computed(self) -> None:
        lot = India().lot_size("NIFTY")
        assert caplots(30000.0, 0.5, 50.0, lot) == 18
        assert caplots(30000.0, 0.8, 80.0, lot) == 7
        assert caplots(30000.0, 0.5, 500.0, lot) == 1

    def test_size_lots_min_of_three_and_skip_below_two(self) -> None:
        cfg = _cfg()
        lot = India().lot_size("NIFTY")
        lots, sizing = size_lots(
            em30=40.294117647058826, delta=0.5, stop=50.0, lot_size=lot, basket_max=25, cfg=cfg
        )
        assert lots == 17
        assert sizing == {"volsize": 17, "caplots": 18, "basket_max": 25}
        skip, small = size_lots(
            em30=685.0, delta=0.5, stop=50.0, lot_size=lot, basket_max=25, cfg=cfg
        )
        assert skip is None
        assert small["volsize"] == 1
        capped, _ = size_lots(em30=27.4, delta=0.5, stop=50.0, lot_size=lot, basket_max=10, cfg=cfg)
        assert capped == 10

    def test_enter_carries_sizing_and_strike_choice(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        out = sel.decide([_signal()], _ctx(clock.now()))
        d = out.decisions[0]
        assert d.decision == "ENTER"
        assert d.lots == 17
        assert d.lot_size == India().lot_size("NIFTY")
        assert d.sizing == {"volsize": 17, "caplots": 18, "basket_max": 25}
        assert d.instrument_id == "NSE_FNO:NIFTY:2026-09-29:24400:CE"
        assert out.strike_choices[d.decision_id].chosen == "ITM100"
        assert d.shadow is not None
        assert d.shadow["strike_choice"]["chosen"] == "ITM100"

    def test_below_min_lots_holds(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        out = sel.decide([_signal()], _ctx(clock.now(), em30=685.0))
        assert out.decisions[0].decision == "HOLD"
        assert HOLD_BELOW_MIN_LOTS in list(out.decisions[0].holds)


class TestBossShadow:
    def test_shadow_published_decision_unchanged(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        ctx = _ctx(
            clock.now(),
            weights={"PAPER-A": 1.4, "PAPER-B": 0.6},
            intermarket={"regime": "risk_on"},
        )
        signals = [_signal(), _signal(sid="PAPER-B", signal_id="sg_b")]
        out = sel.decide(signals, ctx)
        assert out.decisions[0].decision == "ENTER"
        assert len(out.shadow_events) == 1
        ev = out.shadow_events[0]
        assert ev["event_type"] == "BOSS_SHADOW"
        assert ev["mode"] == "shadow"
        assert ev["regime"] == "trend_up"
        assert ev["decision_unchanged"] is True
        assert ev["ranks"][0]["strategy_id"] == "PAPER-A"
        assert ev["intermarket"]["regime"] == "risk_on"
        rerun = sel.decide(signals, ctx)
        assert rerun.decisions[0].decision == out.decisions[0].decision
        assert rerun.decisions[0].lots == out.decisions[0].lots
        assert rerun.decisions[0].signal_ids == out.decisions[0].signal_ids

    def test_apply_mode_still_does_not_change_decision(self, tmp_path: Path) -> None:
        text = REPO_ENGINE.read_text(encoding="utf-8").replace("mode: shadow", "mode: apply")
        path = tmp_path / "engine.yaml"
        path.write_text(text, encoding="utf-8")
        clock = SimClock(_ist(10, 5))
        shadow_sel = _selector(clock)
        apply_sel = _selector(SimClock(_ist(10, 5)), cfg=load_engine_config(path))
        ctx = _ctx(clock.now(), weights={"PAPER-A": 0.1, "PAPER-B": 3.0})
        signals = [_signal(), _signal(sid="PAPER-B", signal_id="sg_b", side="CE")]
        a = shadow_sel.decide(signals, ctx).decisions[0]
        b = apply_sel.decide(signals, ctx).decisions[0]
        assert a.decision == b.decision == "ENTER"
        assert a.lots == b.lots
        assert apply_sel.config.regime_mode == "apply"
        assert apply_sel.decide(signals, ctx).shadow_events[0]["decision_unchanged"] is True


class TestCausality:
    def test_future_available_ts_refused(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        with pytest.raises(LookAheadError, match="REG-01"):
            sel.decide([_signal()], _ctx(clock.now(), available_ts=_ist(10, 6)))

    def test_future_signal_decision_ts_refused(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        with pytest.raises(LookAheadError, match="REG-01"):
            sel.decide([_signal(ts=_ist(10, 6))], _ctx(clock.now()))

    def test_naive_timestamp_rejected(self) -> None:
        clock = SimClock(_ist(10, 5))
        sel = _selector(clock)
        with pytest.raises(ValueError, match="timezone-aware"):
            sel.decide(
                [_signal()],
                _ctx(clock.now(), bar_ts=datetime(2026, 9, 28, 10, 5)),
            )

    def test_random_cut_prefix_matches(self) -> None:
        rng = random.Random(7)
        bars = [_ist(10, m) for m in range(5, 25)]

        def run(prefix: list[datetime]) -> list[str]:
            clock = SimClock(prefix[0])
            sel = _selector(clock)
            out: list[str] = []
            for ts in prefix:
                clock.advance_to(ts)
                d = sel.decide([_signal(ts=ts, signal_id=f"sg_{ts.minute}")], _ctx(ts))
                out.append(d.decisions[0].decision)
            return out

        full = run(bars)
        cut = rng.randint(4, 16)
        assert run(bars[:cut]) == full[:cut]


class TestImportLinter:
    def test_selector_does_not_import_paper_scalp(self) -> None:
        src = SELECTOR_SRC.read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        assert not any("paper_scalp" in name for name in imported)
        assert "desk_ml.paper_scalp" not in src
        assert "dhan_client" not in src
        assert "DhanBroker" not in src

    def test_importing_selector_does_not_load_paper_scalp(self) -> None:
        import sys

        before = {k for k in sys.modules if "paper_scalp" in k}
        import boss.selector as selector_mod

        after = {k for k in sys.modules if "paper_scalp" in k}
        assert after == before
        assert selector_mod.HOLD_CONFLICT == "CONFLICT"


class TestPaperOnly:
    def test_selector_never_mentions_live_submit(self) -> None:
        src = SELECTOR_SRC.read_text(encoding="utf-8")
        assert "never calls a broker" in src
        assert "place_order" not in src
        assert "access_token" not in src

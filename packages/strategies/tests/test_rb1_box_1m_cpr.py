"""RB1-BOX-1M-CPR: frozen params, causal breaks, desk-stop logs. No broker."""

from __future__ import annotations

import logging
import random
from datetime import datetime
from pathlib import Path

import yaml
from contracts.clock import IST

from strategies.api import Bar, PositionUpdate, SessionContext
from strategies.onboarding import check_registry
from strategies.onboarding import main as onboarding_main
from strategies.params_hash import compute_params_hash
from strategies.plugins.rb1_box_1m_cpr import (
    CELL_ID,
    DESK_DAILY_CAP_INR,
    DESK_PREMIUM_STOP_PCT,
    LAST_EXIT_MIN,
    LOTS,
    NIFTY_LOT,
    PARAMS_DICT,
    PARAMS_HASH,
    SIGNAL_END_MIN,
    STRATEGY_ID,
    Rb1Box1mCprPlugin,
    box_width,
    cpr_levels,
    desk_daily_cap_would_fire,
    desk_premium_stop_would_fire,
    detect_breaks,
    premium_pnl_inr,
    strategy,
    trades_for_day,
)
from strategies.registry import load_registry
from strategies.runtime import emission_approved, load_strategy

ROOT = Path(__file__).resolve().parents[3]
SESSION = "2026-10-12"
PRIOR_H, PRIOR_L, PRIOR_C = 25200.0, 24800.0, 25100.0
DAY_OPEN = 25000.0
BANNED = ("DhanBroker", "place_order", "submit_order", "place_live")


class _View:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None:
        del instrument, tf
        return self.values.get(name)


def _minute(hhmm: str) -> int:
    hour, minute = (int(p) for p in hhmm.split(":"))
    return hour * 60 + minute


def _bar(hhmm: str, open_px: float, high: float, low: float, close: float) -> Bar:
    hour, minute = (int(p) for p in hhmm.split(":"))
    ts = datetime(2026, 10, 12, hour, minute, tzinfo=IST).isoformat()
    return Bar(
        instrument_id="NSE_IDX:NIFTY",
        open=open_px,
        high=high,
        low=low,
        close=close,
        volume=1000,
        timestamp=ts,
        available_ts=ts,
    )


def _view(
    *,
    ce: float = 100.0,
    pe: float = 100.0,
    ce_ask: float | None = None,
    ce_bid: float | None = None,
    pe_ask: float | None = None,
    pe_bid: float | None = None,
) -> _View:
    values: dict[str, object] = {
        "prior_high": PRIOR_H,
        "prior_low": PRIOR_L,
        "prior_close": PRIOR_C,
        "day_open": DAY_OPEN,
        "atm_ce": ce,
        "atm_pe": pe,
    }
    if ce_ask is not None:
        values["atm_ce_ask"] = ce_ask
    if ce_bid is not None:
        values["atm_ce_bid"] = ce_bid
    if pe_ask is not None:
        values["atm_pe_ask"] = pe_ask
    if pe_bid is not None:
        values["atm_pe_bid"] = pe_bid
    return _View(values)


def _ohlc(
    rows: list[tuple[str, float, float, float, float]],
) -> tuple[list[float], list[float], list[float], list[float], list[int]]:
    opens = [r[1] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    closes = [r[4] for r in rows]
    minutes = [_minute(r[0]) for r in rows]
    return opens, highs, lows, closes, minutes


# Tight 3-bar box then an UP break that passes CPR WITH + bsz=.5-1.
UP_SETUP: list[tuple[str, float, float, float, float]] = [
    ("09:15", 25000.0, 25030.0, 24990.0, 25020.0),
    ("09:16", 25020.0, 25040.0, 25000.0, 25025.0),
    ("09:17", 25025.0, 25045.0, 25010.0, 25030.0),
    ("09:18", 25030.0, 25120.0, 25020.0, 25100.0),  # break
    ("09:19", 25100.0, 25110.0, 25090.0, 25105.0),  # entry
]

DN_SETUP: list[tuple[str, float, float, float, float]] = [
    ("09:15", 25000.0, 25030.0, 24990.0, 25020.0),
    ("09:16", 25020.0, 25040.0, 25000.0, 25015.0),
    ("09:17", 25015.0, 25035.0, 24995.0, 25010.0),
    ("09:18", 25010.0, 25020.0, 24900.0, 24940.0),  # DN break, body 70/75
    ("09:19", 24940.0, 24950.0, 24920.0, 24930.0),
]


def _ctx() -> SessionContext:
    return SessionContext(
        SESSION,
        "IN_INDEX_OPT",
        {"prior_high": PRIOR_H, "prior_low": PRIOR_L, "prior_close": PRIOR_C, "day_open": DAY_OPEN},
    )


def _feed(
    plugin: Rb1Box1mCprPlugin,
    rows: list[tuple[str, float, float, float, float]],
    view: _View | None = None,
) -> list:
    plugin.on_session_start(_ctx())
    out = []
    snap = view or _view()
    for hhmm, o, h, lo, c in rows:
        out.extend(plugin.on_bar(_bar(hhmm, o, h, lo, c), snap))
    return out


def test_registry_loads_shadow_only_and_not_a_paper_slot() -> None:
    registry = load_registry()
    assert STRATEGY_ID in registry
    inst = load_strategy(STRATEGY_ID, registry)
    assert inst.meta.strategy_id == STRATEGY_ID
    assert inst.meta.stage == "shadow"
    assert inst.meta.params_hash == PARAMS_HASH
    assert inst.meta.params_hash == registry[STRATEGY_ID].params_hash
    assert inst.exit_plan.catastrophic.level.price == DESK_DAILY_CAP_INR
    assert emission_approved(STRATEGY_ID, "shadow") is True
    assert not hasattr(inst, "place_order")
    assert not hasattr(inst, "broker")


def test_params_hash_is_canonical_frozen_json() -> None:
    assert compute_params_hash(PARAMS_DICT) == PARAMS_HASH
    assert PARAMS_HASH == "d0cebf4b9f61b228"
    assert PARAMS_DICT["box_width_pct"] == 0.30
    assert PARAMS_DICT["break_cell"] == "cpr=WITH & bsz=.5-1"
    assert PARAMS_DICT["lots"] == 10
    assert PARAMS_DICT["live"] is False
    assert PARAMS_DICT["orders"] == "REFUSED"


def test_k9_accepts_rb1_shadow_row() -> None:
    errors = [e for e in check_registry() if STRATEGY_ID in e]
    assert errors == []
    assert onboarding_main([]) == 0


def test_accounts_yaml_unchanged() -> None:
    path = ROOT / "config" / "v2" / "accounts.yaml"
    body = yaml.safe_load(path.read_text(encoding="utf-8"))
    wanted = {
        "customer-01": "R01_PDIV_5_ALL_H20",
        "customer-02": "R01_B3A_VOL",
        "customer-03": "B8B_B3A_EX_CHOPPY",
        "customer-04": "R07_MOM3_TREND",
        "customer-05": "B8A_R07_NO_PRE1030",
    }
    customers = [row for row in body["accounts"] if str(row["account_id"]).startswith("customer-")]
    for row in customers:
        assert row["strategy_id"] == wanted[str(row["account_id"])]
        assert row["strategy_id"] != STRATEGY_ID


def test_cpr_and_box_width_match_spec() -> None:
    pivot, bc, tc = cpr_levels(PRIOR_H, PRIOR_L, PRIOR_C)
    assert abs(pivot - (PRIOR_H + PRIOR_L + PRIOR_C) / 3.0) < 1e-9
    assert bc == (PRIOR_H + PRIOR_L) / 2.0
    assert abs(tc - (2.0 * pivot - bc)) < 1e-9
    assert box_width(DAY_OPEN) == 75.0


def test_up_break_emits_ce_on_break_bar() -> None:
    plugin = Rb1Box1mCprPlugin()
    sigs = _feed(plugin, UP_SETUP)
    assert len(sigs) == 1
    sig = sigs[0]
    assert sig.strategy_id == STRATEGY_ID
    assert sig.side == "CE"
    assert sig.strike_rule == "ATM"
    assert sig.decision_ts.endswith("09:18:00+05:30")
    assert sig.features["sig_min"] == float(_minute("09:18"))
    assert sig.features["entry_min"] == float(_minute("09:19"))
    assert sig.features["qty"] == float(LOTS * NIFTY_LOT)
    assert "LIVE_REFUSED" in sig.reasons
    assert CELL_ID in sig.reasons


def test_dn_break_emits_pe() -> None:
    plugin = Rb1Box1mCprPlugin()
    sigs = _feed(plugin, DN_SETUP)
    assert [s.side for s in sigs] == ["PE"]
    assert sigs[0].decision_ts.endswith("09:18:00+05:30")


def test_batch_trades_match_plugin_on_up_setup() -> None:
    width = box_width(DAY_OPEN)
    _p, bc, tc = cpr_levels(PRIOR_H, PRIOR_L, PRIOR_C)
    opens, highs, lows, closes, minutes = _ohlc(UP_SETUP)
    rows = trades_for_day(opens, highs, lows, closes, minutes, width=width, tc=tc, bc=bc)
    assert len(rows) == 1
    assert rows[0].side == "CE"
    assert rows[0].sig_min == _minute("09:18")
    assert rows[0].entry_min == _minute("09:19")
    plugin = Rb1Box1mCprPlugin()
    sigs = _feed(plugin, UP_SETUP)
    assert sigs[0].features["sig_min"] == float(rows[0].sig_min)
    assert sigs[0].side == rows[0].side


def test_lookahead_breaks_match_when_truncated_at_break_bar() -> None:
    width = box_width(DAY_OPEN)
    opens, highs, lows, closes, minutes = _ohlc(UP_SETUP)
    full = detect_breaks(opens, highs, lows, closes, minutes, width)
    assert full
    brk = full[0]
    cut = detect_breaks(
        opens[: brk.i + 1],
        highs[: brk.i + 1],
        lows[: brk.i + 1],
        closes[: brk.i + 1],
        minutes[: brk.i + 1],
        width,
    )
    assert [(b.i, b.side, b.bh, b.bl, b.minute) for b in cut] == [
        (brk.i, brk.side, brk.bh, brk.bl, brk.minute)
    ]


def test_plugin_lookahead_signal_on_truncated_break_bar() -> None:
    full = Rb1Box1mCprPlugin()
    full_sigs = _feed(full, UP_SETUP)
    cut = Rb1Box1mCprPlugin()
    cut_sigs = _feed(cut, UP_SETUP[:4])  # through the break bar only
    assert len(full_sigs) == 1
    assert len(cut_sigs) == 1
    assert cut_sigs[0].side == full_sigs[0].side
    assert cut_sigs[0].decision_ts == full_sigs[0].decision_ts
    assert cut_sigs[0].features["sig_min"] == full_sigs[0].features["sig_min"]


def test_random_cut_causality_on_plugin() -> None:
    rng = random.Random(11)
    series = list(UP_SETUP)
    for i in range(20):
        px = 25105.0 + i
        hh = 9
        mm = 20 + i
        series.append((f"{hh:02d}:{mm:02d}", px, px + 5, px - 5, px + 1))

    def run(prefix: list[tuple[str, float, float, float, float]]) -> list[tuple[str, str]]:
        plugin = Rb1Box1mCprPlugin()
        plugin.on_session_start(_ctx())
        out: list[tuple[str, str]] = []
        for hhmm, o, h, lo, c in prefix:
            sigs = plugin.on_bar(_bar(hhmm, o, h, lo, c), _view())
            out.append((hhmm, ",".join(s.side for s in sigs)))
        return out

    full = run(series)
    cut = rng.randint(4, 12)
    assert run(series[:cut]) == full[:cut]


def test_cpr_filter_rejects_inside_cpr() -> None:
    # Close 25040 is above the box but below TC 25066 — not WITH.
    rows = [
        ("09:15", 25000.0, 25030.0, 24990.0, 25020.0),
        ("09:16", 25020.0, 25040.0, 25000.0, 25025.0),
        ("09:17", 25025.0, 25045.0, 25010.0, 25030.0),
        ("09:18", 25030.0, 25120.0, 25020.0, 25040.0),
        ("09:19", 25040.0, 25050.0, 25030.0, 25045.0),
    ]
    assert _feed(Rb1Box1mCprPlugin(), rows) == []


def test_bsz_filter_rejects_tiny_body() -> None:
    rows = [
        ("09:15", 25000.0, 25030.0, 24990.0, 25020.0),
        ("09:16", 25020.0, 25040.0, 25000.0, 25025.0),
        ("09:17", 25025.0, 25045.0, 25010.0, 25030.0),
        ("09:18", 25095.0, 25120.0, 25020.0, 25100.0),  # body 5 / 75 < 0.5
        ("09:19", 25100.0, 25110.0, 25090.0, 25105.0),
    ]
    assert _feed(Rb1Box1mCprPlugin(), rows) == []


def test_signal_window_skips_after_1505() -> None:
    late = [
        ("15:04", 25000.0, 25030.0, 24990.0, 25020.0),
        ("15:05", 25020.0, 25040.0, 25000.0, 25025.0),
        ("15:06", 25025.0, 25045.0, 25010.0, 25030.0),
        ("15:07", 25030.0, 25120.0, 25020.0, 25100.0),
        ("15:08", 25100.0, 25110.0, 25090.0, 25105.0),
    ]
    assert _feed(Rb1Box1mCprPlugin(), late) == []
    assert SIGNAL_END_MIN == 905


def test_one_at_a_time_and_max_three() -> None:
    rows = list(UP_SETUP)
    # After first entry 09:19, keep the trade open (stay outside the box, no trail).
    for i, hhmm in enumerate(["09:20", "09:21", "09:22", "09:23", "09:24"]):
        px = 25110.0 + i
        rows.append((hhmm, px, px + 8, px - 4, px + 2))
    plugin = Rb1Box1mCprPlugin()
    sigs = _feed(plugin, rows)
    assert len(sigs) == 1


def test_exit_back_inside_box() -> None:
    rows = [
        *UP_SETUP,
        ("09:20", 25100.0, 25105.0, 25000.0, 25020.0),  # close back inside
    ]
    plugin = Rb1Box1mCprPlugin()
    _feed(plugin, rows)
    assert len(plugin.trades) == 1
    assert plugin.trades[0].exit_reason == "BACK_INSIDE"
    assert plugin.trades[0].exit_min == _minute("09:20")


def test_exit_trail_giveback() -> None:
    rows = [
        *UP_SETUP,
        ("09:20", 25110.0, 25150.0, 25100.0, 25140.0),  # +40 from entry open 25100
        ("09:21", 25140.0, 25145.0, 25115.0, 25120.0),  # giveback 20 > 0.35*40
    ]
    plugin = Rb1Box1mCprPlugin()
    _feed(plugin, rows)
    assert plugin.trades
    assert plugin.trades[0].exit_reason == "TRAIL"
    assert plugin.trades[0].exit_min == _minute("09:21")


def test_exit_time_at_1515() -> None:
    rows = list(UP_SETUP)
    # Stay outside the box, never arm a giveback, until 15:15.
    px = 25110.0
    minute = _minute("09:20")
    while minute < LAST_EXIT_MIN:
        hh, mm = divmod(minute, 60)
        rows.append((f"{hh:02d}:{mm:02d}", px, px + 5, px - 5, px))
        minute += 1
    rows.append(("15:15", px, px + 5, px - 5, px))
    plugin = Rb1Box1mCprPlugin()
    _feed(plugin, rows)
    assert plugin.trades
    assert plugin.trades[0].exit_reason == "TIME"
    assert plugin.trades[0].exit_min == LAST_EXIT_MIN


def test_desk_premium_stop_is_logged(caplog) -> None:
    caplog.set_level(logging.INFO)
    plugin = Rb1Box1mCprPlugin()
    plugin.on_session_start(_ctx())
    view_in = _view(ce_ask=100.0, ce_bid=99.0)
    for hhmm, o, h, lo, c in UP_SETUP:
        plugin.on_bar(_bar(hhmm, o, h, lo, c), view_in)
    plugin.on_bar(
        _bar("09:20", 25110.0, 25120.0, 25100.0, 25115.0),
        _view(ce_ask=100.0, ce_bid=85.0),
    )
    kinds = [e["kind"] for e in plugin.desk_events]
    assert "DESK_PREMIUM_STOP_15PCT" in kinds
    assert any("DESK_PREMIUM_STOP_15PCT" in rec.message for rec in caplog.records)
    assert desk_premium_stop_would_fire(100.0, 85.0) is True
    assert DESK_PREMIUM_STOP_PCT == 0.15


def test_desk_daily_cap_is_logged(caplog) -> None:
    caplog.set_level(logging.INFO)
    plugin = Rb1Box1mCprPlugin()
    plugin.on_session_start(_ctx())
    view_in = _view(ce_ask=100.0, ce_bid=99.0)
    for hhmm, o, h, lo, c in UP_SETUP:
        plugin.on_bar(_bar(hhmm, o, h, lo, c), view_in)
    plugin.on_bar(
        _bar("09:20", 25110.0, 25120.0, 25100.0, 25115.0),
        _view(ce_ask=100.0, ce_bid=50.0),
    )
    kinds = [e["kind"] for e in plugin.desk_events]
    assert "DESK_DAILY_CAP_30K" in kinds
    assert any("DESK_DAILY_CAP_30K" in rec.message for rec in caplog.records)
    assert premium_pnl_inr(100.0, 50.0) <= -DESK_DAILY_CAP_INR
    assert desk_daily_cap_would_fire(0.0, premium_pnl_inr(100.0, 50.0)) is True


def test_on_position_logs_daily_cap() -> None:
    plugin = Rb1Box1mCprPlugin()
    _feed(plugin, UP_SETUP, _view(ce_ask=100.0, ce_bid=99.0))
    plugin.on_position(PositionUpdate("NSE_FNO:NIFTY", 650, 100.0, -30000.0))
    assert any(e["kind"] == "DESK_DAILY_CAP_30K" for e in plugin.desk_events)


def test_plugin_is_paper_only_no_broker() -> None:
    text = (
        ROOT / "packages" / "strategies" / "src" / "strategies" / "plugins" / "rb1_box_1m_cpr.py"
    ).read_text(encoding="utf-8")
    for token in BANNED:
        assert token not in text
    assert strategy.meta.stage == "shadow"
    end = Rb1Box1mCprPlugin().on_session_end()
    assert end["live"] is False
    assert end["orders"] == "REFUSED"
    assert end["stage"] == "shadow"

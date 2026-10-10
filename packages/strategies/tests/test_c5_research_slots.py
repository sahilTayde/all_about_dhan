"""C5 paper research slots. Each plugin fires on a frozen-spec fixture. No broker."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from contracts.clock import IST
from desk_ml.research_rules import LOTS, QTY, mplus

from strategies.api import Bar, SessionContext
from strategies.onboarding import check_registry
from strategies.onboarding import main as onboarding_main
from strategies.plugins.b8a_r07_no_pre1030 import strategy as b8a
from strategies.plugins.b8b_b3a_ex_choppy import strategy as b8b
from strategies.plugins.r01_b3a_vol import strategy as r01_b3a
from strategies.plugins.r01_pdiv_5_all_h20 import strategy as r01
from strategies.plugins.r07_mom3_trend import strategy as r07
from strategies.plugins.research_common import (
    SLOT_IDS,
    ResearchSlotPlugin,
    er30,
)
from strategies.registry import load_registry
from strategies.runtime import emission_approved, load_strategy

ROOT = Path(__file__).resolve().parents[3]
SESSION = "2026-10-09"
REGISTRY_IDS = (
    "R01_PDIV_5_ALL_H20",
    "R01_B3A_VOL",
    "B8B_B3A_EX_CHOPPY",
    "R07_MOM3_TREND",
    "B8A_R07_NO_PRE1030",
)
PLUGINS = (r01, r01_b3a, b8b, r07, b8a)


class _View:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None:
        del instrument, tf
        return self.values.get(name)


def _minutes(start: str, n: int) -> list[str]:
    out = [start]
    for _ in range(n - 1):
        out.append(mplus(out[-1], 1))
    return out


def _bar(hhmm: str, idx: float, und: str = "NIFTY") -> Bar:
    hour, minute = (int(p) for p in hhmm.split(":"))
    ts = datetime(2026, 10, 9, hour, minute, tzinfo=IST).isoformat()
    prefix = "BSE_IDX" if und == "SENSEX" else "NSE_IDX"
    return Bar(
        instrument_id=f"{prefix}:{und}",
        open=idx,
        high=idx + 1.0,
        low=idx - 1.0,
        close=idx,
        volume=1000,
        timestamp=ts,
        available_ts=ts,
    )


def _view(
    und: str,
    idx: float,
    *,
    ce: float = 100.0,
    pe: float = 100.0,
    atm: float | None = None,
) -> _View:
    strike = 80000.0 if und == "SENSEX" and atm is None else (25000.0 if atm is None else atm)
    return _View(
        {
            "underlying": und,
            "idx": idx,
            "atm": strike,
            "atm_ce": ce,
            "atm_pe": pe,
        }
    )


def _feed(plugin: ResearchSlotPlugin, rows: list[tuple[str, str, float, float, float]]) -> list:
    plugin.on_session_start(SessionContext(SESSION, "IN_INDEX_OPT", {}))
    out = []
    for hhmm, und, idx, ce, pe in rows:
        out.extend(plugin.on_bar(_bar(hhmm, idx, und), _view(und, idx, ce=ce, pe=pe)))
    return out


def _flat_pdiv(*, ce_t: float = 110.0, pe_t: float = 100.0, und: str = "NIFTY") -> list[tuple]:
    rows = []
    for hhmm in _minutes("09:30", 36):
        idx = 25000.2 if hhmm == "10:05" else 25000.0
        ce, pe = (ce_t, pe_t) if hhmm == "10:05" else (100.0, 100.0)
        rows.append((hhmm, und, idx, ce, pe))
    return rows


def _choppy_pdiv(*, ce_t: float = 110.0, pe_t: float = 100.0) -> list[tuple]:
    rows = []
    flat = 25000.0
    for i, hhmm in enumerate(_minutes("09:30", 36)):
        if hhmm <= "10:00":
            idx = 25000.0 + (40.0 if i % 2 == 0 else -40.0)
            if hhmm == "10:00":
                flat = idx
        else:
            idx = flat
        ce, pe = (ce_t, pe_t) if hhmm == "10:05" else (100.0, 100.0)
        rows.append((hhmm, "NIFTY", idx, ce, pe))
    return rows


def _trendy_vol_pdiv(*, ce_t: float = 110.0, pe_t: float = 100.0) -> list[tuple]:
    rows = []
    idx = 24800.0
    for i, hhmm in enumerate(_minutes("09:30", 36)):
        if hhmm < "10:00":
            idx += 18.0 if i % 3 == 0 else 3.0
        ce, pe = (ce_t, pe_t) if hhmm == "10:05" else (100.0, 100.0)
        rows.append((hhmm, "NIFTY", idx, ce, pe))
    return rows


def _ramp(n: int = 61, start: str = "09:30") -> list[tuple]:
    rows = []
    for i, hhmm in enumerate(_minutes(start, n)):
        rows.append((hhmm, "NIFTY", 25000.0 + i * 5.0, 100.0, 100.0))
    return rows


def _assert_buy(sig, *, sid: str, side: str, und: str = "NIFTY") -> None:
    assert sig.strategy_id == sid
    assert sig.side == side
    assert sig.underlying == und
    assert sig.strike_rule == "ATM"
    assert sig.strike_choice.chosen == "ATM"
    assert sig.exit_plan.time_stops[0].after_s == 1200
    assert sig.exit_plan.structural is None
    assert "LIVE_REFUSED" in sig.reasons
    assert f"BUY_{side}" in sig.reasons
    qty, lots = QTY[und], LOTS
    assert sig.features["qty"] == float(qty)
    assert sig.features["lots"] == float(lots)


def test_registry_loads_all_five_paper_slots() -> None:
    registry = load_registry()
    for sid in REGISTRY_IDS:
        inst = load_strategy(sid, registry)
        assert inst.meta.strategy_id == sid
        assert inst.meta.stage == "paper"
        assert inst.meta.stage != "live_eligible"
        assert inst.meta.underlyings == ("NIFTY", "SENSEX")
        assert inst.params["qty"]["NIFTY"] == 650
        assert inst.params["qty"]["SENSEX"] == 200
        assert inst.params["lots"] == 10
        assert inst.params["live"] is False
        assert inst.params["orders"] == "REFUSED"
        assert inst.params["side"] == "BUY_ONLY"
        assert emission_approved(sid, "paper") is True
        assert not hasattr(inst, "place_order")
        assert not hasattr(inst, "broker")


def test_k9_accepts_new_registry_rows() -> None:
    assert SLOT_IDS == REGISTRY_IDS
    errors = [e for e in check_registry() if any(sid in e for sid in REGISTRY_IDS)]
    assert errors == []
    assert onboarding_main([]) == 0


def test_r01_fires_ce_and_pe_on_spec_fixture() -> None:
    plugin = ResearchSlotPlugin("R01_PDIV_5_ALL_H20")
    ce = _feed(plugin, _flat_pdiv())
    assert len(ce) == 1
    _assert_buy(ce[0], sid="R01_PDIV_5_ALL_H20", side="CE")
    assert ce[0].decision_ts.endswith("10:05:00+05:30")

    plugin = ResearchSlotPlugin("R01_PDIV_5_ALL_H20")
    pe = _feed(plugin, _flat_pdiv(ce_t=100.0, pe_t=112.0))
    assert len(pe) == 1
    _assert_buy(pe[0], sid="R01_PDIV_5_ALL_H20", side="PE")


def test_r01_also_fires_sensex_ten_lots() -> None:
    plugin = ResearchSlotPlugin("R01_PDIV_5_ALL_H20")
    sigs = _feed(plugin, _flat_pdiv(und="SENSEX"))
    assert len(sigs) == 1
    _assert_buy(sigs[0], sid="R01_PDIV_5_ALL_H20", side="CE", und="SENSEX")
    assert sigs[0].features["qty"] == 200.0
    assert sigs[0].features["lot_size"] == 20.0


def test_r01_b3a_vol_requires_rv30_cut() -> None:
    quiet = ResearchSlotPlugin("R01_B3A_VOL")
    assert _feed(quiet, _flat_pdiv()) == []
    plugin = ResearchSlotPlugin("R01_B3A_VOL")
    sigs = _feed(plugin, _trendy_vol_pdiv())
    assert len(sigs) == 1
    _assert_buy(sigs[0], sid="R01_B3A_VOL", side="CE")


def test_b8b_excludes_choppy_and_fires_on_trend_or_sideways() -> None:
    chop = ResearchSlotPlugin("B8B_B3A_EX_CHOPPY")
    assert _feed(chop, _choppy_pdiv()) == []
    # Same choppy tape is a valid B3A (vol gate only).
    b3a = ResearchSlotPlugin("R01_B3A_VOL")
    assert [s.side for s in _feed(b3a, _choppy_pdiv())] == ["CE"]

    plugin = ResearchSlotPlugin("B8B_B3A_EX_CHOPPY")
    sigs = _feed(plugin, _trendy_vol_pdiv())
    assert len(sigs) == 1
    _assert_buy(sigs[0], sid="B8B_B3A_EX_CHOPPY", side="CE")
    assert sigs[0].features["er30"] >= 0.20


def test_r07_fires_on_trend_mom3_and_skips_nontend() -> None:
    plugin = ResearchSlotPlugin("R07_MOM3_TREND")
    sigs = _feed(plugin, _ramp(36))
    assert len(sigs) == 1
    _assert_buy(sigs[0], sid="R07_MOM3_TREND", side="CE")
    assert sigs[0].decision_ts.endswith("10:00:00+05:30")

    flat = ResearchSlotPlugin("R07_MOM3_TREND")
    assert _feed(flat, _flat_pdiv()) == []


def test_b8a_refuses_pre_1030_and_fires_at_or_after() -> None:
    early = ResearchSlotPlugin("B8A_R07_NO_PRE1030")
    assert _feed(early, _ramp(36)) == []  # last bar 10:05, window starts 10:30
    plugin = ResearchSlotPlugin("B8A_R07_NO_PRE1030")
    sigs = _feed(plugin, _ramp(61))
    assert len(sigs) == 1
    _assert_buy(sigs[0], sid="B8A_R07_NO_PRE1030", side="CE")
    assert sigs[0].decision_ts.endswith("10:30:00+05:30")


def test_one_open_per_underlying_until_hold_expires() -> None:
    plugin = ResearchSlotPlugin("R01_PDIV_5_ALL_H20")
    rows = _flat_pdiv()
    # Second PDIV while busy (exit 10:26) must not emit.
    extra = []
    for hhmm in _minutes("10:06", 6):
        extra.append((hhmm, "NIFTY", 25000.0, 110.0, 100.0))
    sigs = _feed(plugin, rows + extra)
    assert len(sigs) == 1


def test_plugins_are_paper_only_and_live_refused() -> None:
    banned = ("DhanBroker", "place_order", "submit_order", "place_live")
    plugin_dir = Path(__file__).resolve().parents[1] / "src" / "strategies" / "plugins"
    text = (plugin_dir / "research_common.py").read_text(encoding="utf-8")
    for token in banned:
        assert token not in text
    for plugin in PLUGINS:
        assert plugin.meta.stage == "paper"
        assert plugin.meta.stage not in {"live", "live_eligible", "limited_live"}
        end = plugin.on_session_end()
        assert end["live"] is False
        assert end["orders"] == "REFUSED"
        assert end["stage"] == "paper"


def test_r01_and_b3a_reuse_desk_ml_research_rules() -> None:
    plugin_dir = Path(__file__).resolve().parents[1] / "src" / "strategies" / "plugins"
    common = (plugin_dir / "research_common.py").read_text(encoding="utf-8")
    assert "from desk_ml import research_rules as rr" in common
    assert "ce_t / ce_k - pe_t / pe_k" not in common
    assert "idx_t / idx_k - 1.0" not in common
    assert "rr.R01" in common and "rr.R01_B3A" in common
    assert "rr.signal(" in common


def test_er30_matches_roster_formula() -> None:
    bars = {hhmm: {"idx": 25000.0 + i} for i, hhmm in enumerate(_minutes("09:30", 31))}
    assert er30(bars, "10:00") == 1.0
    assert er30({"10:00": {"idx": 1.0}}, "10:00") is None


def test_accounts_stay_disabled_and_unarmed() -> None:
    path = ROOT / "config" / "v2" / "accounts.yaml"
    body = yaml.safe_load(path.read_text(encoding="utf-8"))
    customers = [row for row in body["accounts"] if str(row["account_id"]).startswith("customer-")]
    assert [row["account_id"] for row in customers] == [f"customer-0{i}" for i in range(1, 6)]
    for row in customers:
        assert row["status"] == "disabled"
        assert not row.get("strategy_id")
        assert not row.get("basket")
        assert row["broker"] == "paper"

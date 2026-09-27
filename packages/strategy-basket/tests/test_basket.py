"""Basket selector: schema, lab loader, selector determinism, no look-ahead, off-by-default parity, forex parked."""

import copy
import json
import os
import random
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

import desk_ml.paper_scalp as ps
from desk_ml.event_parity import fixture_replay_kwargs, load_fixture
from desk_ml.event_path import EventSession
from desk_ml.features import Triple
from desk_ml.regime.labels import IST
from events import MemoryBus
from strategy_basket.entry import impulse_mid, last_fvg, measure, point_of_control, stretch_atr, verdict
from strategy_basket.basket import (
    MAIN_LAB_BASELINE, MAIN_REPLAY_BASELINES, REGIME_KEYS, BasketBus, BasketError, BasketEventSession, BasketShadow,
    attach_from_settings, basket_parity, check_main_baselines, for_session, legacy_replay_total, load_basket, load_lab,
    load_lab_basket, load_settings, parse_card, preopen_regime, regime_from_label, select_basket, shadow_from_settings,
)

REPO = Path(__file__).resolve().parents[3]
INDIA, FOREX = REPO / "config" / "baskets" / "india.yaml", REPO / "config" / "baskets" / "forex.yaml"
FIXTURE = REPO / "packages" / "desk-ml" / "tests" / "fixtures" / "synthetic_session_nifty.json"
KEY = "trend_up.vol_normal.non_expiry_day"
DAY = "2026-09-10"


def score(**kw):
    base = {"net_pnl": 50000.0, "pf": 1.6, "trades": 80, "win_rate": 0.52, "dsr": 0.97, "weight": 0.5, "rank": 1,
            "status": "active_candidate"}
    return {**base, **kw}


PULLBACK = {"kind": "pullback_limit", "zone": "fvg", "timeout_bars": 3, "max_stretch_atr": None}
CHASE = {"kind": "chase"}


def card(cid="MIX-LAB-A", scores=None, markets=("NIFTY",), policy=None):
    return {
        "id": cid, "source": {"kind": "trader", "ref": "lab run 42"}, "markets": list(markets),
        "adaptations": {markets[0]: {"stop_frac": 0.35}},
        "rules": {"entry": {"signal": "orb_break", "minutes": 15}, "exit": {"stop_frac": 0.4, "target_frac": 0.55},
                  "strike": {"premium": "ITM", "depth": 1}, "sizing": {"lots": 25}, "skip": {"sideways": True}},
        "param_ranges": {"stop_frac": [0.3, 0.35, 0.4]},
        "entry_policy": dict(policy or PULLBACK),
        "scores": {KEY: score()} if scores is None else scores,
    }


def lab_file(tmp, cards, **top):
    blob = {"schema_version": 1, "market": "india", "generated_at": "2026-09-09T18:00:00+05:30",
            "source": "scripts/lab run 42", "data_until": "2026-09-09", "strategies": cards, **top}
    path = Path(tmp) / "basket_india.json"
    path.write_text(json.dumps(blob), encoding="utf-8")
    return path


def regime(key=KEY):
    p, v, e = key.split(".")
    return {"primary": p, "vol": v, "expiry": e, "key": key}


def _ts(hh, mm, day=DAY):
    y, m, d = map(int, day.split("-"))
    return int(datetime(y, m, d, hh, mm, tzinfo=IST).timestamp())


def minute_label(hh, mm, primary="trend_up", vol=None, expiry_day=False, und="NIFTY"):
    return {"scope": "minute", "underlying": und, "ts": _ts(hh, mm), "primary": primary, "vol": vol,
            "expiry_day": expiry_day, "gap_day": False, "labels": [primary], "features": {"adx": 30.0},
            "version": "v0-default-unvalidated"}


def _basket(cards, **entry):
    b = load_basket(INDIA)
    return replace(b, entry={**b.entry, **entry}, cards={c["id"]: parse_card(c, require_scores=False) for c in cards})


# ------------------------------------------------------------------ schema


def test_committed_baskets_load_and_validate():
    india, forex = load_basket(INDIA), load_basket(FOREX)
    assert india.activatable and sorted(india.instruments) == ["NIFTY", "SENSEX"]
    assert india.instruments["NIFTY"].expiry_weekday == "TUE" and india.instruments["NIFTY"].lot_size == 65
    assert "MIX-DEFAULT-BUY" in india.cards
    assert not forex.activatable and "EURUSD" in forex.instruments
    text = INDIA.read_text(encoding="utf-8") + FOREX.read_text(encoding="utf-8")
    assert "Source:" in text and "TODO(verify)" in text


def test_every_committed_card_and_basket_carries_an_entry_policy():
    india = load_basket(INDIA)
    assert india.cards["MIX-DEFAULT-BUY"].entry_policy["kind"] == "chase"  # what legacy does
    assert india.entry["mode"] == "log_only" and load_basket(FOREX).entry["mode"] == "log_only"
    assert "PLACEHOLDER" in INDIA.read_text(encoding="utf-8")


def test_basket_without_entry_location_is_rejected(tmp_path):
    text = INDIA.read_text(encoding="utf-8")
    start = text.index("entry_location:")
    end = text.index("\n\n", start)
    p = tmp_path / "b.yaml"
    p.write_text(text[:start] + text[end:], encoding="utf-8")
    with pytest.raises(BasketError, match="entry_location"):
        load_basket(p)
    p.write_text(text.replace("mode: log_only", "mode: enforce"), encoding="utf-8")
    with pytest.raises(BasketError, match="mode"):
        load_basket(p)


def test_basket_file_may_not_define_its_own_regime_thresholds(tmp_path):
    p = tmp_path / "b.yaml"
    p.write_text(INDIA.read_text(encoding="utf-8") + "\nregime: {intraday_bars: 30}\n", encoding="utf-8")
    with pytest.raises(BasketError, match="config/regime.yaml"):
        load_basket(p)


@pytest.mark.parametrize("mutate, message", [
    (lambda c: c.update(id="bad id"), "id"),
    (lambda c: c["source"].update(kind="guru"), "source"),
    (lambda c: c["rules"].pop("skip"), "rules"),
    (lambda c: c["rules"].update(entry={}), "exact parameters"),
    (lambda c: c["scores"].update({"trend.high_vol.expiry": score()}), "regime key"),
    (lambda c: c["scores"][KEY].update(status="live"), "status"),
    (lambda c: c["scores"][KEY].update(win_rate=1.5), "win_rate"),
    (lambda c: c["scores"][KEY].update(trades=10.5), "trades"),
    (lambda c: c["scores"][KEY].update(pf=float("inf")), "finite"),
    (lambda c: c["scores"][KEY].pop("dsr"), "unscored"),
    (lambda c: c.update(scores={}), "unscored"),
    (lambda c: c.update(stoploss=5), "unknown keys"),
    (lambda c: c["param_ranges"].update(stop_frac=[]), "param_ranges"),
    (lambda c: c.update(adaptations={"BANKNIFTY": {}}), "adaptations"),
    (lambda c: c.pop("entry_policy"), "entry_policy"),
    (lambda c: c.update(entry_policy={"kind": "fomo"}), "kind"),
    (lambda c: c.update(entry_policy={"kind": "pullback_limit", "timeout_bars": 3}), "zone"),
    (lambda c: c.update(entry_policy={"kind": "pullback_limit", "zone": "vwap", "timeout_bars": 3}), "zone"),
    (lambda c: c.update(entry_policy={"kind": "pullback_limit", "zone": "poc"}), "timeout"),
    (lambda c: c.update(entry_policy={"kind": "chase", "timeout_bars": 2}), "does not wait"),
    (lambda c: c.update(entry_policy={"kind": "wait_consolidation", "zone": "fvg"}), "only pullback_limit"),
    (lambda c: c.update(entry_policy={"kind": "chase", "max_stretch_atr": -1}), "max_stretch_atr"),
    (lambda c: c.update(entry_policy={"kind": "chase", "stretch": 1}), "unknown keys"),
])
def test_card_validation_rejects_malformed(mutate, message):
    raw = card()
    mutate(raw)
    with pytest.raises(BasketError, match=message):
        parse_card(raw, require_scores=True)


def test_regime_keys_are_the_regime_services_labels():
    assert len(REGIME_KEYS) == 4 * 3 * 2
    assert {k.split(".")[0] for k in REGIME_KEYS} == {"trend_up", "trend_down", "range", "unknown"}
    assert regime_from_label(minute_label(10, 0, "range", "vol_expansion", True))["key"] == "range.vol_expansion.expiry_day"
    assert regime_from_label(minute_label(10, 0, "trend_down", None))["key"] == "trend_down.vol_normal.non_expiry_day"
    assert regime_from_label({"primary": "sideways"})["key"] == "unknown.vol_normal.non_expiry_day"
    assert preopen_regime(True)["key"] == "unknown.vol_normal.expiry_day"


def test_lab_loader_accepts_good_rejects_bad_entries(tmp_path):
    india = load_basket(INDIA)
    unscored = card("MIX-LAB-B", scores={})
    wrong_market = card("MIX-LAB-C", markets=("BANKNIFTY",))
    path = lab_file(tmp_path, [card(), unscored, wrong_market, card(), "not a card"])
    cards, rejected, until = load_lab_basket(path, india)
    assert list(cards) == ["MIX-LAB-A"] and until == "2026-09-09"
    reasons = {r["index"]: r["reason"] for r in rejected}
    assert "unscored" in reasons[1] and "not instruments" in reasons[2] and "duplicate" in reasons[3]
    assert "mapping" in reasons[4]


@pytest.mark.parametrize("top, message", [
    ({"schema_version": 2}, "schema_version"),
    ({"market": "forex"}, "market"),
    ({"strategies": {"a": 1}}, "list"),
    ({"source": ""}, "source"),
    ({"data_until": None}, "data_until"),
    ({"data_until": "yesterday"}, "data_until"),
])
def test_lab_loader_rejects_malformed_file(tmp_path, top, message):
    with pytest.raises(BasketError, match=message):
        load_lab_basket(lab_file(tmp_path, [card()], **top), load_basket(INDIA))


def test_lab_loader_rejects_nan_and_garbage(tmp_path):
    p = tmp_path / "basket_india.json"
    p.write_text('{"schema_version": 1, "market": "india", "pf": NaN}', encoding="utf-8")
    with pytest.raises(BasketError, match="NaN"):
        load_lab_basket(p, load_basket(INDIA))
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(BasketError, match="unreadable"):
        load_lab_basket(p, load_basket(INDIA))


def test_lab_cards_merge_by_id_and_a_broken_file_is_ignored(tmp_path):
    india = replace(load_basket(INDIA), lab_scores="basket_india.json")
    lab_file(tmp_path, [card(), card("MIX-DEFAULT-BUY", markets=("NIFTY", "SENSEX"))])
    cards, meta = load_lab(india, tmp_path)
    assert meta["found"] and meta["error"] is None and meta["loaded"] == ["MIX-DEFAULT-BUY", "MIX-LAB-A"]
    merged, used = for_session(india, cards, meta, DAY)
    assert used["used"] and merged.cards["MIX-DEFAULT-BUY"].scores[KEY].weight == 0.5  # lab refreshed the yaml card
    (tmp_path / "basket_india.json").write_text("[]", encoding="utf-8")
    cards, meta = load_lab(india, tmp_path)
    assert cards == {} and meta["error"]
    assert for_session(india, cards, meta, DAY)[0] is india


def test_lab_scored_on_the_session_day_or_later_is_ignored(tmp_path):
    """Same rule as the regime service's saved weight state: scores may only use sessions before today."""
    india = replace(load_basket(INDIA), lab_scores="basket_india.json")
    for until, used in (("2026-09-09", True), (DAY, False), ("2026-09-11", False)):
        lab_file(tmp_path, [card()], data_until=until)
        basket, meta = for_session(india, *load_lab(india, tmp_path), DAY)
        assert meta["used"] is used and ("MIX-LAB-A" in basket.cards) is used
        if not used:
            assert "not before" in meta["ignored"]


# ------------------------------------------------------------------ selector


def test_selector_zeroes_failed_parked_and_caps_total_weight():
    cards = [
        card("MIX-A", {KEY: score(weight=0.8, rank=2)}),
        card("MIX-B", {KEY: score(weight=0.6, rank=1)}),
        card("MIX-PARKED", {KEY: score(status="parked")}),
        card("MIX-WATCH", {KEY: score(status="watch")}),
        card("MIX-FX", {KEY: score(status="parked_for_forex_test")}),
        card("MIX-THIN", {KEY: score(trades=5)}),
        card("MIX-PF", {KEY: score(pf=0.9)}),
        card("MIX-LOSS", {KEY: score(net_pnl=-1.0)}),
        card("MIX-DSR", {KEY: score(dsr=0.4)}),
        card("MIX-OTHER-REGIME", {"range.vol_expansion.expiry_day": score()}),
        card("MIX-SENSEX-ONLY", {KEY: score()}, markets=("SENSEX",)),
    ]
    out = select_basket(_basket(cards), "NIFTY", regime())
    by = {r["id"]: r for r in out["strategies"]}
    assert "MIX-SENSEX-ONLY" not in by
    assert [r["id"] for r in out["strategies"][:2]] == ["MIX-B", "MIX-A"]  # lab rank wins over raw weight
    assert by["MIX-B"]["rank"] == 1 and by["MIX-A"]["rank"] == 2
    assert out["scaled"] and 1.0 - 2e-6 <= out["total_weight"] <= 1.0  # 0.8 + 0.6 capped to 1.0, rounded down
    assert by["MIX-A"]["weight"] == pytest.approx(0.8 / 1.4, abs=1e-6)
    assert by["MIX-B"]["weight"] == pytest.approx(0.6 / 1.4, abs=1e-6)
    assert {k: by[k]["reason"] for k in by if by[k]["weight"] == 0} == {
        "MIX-PARKED": "status_parked", "MIX-WATCH": "status_watch", "MIX-FX": "status_parked_for_forex_test",
        "MIX-THIN": "failed_min_trades", "MIX-PF": "failed_pf", "MIX-LOSS": "failed_net_pnl",
        "MIX-DSR": "failed_dsr", "MIX-OTHER-REGIME": "unscored_regime",
    }
    assert all(by[k]["rank"] is None for k in by if by[k]["weight"] == 0)
    unknown = select_basket(_basket(cards), "NIFTY", {"key": None})
    assert unknown["total_weight"] == 0 and not unknown["active"]
    assert {r["reason"] for r in unknown["strategies"]} == {"regime_unknown"}


def test_selector_entry_policy_modes():
    cards = [card("MIX-CHASE", {KEY: score(weight=0.4, rank=1)}, policy=CHASE),
             card("MIX-PULL", {KEY: score(weight=0.2, rank=1)})]
    by = lambda out: {r["id"]: r for r in out["strategies"]}  # noqa: E731
    log_only = select_basket(_basket(cards), "NIFTY", regime())
    assert log_only["entry_mode"] == "log_only"
    assert by(log_only)["MIX-CHASE"]["weight"] == 0.4 and "would" in by(log_only)["MIX-CHASE"]["entry_note"]
    assert [r["id"] for r in log_only["strategies"]] == ["MIX-CHASE", "MIX-PULL"]
    prefer = select_basket(_basket(cards, mode="prefer"), "NIFTY", regime())
    assert by(prefer)["MIX-CHASE"]["weight"] == pytest.approx(0.2) and by(prefer)["MIX-CHASE"]["reason"] == "selected"
    assert [r["id"] for r in prefer["strategies"]] == ["MIX-PULL", "MIX-CHASE"]  # non-chasing first at equal rank
    require = select_basket(_basket(cards, mode="require"), "NIFTY", regime())
    assert by(require)["MIX-CHASE"]["weight"] == 0 and by(require)["MIX-CHASE"]["reason"] == "entry_policy_chase"
    assert by(require)["MIX-PULL"]["weight"] == 0.2 and by(require)["MIX-PULL"]["entry_policy"]["zone"] == "fvg"


def test_selector_is_deterministic_regardless_of_card_order():
    cards = [card(f"MIX-{n}", {KEY: score(weight=0.1 * n, rank=1 + n % 3)}) for n in range(1, 9)]
    first = json.dumps(select_basket(_basket(cards), "NIFTY", regime()), sort_keys=True)
    for seed in range(5):
        shuffled = copy.deepcopy(cards)
        random.Random(seed).shuffle(shuffled)
        assert json.dumps(select_basket(_basket(shuffled), "NIFTY", regime()), sort_keys=True) == first


# ------------------------------------------------------------------ entry location (zones, distance, verdict)


def bar(n, o, h, lo, c, vol=None):
    return {"ts": _ts(10, 0) + 60 * n, "open": o, "high": h, "low": lo, "close": c, "volume": vol}


def test_zone_finders():
    ce_gap = [bar(0, 100, 101, 99, 100.5), bar(1, 100.5, 104, 100.4, 103.8), bar(2, 103.8, 105, 102, 104.5)]
    assert last_fvg(ce_gap, "CE") == (101.0, 102.0) and last_fvg(ce_gap, "PE") is None
    pe_gap = [bar(0, 100, 101, 99, 99.5), bar(1, 99.5, 99.6, 95, 95.2), bar(2, 95.2, 97, 94, 94.5)]
    assert last_fvg(pe_gap, "PE") == (97.0, 99.0)
    assert impulse_mid(ce_gap, "CE", atr=2.0, mult=1.5) == (103.5, 103.5)  # most recent: bar 2, range 3 >= 3
    assert impulse_mid(ce_gap, "CE", atr=2.0, mult=1.6) == (102.2, 102.2)  # only bar 1 (range 3.6) >= 3.2
    assert impulse_mid(ce_gap, "PE", atr=2.0, mult=1.5) is None
    by_vol = [bar(0, 1, 1, 1, 100.2, 10), bar(1, 1, 1, 1, 103.1, 50), bar(2, 1, 1, 1, 100.7, 10)]
    assert point_of_control(by_vol, 1.0) == (103.0, 104.0)
    no_vol = [dict(b, volume=None) for b in by_vol]
    assert point_of_control(no_vol, 1.0) == (100.0, 101.0)  # time at price when the tape has no volume
    assert stretch_atr(106.0, (101.0, 102.0), "CE", 2.0) == 2.0
    assert stretch_atr(101.5, (101.0, 102.0), "CE", 2.0) == 0.0
    assert stretch_atr(95.0, (97.0, 99.0), "PE", 1.0) == 2.0 and stretch_atr(100.0, (97.0, 99.0), "PE", 1.0) == -1.0


def _cfg(**kw):
    return {**load_basket(INDIA).entry, **kw}


def _impulse_tape(extra_close=112.0):
    """20 quiet bars around 100, then a CE impulse that leaves an FVG, then the forming minute."""
    bars = [bar(n, 100, 100.6, 99.6, 100.1 + (n % 2) * 0.2, 100) for n in range(20)]
    bars += [bar(20, 100.2, 100.5, 100.0, 100.4, 100), bar(21, 100.4, 104.5, 100.3, 104.4, 300),
             bar(22, 104.4, 106.0, 103.0, 105.8, 200), bar(23, 105.8, 200.0, 50.0, extra_close, 1)]
    return bars


def test_measure_uses_only_closed_bars_and_the_nearest_zone_behind_the_price():
    now = _ts(10, 23) + 30  # 30 s into minute 23: bars 0..22 are closed
    sig = measure(_impulse_tape(), now, 107.0, "CE", _cfg())
    assert sig["n_bars"] == 23 and sig["atr"] is not None
    assert sig["zones"]["fvg"]["lo"] == 100.5 and sig["zones"]["fvg"]["hi"] == 103.0
    behind = {k: z["distance_atr"] for k, z in sig["zones"].items() if z and z["distance_atr"] >= 0}
    assert len(behind) >= 2 and sig["entry_distance_atr"] == min(behind.values()) > 0
    assert sig["zone_type"] == min(behind, key=behind.get)
    assert measure(_impulse_tape(extra_close=1.0), now, 107.0, "CE", _cfg()) == sig  # forming minute ignored
    below = measure(_impulse_tape(), now, 99.0, "CE", _cfg())
    assert all(z is None or z["distance_atr"] < 0 for z in below["zones"].values())
    assert below["entry_distance_atr"] is None and below["zone_type"] is None  # zones ahead are never picked


def test_verdicts_log_vetoes_and_never_enforce():
    now = _ts(10, 23) + 30
    sig = measure(_impulse_tape(), now, 107.0, "CE", _cfg())
    d = sig["entry_distance_atr"]
    chase = verdict({"kind": "chase"}, sig, _cfg(max_stretch_atr=d / 2))
    assert chase["action"] == "VETO_STRETCHED" and chase["veto_reason"].startswith("STRETCHED_ENTRY")
    assert verdict({"kind": "chase", "max_stretch_atr": d * 2}, sig, _cfg(max_stretch_atr=d / 2))["action"] == "ENTER"
    pull = verdict({"kind": "pullback_limit", "zone": "fvg", "timeout_bars": 3}, sig, _cfg(max_stretch_atr=d / 2))
    assert pull["action"] == "WAIT_PULLBACK" and pull["limit_index_level"] == 103.0 and pull["veto_reason"] is None
    wait = verdict({"kind": "wait_consolidation"}, sig, _cfg(max_stretch_atr=d / 2))
    assert wait["action"] == "WAIT_CONSOLIDATION"
    req = verdict({"kind": "chase"}, sig, _cfg(mode="require"))
    assert req["action"] == "CHASE_NOT_ALLOWED" and req["veto_reason"] == "CHASE_POLICY_NOT_ALLOWED"
    assert verdict({"kind": "chase"}, sig, _cfg(max_stretch_atr=None))["action"] == "ENTER"  # no cap configured
    below = measure(_impulse_tape(), now, 99.0, "CE", _cfg())
    assert verdict({"kind": "chase"}, below, _cfg())["action"] == "NO_ZONE_BEHIND"
    thin = measure(_impulse_tape()[:5], _ts(10, 5), 100.0, "CE", _cfg())
    assert verdict({"kind": "chase"}, thin, _cfg())["action"] == "DATA_INSUFFICIENT"
    assert all(v["enforced"] is False for v in (chase, pull, wait, req))


# ------------------------------------------------------------------ no look-ahead on regime inputs


def test_a_label_for_a_minute_still_forming_is_refused(tmp_path):
    shadow = BasketShadow([load_basket(INDIA)], out_dir=tmp_path)
    shadow.pre_open("NIFTY", _ts(9, 15), expiry_day=False)
    with pytest.raises(ValueError, match="not complete"):
        shadow.on_label(minute_label(10, 0), _ts(10, 0) + 59)  # 10:00 bar closes at 10:01:00
    assert len(shadow.rows) == 1
    assert shadow.on_label(minute_label(10, 0), _ts(10, 1))["regime"]["key"] == KEY
    assert shadow.on_label(minute_label(10, 1), _ts(10, 2)) is None  # same key: no new row
    assert shadow.on_label({"scope": "intermarket", "session_date": DAY}, _ts(10, 2)) is None


def test_basket_errors_never_reach_the_bus_or_the_entry_path(tmp_path):
    bus = MemoryBus()
    bridge = BasketBus(BasketShadow([load_basket(INDIA)], out_dir=tmp_path), bus, engine=None)
    bus.publish("MARKET_TICK", {"key": "x", "underlying": "NIFTY", "ts": _ts(10, 0) + 30}, source="feed")
    bus.publish("REGIME_LABEL", {**minute_label(10, 0), "ts": "garbage"}, source="regime")
    bus.publish("REGIME_LABEL", minute_label(10, 0), source="regime")  # 10:00 bar not closed at 10:00:30
    assert bus.errors == [] and len(bridge.errors) == 2


def _replay(fx, root, **kw):
    return ps.replay_paper_scalp(**fixture_replay_kwargs(fx, Path(root)), write=False, **kw)


def _shadow(out):
    return BasketShadow([load_basket(INDIA), load_basket(FOREX)], out_dir=Path(out))


@pytest.fixture()
def fx(monkeypatch):
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "fixture"))
    monkeypatch.delenv("USE_BASKET_SELECTOR", raising=False)
    monkeypatch.delenv(ps.USE_EVENT_BUS_ENV, raising=False)
    return load_fixture(FIXTURE)


def test_changing_the_future_does_not_change_earlier_basket_rows(fx, tmp_path):
    fx["triples"] = fx["triples"][:900]
    cut = fx["triples"][500].ts
    a = _shadow(tmp_path / "a")
    _replay(fx, tmp_path / "ra", event_session=BasketEventSession(basket=a))
    future = copy.deepcopy(fx)
    future["triples"] = fx["triples"][:501] + [
        Triple(**{**t.__dict__, "idx_close": t.idx_close * (1.02 if n % 2 else 0.98)})
        for n, t in enumerate(fx["triples"][501:])
    ]
    b = _shadow(tmp_path / "b")
    _replay(future, tmp_path / "rb", event_session=BasketEventSession(basket=b))
    early = lambda s: [r for r in s.rows if r["ts"] <= cut]  # noqa: E731
    assert len(early(a)) >= 3 and early(a) == early(b)
    assert any(r["trigger"] == "signal" for r in early(a)), "signal rows (entry distance) are covered too"
    assert a.rows != b.rows, "the perturbation must actually change later labels"


# ------------------------------------------------------------------ off by default = byte-identical


@pytest.fixture(scope="module")
def replays(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("basket")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ps, "load_index_closes", lambda u, root=None: {})
        mp.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "fixture"))
        mp.delenv("USE_BASKET_SELECTOR", raising=False)
        mp.delenv(ps.USE_EVENT_BUS_ENV, raising=False)
        fx = load_fixture(FIXTURE)
        shadow_1, shadow_2 = _shadow(tmp / "s1"), _shadow(tmp / "s2")
        default_session = BasketEventSession()  # no basket argument: reads config/baskets/selector.yaml (off)
        return {
            "monolith": _replay(fx, tmp / "r0", use_event_bus=False),
            "event_main": _replay(fx, tmp / "r1", event_session=EventSession()),
            "event_default": _replay(fx, tmp / "r2", event_session=default_session),
            "event_on": _replay(fx, tmp / "r3", event_session=BasketEventSession(basket=shadow_1)),
            "event_on_again": _replay(fx, tmp / "r4", event_session=BasketEventSession(basket=shadow_2)),
            "default_session": default_session, "shadows": (shadow_1, shadow_2),
        }


def test_flag_off_is_the_default():
    settings = load_settings(REPO)
    assert settings["enabled"] is False
    assert shadow_from_settings(settings, root=REPO) is None
    assert attach_from_settings(MemoryBus(), engine=None, root=REPO) is None


def test_off_by_default_replay_is_byte_identical_and_on_changes_no_trade(replays):
    dump = lambda b: json.dumps(  # noqa: E731
        {k: b.get(k) for k in ("closed_trades", "open_trades", "skip_reason_counts")}, sort_keys=True, default=str)
    assert len(replays["monolith"]["closed_trades"]) >= 5
    assert replays["default_session"].basket_bus is None
    assert "basket_shadow" not in replays["event_default"]["event_bus"]
    assert (dump(replays["monolith"]) == dump(replays["event_main"]) == dump(replays["event_default"])
            == dump(replays["event_on"]))
    events = replays["event_main"]["event_bus"]["events"]
    assert events == replays["event_default"]["event_bus"]["events"] == replays["event_on"]["event_bus"]["events"]
    on = replays["event_on"]["event_bus"]
    assert on["handler_errors"] == [] and on["basket_shadow"]["errors"] == []
    assert on["basket_shadow"]["labels_seen"] >= 5 and on["basket_shadow"]["rows"] >= 5


def test_every_boss_ticket_gets_an_entry_location_row(replays):
    rows = [r for r in replays["shadows"][0].rows if r["trigger"] == "signal"]
    n_tickets = replays["event_on"]["event_bus"]["events"]["ENTRY_APPROVED"]
    assert n_tickets >= 5 and len(rows) == n_tickets
    tickets = {r["trade_id"] for r in replays["event_on"]["closed_trades"]}
    assert {r["signal"]["trade_id"] for r in rows} <= tickets
    for r in rows:
        s = r["signal"]
        assert {"entry_distance_atr", "zone_type", "zones", "atr"} <= set(s) and s["side"] in ("CE", "PE")
        assert s["entry_distance_atr"] is None or s["entry_distance_atr"] >= 0
        v = r["verdicts"]["MIX-DEFAULT-BUY"]
        assert v["policy"] == "chase" and v["enforced"] is False and r["places_orders"] is False
        assert (v["action"] == "VETO_STRETCHED") == ("MIX-DEFAULT-BUY" in r["vetoes"])
    assert any(r["vetoes"] for r in rows), "the placeholder cap should flag at least one stretched legacy entry"


def test_every_row_uses_only_minutes_closed_before_its_tick(replays):
    rows = [r for r in replays["shadows"][0].rows if r["trigger"] != "signal"]
    assert rows[0]["trigger"] == "pre_open" and rows[0]["regime"]["key"].startswith("unknown.")
    changes = rows[1:]
    assert changes and all(r["trigger"] == "regime_change" and r["regime"]["source"] == "regime_service" for r in changes)
    assert all(r["regime"]["label_ts"] + 60 <= r["ts"] for r in changes)
    assert all(a["regime"]["key"] != b["regime"]["key"] for a, b in zip(rows, rows[1:]) if a["underlying"] == b["underlying"])


def test_shadow_log_is_deterministic_and_says_no_orders(replays):
    s1, s2 = replays["shadows"]
    f1, f2 = (Path(s.out_dir) / f"{DAY}.jsonl" for s in (s1, s2))
    assert f1.read_bytes() == f2.read_bytes()
    rows = [json.loads(line) for line in f1.read_text(encoding="utf-8").splitlines()]
    assert all(r["shadow"] is True and r["places_orders"] is False for r in rows)
    assert all(r["basket"]["total_weight"] <= r["basket"]["cap"] for r in rows if r["trigger"] != "signal")
    s1._seen.clear()
    s1._write(rows[0]["day"], s1.rows[0])  # a re-replay (live loop) must not append the same row twice
    assert len(f1.read_text(encoding="utf-8").splitlines()) == len(rows)


def _board(board):
    return json.dumps(
        {k: board.get(k) for k in ("closed_trades", "open_trades", "skip_reason_counts")},
        sort_keys=True, default=str)


def test_shadow_log_off_basket_off_matches_the_legacy_replay(fx, tmp_path, monkeypatch):
    """SHADOW_LOG=0 and the selector off: BasketEventSession is the legacy board, byte for byte."""
    monkeypatch.setenv("SHADOW_LOG", "0")
    monkeypatch.delenv("USE_BASKET_SELECTOR", raising=False)
    monkeypatch.delenv(ps.USE_EVENT_BUS_ENV, raising=False)
    fx["triples"] = fx["triples"][:600]
    legacy = _replay(fx, tmp_path / "legacy", use_event_bus=False)
    session = BasketEventSession()
    hooked = _replay(fx, tmp_path / "hooked", event_session=session)
    assert session.basket_bus is None
    assert _board(legacy) == _board(hooked)
    assert "basket_shadow" not in (hooked.get("event_bus") or {})
    assert list((tmp_path / "hooked").glob("data/shadow/**/*.jsonl")) == []


def test_main_baseline_quotes_and_no_tapes_is_not_a_pass(tmp_path, monkeypatch):
    assert MAIN_REPLAY_BASELINES == (
        ("NIFTY", ("NIFTY",), 63, -96190.79),
        ("ALL", ("NIFTY", "BANKNIFTY", "SENSEX"), 140, -27022.54),
    )
    assert MAIN_LAB_BASELINE == ("LAB_P2C", 36, 110000.29)
    monkeypatch.setenv("SHADOW_LOG", "1")
    monkeypatch.setenv("USE_BASKET_SELECTOR", "1")
    monkeypatch.setenv("USE_EVENT_BUS", "1")
    empty = legacy_replay_total(tmp_path, ("NIFTY",))
    assert empty["n_trades"] == 0 and empty["days"] == [] and empty["shadow_log"] == "0"
    assert os.environ["SHADOW_LOG"] == "1" and os.environ["USE_BASKET_SELECTOR"] == "1"
    report = check_main_baselines(tmp_path)
    assert report["ok"] is None and report["reason"] == "no_tapes" and report["runs"] == []
    assert report["lab"]["expected_trades"] == 36 and report["lab"]["expected_net_pnl_inr"] == 110000.29
    assert "not replay_paper_scalp" in report["lab"]["reason"]


def test_parity_helper_reports_parity_and_writes_nothing_to_the_repo(fx, tmp_path):
    fx["triples"] = fx["triples"][:600]
    before = sorted((REPO / "data" / "shadow" / "basket").glob("*.jsonl"))
    rep = basket_parity(**fixture_replay_kwargs(fx, tmp_path))
    assert rep["ok"] and rep["problems"] == [] and rep["old"] == rep["new"]
    assert rep["basket"]["rows"] >= 2 and rep["basket"]["errors"] == []
    assert sorted((REPO / "data" / "shadow" / "basket").glob("*.jsonl")) == before


def test_founder_switch_turns_it_off_entirely(tmp_path, monkeypatch):
    founder = tmp_path / "data" / "shadow" / "basket" / "FOUNDER_OFF"
    settings = {"enabled": True, "founder_off_file": "data/shadow/basket/FOUNDER_OFF",
                "baskets": [str(INDIA), str(FOREX)], "out_dir": "out"}
    monkeypatch.delenv("USE_BASKET_SELECTOR", raising=False)
    assert shadow_from_settings(settings, root=tmp_path) is not None
    monkeypatch.setenv("USE_BASKET_SELECTOR", "0")
    assert shadow_from_settings(settings, root=tmp_path) is None
    monkeypatch.delenv("USE_BASKET_SELECTOR")
    shadow = shadow_from_settings(settings, root=tmp_path)
    founder.parent.mkdir(parents=True)
    founder.write_text("off\n", encoding="utf-8")
    assert shadow_from_settings(settings, root=tmp_path) is None
    assert shadow.pre_open("NIFTY", _ts(9, 16), expiry_day=False) is None  # mid-session too
    assert shadow.on_label(minute_label(10, 0), _ts(10, 1)) is None and shadow.rows == []


# ------------------------------------------------------------------ forex stays parked


def test_forex_basket_loads_but_never_activates(tmp_path):
    forex = load_basket(FOREX)
    fx_card = card("MIX-FX-TREND", {KEY: score()}, markets=("EURUSD",))
    loaded = replace(forex, cards={"MIX-FX-TREND": parse_card(fx_card, require_scores=True)})
    out = select_basket(loaded, "EURUSD", regime())
    assert not out["active"] and out["total_weight"] == 0
    assert [r["reason"] for r in out["strategies"]] == ["basket_parked"]
    shadow = BasketShadow([load_basket(INDIA), loaded], out_dir=tmp_path)
    assert "EURUSD" not in shadow.by_und
    assert shadow.pre_open("EURUSD", _ts(10, 0), expiry_day=False) is None
    assert shadow.on_label(minute_label(10, 0, und="EURUSD"), _ts(10, 1)) is None
    settings = {"enabled": True, "baskets": [str(INDIA), str(FOREX)], "out_dir": str(tmp_path / "out")}
    live = shadow_from_settings(settings, root=tmp_path)
    assert {b.market for b in live.baskets} == {"india", "forex"} and set(live.by_und) == {"NIFTY", "SENSEX"}

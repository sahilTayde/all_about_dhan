"""Basket selector: schema, lab loader, selector determinism, no look-ahead, off-by-default parity, forex parked."""

import copy
import json
import random
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

import desk_ml.paper_scalp as ps
from boss.basket import (
    IST, REGIME_KEYS, BasketError, BasketShadow, intraday_regime, load_basket, load_lab_basket, parse_card,
    preopen_regime, select_basket, shadow_from_settings, with_lab,
)
from desk_ml.event_parity import fixture_replay_kwargs, load_fixture
from desk_ml.event_path import EventSession, _read_yaml
from desk_ml.features import Triple

REPO = Path(__file__).resolve().parents[3]
INDIA, FOREX = REPO / "config" / "baskets" / "india.yaml", REPO / "config" / "baskets" / "forex.yaml"
FIXTURE = REPO / "packages" / "desk-ml" / "tests" / "fixtures" / "synthetic_session_nifty.json"
KEY = "trend.low_vol.non_expiry"


def score(**kw):
    base = {"net_pnl": 50000.0, "pf": 1.6, "trades": 80, "win_rate": 0.52, "dsr": 0.97, "weight": 0.5, "rank": 1,
            "status": "active_candidate"}
    return {**base, **kw}


def card(cid="MIX-LAB-A", scores=None, markets=("NIFTY",)):
    return {
        "id": cid, "source": {"kind": "trader", "ref": "lab run 42"}, "markets": list(markets),
        "adaptations": {markets[0]: {"stop_frac": 0.35}},
        "rules": {"entry": {"signal": "orb_break", "minutes": 15}, "exit": {"stop_frac": 0.4, "target_frac": 0.55},
                  "strike": {"premium": "ITM", "depth": 1}, "sizing": {"lots": 25}, "skip": {"sideways": True}},
        "param_ranges": {"stop_frac": [0.3, 0.35, 0.4]},
        "scores": {KEY: score()} if scores is None else scores,
    }


def lab_file(tmp, cards, **top):
    blob = {"schema_version": 1, "market": "india", "generated_at": "2026-09-26T18:00:00+05:30",
            "source": "scripts/lab run 42", "strategies": cards, **top}
    path = Path(tmp) / "basket_india.json"
    path.write_text(json.dumps(blob), encoding="utf-8")
    return path


def regime(key=KEY):
    t, v, e = key.split(".")
    return {"trend": t, "vol": v, "expiry": e, "key": key}


# ------------------------------------------------------------------ schema


def test_committed_baskets_load_and_validate():
    india, forex = load_basket(INDIA), load_basket(FOREX)
    assert india.activatable and sorted(india.instruments) == ["NIFTY", "SENSEX"]
    assert india.instruments["NIFTY"].expiry_weekday == "TUE" and india.instruments["NIFTY"].lot_size == 65
    assert "MIX-DEFAULT-BUY" in india.cards
    assert not forex.activatable and "EURUSD" in forex.instruments
    text = INDIA.read_text(encoding="utf-8") + FOREX.read_text(encoding="utf-8")
    assert "Source:" in text and "TODO(verify)" in text


@pytest.mark.parametrize("mutate, message", [
    (lambda c: c.update(id="bad id"), "id"),
    (lambda c: c["source"].update(kind="guru"), "source"),
    (lambda c: c["rules"].pop("skip"), "rules"),
    (lambda c: c["rules"].update(entry={}), "exact parameters"),
    (lambda c: c["scores"].update({"sideways.low_vol.expiry": score()}), "regime key"),
    (lambda c: c["scores"][KEY].update(status="live"), "status"),
    (lambda c: c["scores"][KEY].update(win_rate=1.5), "win_rate"),
    (lambda c: c["scores"][KEY].update(trades=10.5), "trades"),
    (lambda c: c["scores"][KEY].update(pf=float("inf")), "finite"),
    (lambda c: c["scores"][KEY].pop("dsr"), "unscored"),
    (lambda c: c.update(scores={}), "unscored"),
    (lambda c: c.update(stoploss=5), "unknown keys"),
    (lambda c: c["param_ranges"].update(stop_frac=[]), "param_ranges"),
    (lambda c: c.update(adaptations={"BANKNIFTY": {}}), "adaptations"),
])
def test_card_validation_rejects_malformed(mutate, message):
    raw = card()
    mutate(raw)
    with pytest.raises(BasketError, match=message):
        parse_card(raw, require_scores=True)


def test_every_regime_key_is_trend_vol_expiry():
    assert len(REGIME_KEYS) == 8 and all(k.count(".") == 2 for k in REGIME_KEYS)


def test_lab_loader_accepts_good_rejects_bad_entries(tmp_path):
    india = load_basket(INDIA)
    unscored = card("MIX-LAB-B", scores={})
    wrong_market = card("MIX-LAB-C", markets=("BANKNIFTY",))
    path = lab_file(tmp_path, [card(), unscored, wrong_market, card(), "not a card"])
    cards, rejected = load_lab_basket(path, india)
    assert list(cards) == ["MIX-LAB-A"]
    reasons = {r["index"]: r["reason"] for r in rejected}
    assert "unscored" in reasons[1] and "not instruments" in reasons[2] and "duplicate" in reasons[3]
    assert "mapping" in reasons[4]


@pytest.mark.parametrize("top, message", [
    ({"schema_version": 2}, "schema_version"),
    ({"market": "forex"}, "market"),
    ({"strategies": {"a": 1}}, "list"),
    ({"source": ""}, "source"),
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


def test_with_lab_merges_by_id_and_ignores_a_broken_file(tmp_path):
    from dataclasses import replace

    india = replace(load_basket(INDIA), lab_scores="basket_india.json")
    lab_file(tmp_path, [card(), card("MIX-DEFAULT-BUY", markets=("NIFTY", "SENSEX"))])
    merged, meta = with_lab(india, tmp_path)
    assert meta["found"] and meta["error"] is None and meta["loaded"] == ["MIX-DEFAULT-BUY", "MIX-LAB-A"]
    assert merged.cards["MIX-DEFAULT-BUY"].scores[KEY].weight == 0.5  # lab refreshed the yaml card
    (tmp_path / "basket_india.json").write_text("[]", encoding="utf-8")
    same, meta = with_lab(india, tmp_path)
    assert same is india and meta["error"]


# ------------------------------------------------------------------ selector


def _basket(cards):
    from dataclasses import replace

    return replace(load_basket(INDIA), cards={c["id"]: parse_card(c, require_scores=False) for c in cards})


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
        card("MIX-OTHER-REGIME", {"chop.high_vol.expiry": score()}),
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
    assert out["total_weight"] <= out["cap"]
    assert {k: by[k]["reason"] for k in by if by[k]["weight"] == 0} == {
        "MIX-PARKED": "status_parked", "MIX-WATCH": "status_watch", "MIX-FX": "status_parked_for_forex_test",
        "MIX-THIN": "failed_min_trades", "MIX-PF": "failed_pf", "MIX-LOSS": "failed_net_pnl",
        "MIX-DSR": "failed_dsr", "MIX-OTHER-REGIME": "unscored_regime",
    }
    assert all(by[k]["rank"] is None for k in by if by[k]["weight"] == 0)
    unknown = select_basket(_basket(cards), "NIFTY", {"key": None})
    assert unknown["total_weight"] == 0 and not unknown["active"]
    assert {r["reason"] for r in unknown["strategies"]} == {"regime_unknown"}


def test_selector_is_deterministic_regardless_of_card_order():
    cards = [card(f"MIX-{n}", {KEY: score(weight=0.1 * n, rank=1 + n % 3)}) for n in range(1, 9)]
    first = json.dumps(select_basket(_basket(cards), "NIFTY", regime()), sort_keys=True)
    for seed in range(5):
        shuffled = copy.deepcopy(cards)
        random.Random(seed).shuffle(shuffled)
        assert json.dumps(select_basket(_basket(shuffled), "NIFTY", regime()), sort_keys=True) == first


# ------------------------------------------------------------------ regime inputs: no look-ahead


def _ts(hh, mm, day="2026-09-10"):
    y, m, d = map(int, day.split("-"))
    return int(datetime(y, m, d, hh, mm, tzinfo=IST).timestamp())


def test_preopen_labels_ignore_today_and_later_rows():
    india = load_basket(INDIA)
    prior = [{"date": f"2026-08-{d:02d}", "close": 25000 + 40 * d} for d in range(10, 30)]
    base = preopen_regime(prior, "2026-09-10", india.instruments["NIFTY"], india.regime)
    assert base["key"] == "trend.low_vol.non_expiry" and base["inputs"]["last_day"] == "2026-08-29"
    future = prior + [{"date": "2026-09-10", "close": 1.0}, {"date": "2026-09-11", "close": 99999.0}]
    assert preopen_regime(future, "2026-09-10", india.instruments["NIFTY"], india.regime) == base
    tuesday = preopen_regime(prior, "2026-09-08", india.instruments["NIFTY"], india.regime)
    assert tuesday["expiry"] == "expiry"


def test_intraday_labels_use_only_closed_minutes():
    india = load_basket(INDIA)
    inst, cfg = india.instruments["NIFTY"], india.regime
    bars = [{"ts": _ts(9, 15) + 60 * n, "close": 25000 + (n % 4)} for n in range(40)]
    now = bars[35]["ts"] + 20  # 20 s into minute 35: bars 0..34 are closed
    base = intraday_regime(bars[:36], now, "2026-09-10", inst, cfg)
    assert base["inputs"]["last_bar_ts"] == bars[34]["ts"] and base["key"] is not None
    spoiled = [dict(b) for b in bars]
    for b in spoiled[35:]:
        b["close"] = 30000.0  # the forming minute and everything after it
    assert intraday_regime(spoiled, now, "2026-09-10", inst, cfg) == base


def _replay(fx, root, **kw):
    return ps.replay_paper_scalp(**fixture_replay_kwargs(fx, Path(root)), write=False, **kw)


@pytest.fixture()
def fx(monkeypatch):
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "fixture"))
    monkeypatch.delenv("USE_BASKET_SELECTOR", raising=False)
    monkeypatch.delenv(ps.USE_EVENT_BUS_ENV, raising=False)
    return load_fixture(FIXTURE)


def _shadow(out):
    return BasketShadow([load_basket(INDIA), load_basket(FOREX)], out_dir=Path(out))


def test_changing_the_future_does_not_change_earlier_basket_rows(fx, tmp_path):
    fx["triples"] = fx["triples"][:600]
    cut = fx["triples"][400].ts
    a = _shadow(tmp_path / "a")
    _replay(fx, tmp_path / "ra", event_session=EventSession(basket=a))
    future = copy.deepcopy(fx)
    future["triples"] = fx["triples"][:401] + [
        Triple(**{**t.__dict__, "idx_close": t.idx_close * (1.02 if n % 2 else 0.98)})
        for n, t in enumerate(fx["triples"][401:])
    ]
    b = _shadow(tmp_path / "b")
    _replay(future, tmp_path / "rb", event_session=EventSession(basket=b))
    early = lambda s: [r for r in s.rows if r["ts"] <= cut]  # noqa: E731
    assert len(early(a)) >= 3 and early(a) == early(b)
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
        off_session = EventSession()  # no basket argument: reads config/event_path.yaml, where it is off
        return {
            "monolith": _replay(fx, tmp / "r0", use_event_bus=False),
            "event_off": _replay(fx, tmp / "r1", event_session=off_session),
            "event_on": _replay(fx, tmp / "r2", event_session=EventSession(basket=shadow_1)),
            "event_on_again": _replay(fx, tmp / "r3", event_session=EventSession(basket=shadow_2)),
            "off_session": off_session, "shadows": (shadow_1, shadow_2),
        }


def test_flag_off_is_the_default():
    settings = _read_yaml(REPO / "config" / "event_path.yaml")
    assert settings["basket_selector"]["enabled"] is False
    assert shadow_from_settings(settings, root=REPO) is None


def test_off_by_default_replay_is_byte_identical_and_on_changes_no_trade(replays):
    dump = lambda b: json.dumps(  # noqa: E731
        {k: b.get(k) for k in ("closed_trades", "open_trades", "skip_reason_counts")}, sort_keys=True, default=str)
    assert len(replays["monolith"]["closed_trades"]) >= 5
    assert replays["off_session"].boss.basket is None
    assert "basket_shadow" not in replays["event_off"]["event_bus"]
    assert dump(replays["monolith"]) == dump(replays["event_off"]) == dump(replays["event_on"])
    assert replays["event_off"]["event_bus"]["events"] == replays["event_on"]["event_bus"]["events"]
    assert replays["event_on"]["event_bus"]["basket_shadow"]["rows"] >= 2


def test_shadow_log_is_deterministic_and_says_no_orders(replays):
    s1, s2 = replays["shadows"]
    f1, f2 = (Path(s.out_dir) / "2026-09-10.jsonl" for s in (s1, s2))
    assert f1.read_bytes() == f2.read_bytes()
    rows = [json.loads(line) for line in f1.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["trigger"] == "pre_open" and {r["trigger"] for r in rows[1:]} == {"regime_change"}
    assert all(r["shadow"] is True and r["places_orders"] is False for r in rows)
    assert all(r["basket"]["total_weight"] <= r["basket"]["cap"] for r in rows)
    s1._seen.clear()
    s1._write(rows[0]["day"], s1.rows[0])  # a re-replay (live loop) must not append the same row twice
    assert len(f1.read_text(encoding="utf-8").splitlines()) == len(rows)


def test_founder_switch_turns_it_off_entirely(tmp_path, monkeypatch):
    founder = tmp_path / "data" / "founder" / "basket_selector_off"
    settings = {"basket_selector": {"enabled": True, "founder_off_file": "data/founder/basket_selector_off",
                                    "baskets": [str(INDIA), str(FOREX)], "out_dir": "out"}}
    assert shadow_from_settings(settings, root=tmp_path) is not None
    monkeypatch.setenv("USE_BASKET_SELECTOR", "0")
    assert shadow_from_settings(settings, root=tmp_path) is None
    monkeypatch.delenv("USE_BASKET_SELECTOR")
    shadow = shadow_from_settings(settings, root=tmp_path)
    founder.parent.mkdir(parents=True)
    founder.write_text("off\n", encoding="utf-8")
    assert shadow_from_settings(settings, root=tmp_path) is None
    assert shadow.on_tick("NIFTY", _ts(9, 16), [], []) is None and shadow.rows == []  # mid-session too


# ------------------------------------------------------------------ forex stays parked


def test_forex_basket_loads_but_never_activates(tmp_path):
    from dataclasses import replace

    forex = load_basket(FOREX)
    fx_card = card("MIX-FX-TREND", {KEY: score()}, markets=("EURUSD",))
    loaded = replace(forex, cards={"MIX-FX-TREND": parse_card(fx_card, require_scores=True)})
    out = select_basket(loaded, "EURUSD", regime())
    assert not out["active"] and out["total_weight"] == 0
    assert [r["reason"] for r in out["strategies"]] == ["basket_parked"]
    shadow = BasketShadow([load_basket(INDIA), loaded], out_dir=tmp_path)
    assert "EURUSD" not in shadow.by_und and shadow.on_tick("EURUSD", _ts(10, 0), [], []) is None
    with tempfile.TemporaryDirectory() as tmp:
        settings = {"basket_selector": {"enabled": True, "baskets": [str(INDIA), str(FOREX)], "out_dir": tmp}}
        live = shadow_from_settings(settings, root=REPO)
    assert {b.market for b in live.baskets} == {"india", "forex"} and set(live.by_und) == {"NIFTY", "SENSEX"}

"""PR-B paper cost model (desk_ml.costs): legacy identity, fills, resting targets, stale-quote guard,
BSE fee, trade-through limits. Synthetic data only. Paper only; no broker is called."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import desk_ml.paper_scalp as ps
from desk_ml import costs
from desk_ml.event_parity import load_fixture, run_parity, synthetic_triples
from desk_ml.features import Triple
from desk_ml.founder_session import save_founder_book

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_session_nifty.json"
REPO = Path(__file__).resolve().parents[3]
LOTS = {"NIFTY": 65, "SENSEX": 20, "BANKNIFTY": 30}
# canonical(board) after Dhan/NSE FA/73061 paper rates (txn 0.000355299 + IPFT). Charges-only move.
LEGACY_SHA = {
    "fixture": "002966884f2a25cece9c15fd7de0f032d7635ad688a7b499a184d60087f042f9",
    "nifty_sensex": "b18383da257b091c9794a5918ba37038c6f3b54cdbc7ddace0e290eed785c77c",
}
REALISTIC_KEYS = {"cost_model", "decision_entry", "decision_exit", "slippage_inr", "quote_src", "quote_age_s",
                  "exit_pending_since_ts"}
SLIPPAGE_ONLY = dict(target_fill="market_at_poll", exit_quote_max_age_s=None, exchange_fees="nse_flat",
                     limit_fill="touch")
T_NOON = int(datetime.fromisoformat("2026-09-10T12:00:00+05:30").timestamp())


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (LOTS[und], "fixture"))
    monkeypatch.delenv(costs.COST_MODEL_ENV, raising=False)


def canonical(board):
    blob = {"closed": board["closed_trades"], "skips": board["skip_reason_counts"], "open": board["open_trades"]}
    return hashlib.sha256(json.dumps(blob, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def replay(tmp_path, tbu, **kw):
    save_founder_book(list(tbu), root=tmp_path)
    return ps.replay_paper_scalp(root=tmp_path, underlyings=tuple(tbu), triples_by_und=tbu,
                                 session_ist_date="2026-09-10", write=False, use_event_bus=False, **kw)


def filled(board):
    return [r for r in board["closed_trades"] if r.get("filled")]


def net(rows):
    return round(sum(r["realized_pnl_inr"] for r in rows), 2)


def two_index():
    return {"NIFTY": synthetic_triples(seed=5), "SENSEX": synthetic_triples(seed=9, underlying="SENSEX")}


# ------------------------------------------------------------------ legacy identity


@pytest.mark.parametrize("name", ["fixture", "nifty_sensex"])
@pytest.mark.parametrize("how", ["default", "explicit"])
def test_legacy_replay_is_byte_identical_to_pre_build(tmp_path, name, how):
    tbu = {"NIFTY": load_fixture(FIXTURE)["triples"]} if name == "fixture" else two_index()
    board = replay(tmp_path, tbu, **({"cost_model": "legacy"} if how == "explicit" else {}))
    assert canonical(board) == LEGACY_SHA[name]
    assert not any(REALISTIC_KEYS & set(r) for r in board["closed_trades"]), "legacy rows gained keys"
    assert board["cost_model"] == ps.groww_cost_meta()
    if name == "fixture":
        assert (len(filled(board)), net(filled(board))) == (12, 69309.1)  # same 12 trades; higher NSE txn/IPFT


def test_default_is_legacy_and_env_or_kwarg_switches(monkeypatch):
    assert costs.resolve_cost_model() == "legacy"
    monkeypatch.setenv(costs.COST_MODEL_ENV, "realistic")
    assert costs.resolve_cost_model() == "realistic"  # how the owner flips the live paper loop
    assert costs.resolve_cost_model("legacy") == "legacy"  # caller / ReplayContext beats env
    monkeypatch.setenv(costs.COST_MODEL_ENV, "optimistic")
    with pytest.raises(ValueError):
        costs.resolve_cost_model()


def test_config_file_matches_module_defaults():
    blob = yaml.safe_load((REPO / "config" / "paper_costs.yaml").read_text(encoding="utf-8"))
    assert blob == costs.DEFAULTS
    assert costs.load_config() == costs.DEFAULTS
    with costs.overrides(target_fill="market_at_poll"):
        assert costs.load_config()["target_fill"] == "market_at_poll"
    with pytest.raises(KeyError), costs.overrides(slipage=1):
        pass
    with pytest.raises(ValueError), costs.overrides(limit_fill="maybe"):
        costs.load_config()


# ------------------------------------------------------------------------- fills


@pytest.mark.parametrize("px,slip,entry,exit_", [
    (230.05, 0.20, 230.25, 229.85),  # on-tick print: exactly 4 ticks each way
    (230.03, 0.20, 230.25, 229.80),  # off-tick: buy rounds up, sell rounds down
    (100.00, 0.0, 100.00, 100.00),
    (0.10, 0.20, 0.30, 0.05),  # exit never below one tick
])
def test_fill_rounding_and_slippage_sign(px, slip, entry, exit_):
    assert costs.entry_fill_price(px, slip) == entry >= px
    assert costs.exit_fill_price(px, slip) == exit_
    assert costs.exit_fill_price(px, slip) <= px or px < 0.05 + slip


def test_half_spread_replaces_configured_slippage():
    cfg = costs.load_config()
    tick = SimpleNamespace(wing_quotes={"24900": {"ce": 200.0, "ce_bid": 199.9, "ce_ask": 200.3}})
    spread = costs.recorded_spread(tick, "CE", 24900.0)
    assert spread == (199.9, 200.3)
    assert costs.slip_points("NIFTY", cfg, spread) == pytest.approx(0.2)
    assert costs.slip_points("NIFTY", cfg, None) == 0.20
    assert costs.recorded_spread(tick, "PE", 24900.0) is None  # no PE book recorded
    bad = SimpleNamespace(wing_quotes={"24900": {"ce_bid": 201.0, "ce_ask": 200.0}})
    assert costs.recorded_spread(bad, "CE", 24900.0) is None  # crossed book is not a spread


# ---------------------------------------------------------- engine-level unit cases


def _engine(tmp_path, model="realistic"):
    return ps.BookEngine(root=tmp_path, cost_model=model)


def _pos(**kw):
    base = dict(book_id="MIX-DEFAULT-BUY", underlying="NIFTY", side="CE", trade_id="t1", entry=200.0, stop=180.0,
                target=230.0, atm_strike=24900.0, opened_ts=T_NOON, opened_bar=0, strike_source="TEST",
                lot_size=65, lots=25, qty=1625, filled=True, agent_status="IN_TRADE")
    base.update(kw)
    return ps.OpenPaper(**base)


def _open(engine, pos, *, impulse=True, wings=None):
    engine.opens[(pos.book_id, pos.underlying)] = pos
    if costs.is_realistic(engine):
        costs.on_plan_open(engine, pos, SimpleNamespace(ts=pos.opened_ts, wing_quotes=wings or {}), impulse=impulse)


@pytest.mark.parametrize("target_fill,exit_px", [("resting_limit", 230.0), ("market_at_poll", 238.15)])
def test_target_exit_books_resting_limit_or_poll_print(tmp_path, target_fill, exit_px):
    with costs.overrides(target_fill=target_fill):
        eng = _engine(tmp_path)
        pos = _pos()
        _open(eng, pos)
        costs.on_quote(eng, pos, SimpleNamespace(ts=T_NOON + 300, wing_quotes={}), 238.35, "STRIKE_24900")
        ps._close(eng, pos, ltp=238.35, ts=T_NOON + 300, reason="TARGET")
    row = eng.closed[-1]
    assert (row["entry"], row["exit"], row["exit_reason"]) == (200.2, exit_px, "TARGET")
    assert row["gross_pnl_inr"] == round((exit_px - 200.2) * 1625, 2)
    assert row["slippage_inr"] == (325.0 if target_fill == "resting_limit" else 650.0)
    assert row["decision_entry"] == 200.0 and row["cost_model"] == "realistic"


def test_legacy_close_is_untouched(tmp_path):
    eng = _engine(tmp_path, "legacy")
    pos = _pos()
    _open(eng, pos)
    ps._close(eng, pos, ltp=238.35, ts=T_NOON + 300, reason="TARGET")
    row = eng.closed[-1]
    assert (row["entry"], row["exit"]) == (200.0, 238.35)
    assert not REALISTIC_KEYS & set(row) and eng.cost_state == {}


def test_stale_exit_waits_for_first_fresh_print_and_keeps_reason(tmp_path):
    eng = _engine(tmp_path)
    pos = _pos()
    _open(eng, pos)
    fresh, gap_end = T_NOON + 60, T_NOON + 60 + 24 * 60
    assert costs.on_quote(eng, pos, SimpleNamespace(ts=fresh, wing_quotes={}), 230.05, "STRIKE_24900") is None
    ps._close(eng, pos, ltp=230.05, ts=fresh + 11 * 60, reason="CANCEL_STALL")  # 11-min-old quote (09-21 D4)
    assert eng.closed == [] and (pos.book_id, "NIFTY") in eng.opens
    ps._close(eng, pos, ltp=230.05, ts=fresh + 12 * 60, reason="TIME")  # still pending, first reason kept
    assert costs.on_quote(eng, pos, SimpleNamespace(ts=gap_end - 60, wing_quotes={}), 230.05, "LAST_PRINT") is None
    due = costs.on_quote(eng, pos, SimpleNamespace(ts=gap_end, wing_quotes={}), 227.15, "STRIKE_24900")
    assert due == "CANCEL_STALL"
    ps._close(eng, pos, ltp=227.15, ts=gap_end, reason=due)
    row = eng.closed[-1]
    assert (row["exit_reason"], row["exit"], row["quote_age_s"], row["quote_src"]) == ("CANCEL_STALL", 226.95, 0, "PRINT")
    assert row["exit_pending_since_ts"] == fresh + 11 * 60
    alerts = eng.cost_state["alerts"]
    assert [a["kind"] for a in alerts] == [costs.EXIT_PENDING_NO_QUOTE]  # one alert per incident


def test_stale_exit_hard_flattens_at_last_good_print(tmp_path):
    eng = _engine(tmp_path)
    t = int(datetime.fromisoformat("2026-09-10T15:05:00+05:30").timestamp())
    pos = _pos(opened_ts=t)
    _open(eng, pos)
    ps._close(eng, pos, ltp=210.0, ts=t + 12 * 60, reason="FLATTEN_1516")  # 15:17, quote 12 min old
    assert eng.closed == []
    at_1520 = t + 15 * 60
    due = costs.on_quote(eng, pos, SimpleNamespace(ts=at_1520, wing_quotes={}), 210.0, "LAST_PRINT")
    assert due == costs.FLATTEN_STALE_QUOTE
    ps._close(eng, pos, ltp=210.0, ts=at_1520, reason=due)
    row = eng.closed[-1]
    assert row["exit_reason"] == costs.FLATTEN_STALE_QUOTE and row["quote_src"] == "LAST_GOOD_PRINT"
    assert row["exit"] == 199.8 and row["quote_age_s"] == 15 * 60  # last good print 200.0 - 0.20
    assert [a["kind"] for a in eng.cost_state["alerts"]] == [costs.EXIT_PENDING_NO_QUOTE, costs.FLATTEN_STALE_QUOTE]


def test_replay_end_is_never_deferred(tmp_path):
    eng = _engine(tmp_path)
    pos = _pos()
    _open(eng, pos)
    ps._close(eng, pos, ltp=250.0, ts=T_NOON + 3600, reason="REPLAY_END")
    assert eng.closed[-1]["exit_reason"] == costs.FLATTEN_STALE_QUOTE and not eng.opens


def _mtm_tick(ts, *, held=None, atm=25000.0):
    wings = {} if held is None else {"24900": {"ce": held, "pe": 40.0}}
    return Triple(ts=ts, idx_close=25010.0, ce_close=60.0, pe_close=60.0, atm_strike=atm, wing_quotes=wings)


@pytest.mark.parametrize("model", ["legacy", "realistic"])
def test_mark_to_market_wiring_over_a_quote_gap(tmp_path, model):
    """Held strike quoted, then missing for 50 min (TIME fires on the stale print), then back at 190."""
    eng = _engine(tmp_path, model)
    t0 = int(datetime.fromisoformat("2026-09-10T11:00:00+05:30").timestamp())
    pos = _pos(opened_ts=t0, stop=150.0, target=400.0, book_id="MIX-DEFAULT-BUY")
    _open(eng, pos)
    ticks = [_mtm_tick(t0 + 60 * k, held=200.0 + k) for k in range(1, 6)]  # MFE 5 pts: no NO_PROGRESS
    ticks += [_mtm_tick(t0 + 60 * k) for k in range(6, 56)]
    ticks += [_mtm_tick(t0 + 60 * 56, held=190.0)]
    for i, tick in enumerate(ticks):
        ps.mark_to_market(eng, tick, "NIFTY", i)
        if eng.closed:
            break
    row = eng.closed[-1]
    if model == "legacy":
        assert t0 + 60 * 6 < row["closed_ts"] < t0 + 60 * 56 and row["exit"] == 205.0  # stale LAST_PRINT
    else:
        assert row["closed_ts"] == t0 + 60 * 56 and row["exit"] == 189.8 and row["quote_age_s"] == 0
        assert eng.cost_state["alerts"][0]["kind"] == costs.EXIT_PENDING_NO_QUOTE


def test_working_limit_needs_trade_through_and_fills_at_limit(tmp_path):
    pos = _pos(filled=False, entry=200.0, limit_price=199.0, agent_status="WORKING_LIMIT")
    touch = ps._unfilled_reason(pos, 199.0, T_NOON + 60, 1, side_low=199.0)
    assert touch == "FILL"  # legacy: a touch fills
    assert ps._unfilled_reason(pos, 199.0, T_NOON + 60, 1, side_low=199.0, fill_below=0.05) != "FILL"
    assert ps._unfilled_reason(pos, 198.95, T_NOON + 60, 1, side_low=198.95, fill_below=0.05) == "FILL"
    eng = _engine(tmp_path)
    pos = _pos(filled=False, entry=200.0, limit_price=199.03, agent_status="WORKING_LIMIT")
    _open(eng, pos, impulse=False)
    assert pos.limit_price == 199.0  # buy limit tick-floored at creation (D7)
    assert costs.limit_fill_below(eng) == 0.05 and costs.limit_fill_below(_engine(tmp_path, "legacy")) == 0.0
    costs.on_limit_fill(eng, pos)
    assert pos.entry == 199.0 and costs.booked_entry(eng, pos) == 199.0  # at the limit, no slippage


# ------------------------------------------------------------ replay-level behaviour


def test_slippage_only_keeps_trade_list_and_moves_money_exactly(tmp_path):
    tbu = two_index()
    legacy = filled(replay(tmp_path / "a", tbu))
    with costs.overrides(**SLIPPAGE_ONLY):
        real = filled(replay(tmp_path / "b", tbu, cost_model="realistic"))
    key = lambda r: (r["trade_id"], r["opened_ts"], r["closed_ts"], r["exit_reason"], r["qty"])  # noqa: E731
    assert [key(r) for r in legacy] == [key(r) for r in real] and len(real) >= 5
    for a, b in zip(legacy, real):
        assert b["entry"] == costs.entry_fill_price(a["entry"], 0.20)
        assert b["exit"] == costs.exit_fill_price(a["exit"], 0.20)
        assert round(a["gross_pnl_inr"] - b["gross_pnl_inr"], 2) == b["slippage_inr"]
        d_net = round(a["realized_pnl_inr"] - b["realized_pnl_inr"], 2)
        assert d_net == round(b["slippage_inr"] + b["charges_inr"] - a["charges_inr"], 2)
        assert abs(b["charges_inr"] - a["charges_inr"]) < 1.0  # only turnover + paise rounding moved


def test_full_realistic_rows_never_book_a_stale_quote(tmp_path):
    board = replay(tmp_path, {"NIFTY": load_fixture(FIXTURE)["triples"]}, cost_model="realistic")
    rows = filled(board)
    assert len(rows) >= 5 and all(r["cost_model"] == "realistic" for r in board["closed_trades"])
    for r in rows:
        assert r["quote_src"] in {"PRINT", "TARGET_LIMIT", "LAST_GOOD_PRINT"}
        assert r["quote_age_s"] <= 90 or r["exit_reason"] == costs.FLATTEN_STALE_QUOTE
        ch = costs.realistic_charges(r["underlying"], r["qty"], r["entry"], r["exit"], costs.load_config())
        assert r["charges_inr"] == ch["charges_inr"]
        assert r["realized_pnl_inr"] == round(r["gross_pnl_inr"] - r["charges_inr"], 2)
    meta = board["cost_model"]
    assert meta["mode"] == "realistic" and meta["n_alerts"] >= 1  # the fixture has held-strike gaps


def test_bse_fee_for_sensex_and_nse_march_2026_rate_for_nifty():
    cfg = costs.load_config()
    sx = costs.realistic_charges("SENSEX", 500, 400.0, 400.0, cfg)  # turnover 2,00,000 per leg
    nf = costs.realistic_charges("NIFTY", 500, 400.0, 400.0, cfg)
    flat = costs.realistic_charges("SENSEX", 500, 400.0, 400.0, {**cfg, "exchange_fees": "nse_flat"})
    assert (sx["exchange"], nf["exchange"], flat["exchange"]) == ("BSE", "NSE", "NSE_FLAT")
    assert sx["exchange_inr"] == 2 * 65.0  # 0.0325% x 2,00,000 per leg
    assert nf["exchange_inr"] == 2 * 71.06  # 0.03553% x 2,00,000 per leg
    assert flat["exchange_inr"] == 2 * 71.06  # NSE txn 0.0355299% × 2,00,000/leg (paise)
    assert sx["brokerage_inr"] == 40.0 and sx["stt_inr"] == 300.0 and sx["stamp_inr"] == 6.0


def test_event_path_realistic_matches_monolith_and_ledger_to_the_paisa(tmp_path):
    tbu = two_index()
    save_founder_book(list(tbu), root=tmp_path)
    from desk_ml.event_path import EventSession

    rep = run_parity(root=tmp_path, underlyings=tuple(tbu), triples_by_und=tbu, session_ist_date="2026-09-10",
                     cost_model="realistic")
    assert rep["ok"], rep["problems"][:5]
    session = EventSession()
    try:
        ps.replay_paper_scalp(root=tmp_path, underlyings=tuple(tbu), triples_by_und=tbu,
                              session_ist_date="2026-09-10", write=False, cost_model="realistic",
                              event_session=session)
        ledger = {t["trade_id"]: t for t in session.ledger_trades()}
    finally:
        session.close()
    rows = [r for r in rep["closed_trades"] if r["filled"]]
    assert {r["underlying"] for r in rows} == {"NIFTY", "SENSEX"}
    for r in rows:
        t = ledger[r["trade_id"]]
        assert (t["entry_price"], t["exit_price"]) == (r["entry"], r["exit"])
        assert round(t["charges"], 2) == r["charges_inr"]
        assert round(t["entry_slippage"], 4) == round(r["entry"] - r["decision_entry"], 4)

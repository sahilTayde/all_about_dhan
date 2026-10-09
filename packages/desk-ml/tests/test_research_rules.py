"""Frozen R01 PDIV + R01_B3A_VOL + R02 MOM paper rules. No broker. Cost fixture #84."""

from __future__ import annotations

import inspect
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr
from desk_ml.paper_lots import pnl_inr
from desk_ml import research_rules as rr

IST = timezone(timedelta(hours=5, minutes=30))
DAY = "2026-10-09"


def _ts(hhmm: str, sec: int = 50) -> str:
    return f"{DAY}T{hhmm}:{sec:02d}+05:30"


def _snap(und: str, hhmm: str, idx: float, ce: float, pe: float, atm: float = 25000.0) -> dict:
    return {
        "underlying": und,
        "as_of_ist": _ts(hhmm),
        "index_ltp": idx,
        "atm_strike": atm,
        "atm_ce_ltp": ce,
        "atm_pe_ltp": pe,
        "wing_quotes": {
            "25000": {"ce": ce, "pe": pe},
        },
    }


def _write_tape(root: Path, rows: list[tuple[str, list[dict]]]) -> None:
    folder = root / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{DAY}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for hhmm, snaps in rows:
            fh.write(
                json.dumps({"as_of_ist": _ts(hhmm), "underlyings": snaps, "orders": "refused"}) + "\n"
            )


def _minutes(start: str, n: int) -> list[str]:
    out = [start]
    for _ in range(n - 1):
        out.append(rr.mplus(out[-1], 1))
    return out


def test_flag_defaults_on_and_can_disable() -> None:
    assert rr.enabled({}) is True
    assert rr.enabled({rr.FLAG_ENV: "1"}) is True
    assert rr.enabled({rr.FLAG_ENV: "0"}) is False
    assert rr.enabled({rr.FLAG_ENV: "false"}) is False


def test_pdiv_and_mom_thresholds_are_frozen() -> None:
    # Index flat, CE rips vs PE → buy CE.
    assert (
        rr.pdiv_side(
            idx_t=25000.0,
            idx_k=25001.0,
            ce_t=110.0,
            ce_k=100.0,
            pe_t=100.0,
            pe_k=100.0,
            flat_thr=0.0005,
            dv_thr=0.1,
        )
        == "CE"
    )
    # Index moved 6bp → no PDIV.
    assert (
        rr.pdiv_side(
            idx_t=25015.0,
            idx_k=25000.0,
            ce_t=110.0,
            ce_k=100.0,
            pe_t=100.0,
            pe_k=100.0,
            flat_thr=0.0005,
            dv_thr=0.1,
        )
        is None
    )
    # PE rips vs CE, index flat → buy PE.
    assert (
        rr.pdiv_side(
            idx_t=25000.0,
            idx_k=25000.0,
            ce_t=100.0,
            ce_k=100.0,
            pe_t=112.0,
            pe_k=100.0,
            flat_thr=0.0005,
            dv_thr=0.1,
        )
        == "PE"
    )
    assert rr.mom_side(idx_t=25013.0, idx_k=25000.0, thr=0.0005) == "CE"
    assert rr.mom_side(idx_t=24987.0, idx_k=25000.0, thr=0.0005) == "PE"
    assert rr.mom_side(idx_t=25010.0, idx_k=25000.0, thr=0.0005) is None


def test_replay_fills_t_plus_1_holds_20_and_uses_cost_fixture(tmp_path: Path) -> None:
    # Warmup 09:30..09:59 (30 min). Signal window starts 10:00.
    # MOM: 10:00 vs 09:57 up 6bp → CE. PDIV: flat index, CE +10% vs PE.
    mins = _minutes("09:30", 62)  # 09:30 .. 10:31 (PDIV TIME exit)
    rows = []
    for hhmm in mins:
        idx = 25000.0
        ce, pe = 100.0, 100.0
        if hhmm == "09:57":
            idx = 25000.0
        if hhmm == "10:00":
            idx = 25015.0  # +6bp vs 09:57 → MOM CE; PDIV blocked (not flat)
            ce, pe = 100.0, 100.0
        if hhmm == "10:05":
            idx = 25000.0  # flat vs 10:00? k=5 → 10:00 was 25015, not flat
        if hhmm == "10:10":
            idx = 25000.2  # vs 10:05 (25000) = 0.8bp < 5bp → PDIV ok
            ce, pe = 110.0, 100.0  # dv = 0.10 → CE
        if hhmm == "10:11":
            ce, pe = 111.0, 99.0  # PDIV fill minute
        if hhmm == "10:01":
            ce, pe = 102.0, 98.0  # MOM fill minute
        if hhmm == "10:21":
            ce, pe = 108.0, 97.0  # MOM TIME exit
        if hhmm == "10:31":
            ce, pe = 105.0, 101.0  # PDIV TIME exit
        rows.append((hhmm, [_snap("NIFTY", hhmm, idx, ce, pe), _snap("SENSEX", hhmm, idx * 3.2, ce, pe, 80000.0)]))
    # SENSEX ATM 80000 is not in wing 25000 — give matching wings via snap override
    fixed = []
    for hhmm, snaps in rows:
        sx = dict(snaps[1])
        sx["wing_quotes"] = {"80000": {"ce": sx["atm_ce_ltp"], "pe": sx["atm_pe_ltp"]}}
        fixed.append((hhmm, [snaps[0], sx]))
    _write_tape(tmp_path, fixed)

    out = rr.replay(tmp_path, DAY)
    mom = [t for t in out["closed"] if t["rule_id"] == rr.R02 and t["underlying"] == "NIFTY"]
    pdiv = [t for t in out["closed"] if t["rule_id"] == rr.R01 and t["underlying"] == "NIFTY"]
    assert len(mom) == 1
    assert mom[0]["side"] == "CE"
    assert mom[0]["sig_min"] == "10:00"
    assert mom[0]["entry_min"] == "10:01"
    assert mom[0]["exit_min"] == "10:21"
    assert mom[0]["entry"] == 102.0
    assert mom[0]["exit"] == 108.0
    assert mom[0]["qty"] == 650
    assert mom[0]["lots"] == 10
    assert mom[0]["execution"] == "refused"
    expect = groww_round_trip_charges(exit_premium=108.0, entry_premium=102.0, qty=650, filled=True)
    assert mom[0]["charges_inr"] == expect["charges_inr"]
    assert mom[0]["exchange_inr"] == expect["exchange_inr"]
    assert mom[0]["brokerage_inr"] == 40.0
    gross = pnl_inr(points=6.0, lot_size=65, lots=10)
    assert mom[0]["gross_pnl_inr"] == gross
    assert mom[0]["realized_pnl_inr"] == net_pnl_inr(gross_inr=gross, charges_inr=expect["charges_inr"])

    assert len(pdiv) == 1
    assert pdiv[0]["side"] == "CE"
    assert pdiv[0]["sig_min"] == "10:10"
    assert pdiv[0]["entry_min"] == "10:11"
    assert pdiv[0]["exit_min"] == "10:31"
    assert pdiv[0]["qty"] == 650
    b3a = [t for t in out["closed"] if t["rule_id"] == rr.R01_B3A and t["underlying"] == "NIFTY"]
    assert b3a == []  # same tape, rv30 below frozen cut — R01 unchanged, B3A gated off

    sx = [t for t in out["closed"] if t["underlying"] == "SENSEX"]
    assert sx
    assert {t["qty"] for t in sx} == {200}
    assert {t["lots"] for t in sx} == {10}


def test_flag_off_does_not_attach(tmp_path: Path) -> None:
    board = {"session_ist_date": DAY, "open_trades": [], "closed_trades": [{"book_id": "MIX-DEFAULT-BUY"}]}
    out = rr.attach_to_board(board, root=tmp_path, environ={rr.FLAG_ENV: "0"})
    assert out["research_rules"]["enabled"] is False
    assert out["closed_trades"] == [{"book_id": "MIX-DEFAULT-BUY"}]


def test_attach_merges_onto_desk_board(tmp_path: Path) -> None:
    mins = _minutes("09:30", 52)
    rows = []
    for hhmm in mins:
        idx = 25000.0
        ce, pe = 100.0, 100.0
        if hhmm == "10:00":
            idx = 25015.0
        if hhmm == "10:01":
            ce = 101.0
        if hhmm == "10:21":
            ce = 99.0
        rows.append((hhmm, [_snap("NIFTY", hhmm, idx, ce, pe)]))
    _write_tape(tmp_path, rows)
    board = {
        "session_ist_date": DAY,
        "open_trades": [{"book_id": "MIX-DEFAULT-BUY", "trade_id": "sod-1"}],
        "closed_trades": [],
        "n_open": 1,
    }
    out = rr.attach_to_board(board, root=tmp_path, environ={rr.FLAG_ENV: "1"})
    books = {t["book_id"] for t in out["closed_trades"] + out["open_trades"]}
    assert rr.R02 in books
    assert "MIX-DEFAULT-BUY" in books
    assert out["research_rules"]["orders"] == "REFUSED"
    assert (tmp_path / "data" / "recon" / "research_rules" / f"{DAY}.json").is_file()


def test_source_never_calls_a_broker() -> None:
    src = inspect.getsource(rr)
    assert "ExecutionClient" not in src
    assert "place_order" not in src
    assert "dhanhq" not in src.lower()
    assert "brokers" not in src
    fixture = groww_round_trip_charges(exit_premium=100.0, entry_premium=100.0, qty=65, filled=True)
    assert fixture["charges_inr"] == 62.61


def test_one_open_per_rule_non_overlapping() -> None:
    bars: dict[str, dict] = {}
    for hhmm in _minutes("09:30", 80):
        idx = 25000.0
        if hhmm >= "10:00":
            idx = 25020.0  # would keep firing MOM CE every minute if overlapping
        bars[hhmm] = {
            "idx": idx,
            "ce": 100.0,
            "pe": 100.0,
            "atm": 25000.0,
            "ts": int(datetime.fromisoformat(_ts(hhmm)).timestamp()),
            "hhmm": hhmm,
            "wings": {"25000": {"ce": 100.0, "pe": 100.0}},
        }
    mom_rule = next(r for r in rr.FROZEN_RULES if r["rule_id"] == rr.R02)
    opens, closed = rr.replay_underlying(bars, underlying="NIFTY", day=DAY, rules=[mom_rule])
    taken = opens + closed
    assert len(taken) == 1
    assert taken[0]["sig_min"] == "10:00"


def _bar(idx: float, ce: float = 100.0, pe: float = 100.0, atm: float = 25000.0, hhmm: str = "10:00") -> dict:
    return {
        "idx": idx,
        "ce": ce,
        "pe": pe,
        "atm": atm,
        "hhmm": hhmm,
        "ts": int(datetime.fromisoformat(_ts(hhmm)).timestamp()),
        "wings": {"25000": {"ce": ce, "pe": pe}},
    }


def _pdiv_bars(*, idx_by_min: dict[str, float], t: str = "10:10") -> dict[str, dict]:
    """PDIV CE at t: last 5 index minutes flat-enough, CE +10% vs PE."""
    bars: dict[str, dict] = {}
    for hhmm, idx in idx_by_min.items():
        ce, pe = 100.0, 100.0
        if hhmm == t:
            ce = 110.0
        if hhmm == rr.mplus(t, 1):
            ce = 111.0
        if hhmm == rr.mplus(t, 21):
            ce = 105.0
        bars[hhmm] = _bar(idx, ce=ce, pe=pe, hhmm=hhmm)
    return bars


def test_rv30_none_when_fewer_than_20_observations() -> None:
    bars = {hhmm: _bar(25000.0, hhmm=hhmm) for hhmm in _minutes("10:00", 19)}
    assert rr.rv30(bars, "10:18") is None
    bars20 = {hhmm: _bar(25000.0, hhmm=hhmm) for hhmm in _minutes("10:00", 20)}
    assert rr.rv30(bars20, "10:19") == 0.0


def test_vol_gate_on_off_at_frozen_cut() -> None:
    cut_n = rr.VOL_CUT["NIFTY"]
    cut_s = rr.VOL_CUT["SENSEX"]
    assert cut_n == 0.00021620371
    assert cut_s == 0.00021971343
    assert rr.vol_gate_ok(cut_n, cut_n) is True
    assert rr.vol_gate_ok(cut_n + 1e-12, cut_n) is True
    assert rr.vol_gate_ok(cut_n - 1e-12, cut_n) is False
    assert rr.vol_gate_ok(None, cut_n) is False
    assert rr.vol_gate_ok(cut_s, cut_s) is True
    assert rr.vol_gate_ok(cut_s - 1e-15, cut_s) is False


def test_r01_b3a_vol_gate_at_cut_and_r01_still_fires() -> None:
    t = "10:10"
    mins = _minutes("09:30", 62)
    cut = rr.VOL_CUT["NIFTY"]
    # 31 observed minutes in [t-30, t] → 30 log returns. Two opposite jumps, rest 0.
    # pop std = x * sqrt(2/30); x = cut * sqrt(15).
    x = cut * (15.0 ** 0.5)
    ratio = math.exp(x)
    idx: dict[str, float] = {hhmm: 25000.0 for hhmm in mins}
    idx["09:40"] = 25000.0
    idx["09:41"] = 25000.0 * ratio
    idx["09:42"] = 25000.0  # down by the same log return
    bars = _pdiv_bars(idx_by_min=idx, t=t)
    rv = rr.rv30(bars, t)
    assert rv is not None
    assert abs(rv - cut) / cut < 1e-9
    pdiv = next(r for r in rr.FROZEN_RULES if r["rule_id"] == rr.R01)
    b3a = next(r for r in rr.FROZEN_RULES if r["rule_id"] == rr.R01_B3A)
    assert rr.signal(pdiv, bars, t, underlying="NIFTY") == "CE"
    assert rr.signal(b3a, bars, t, underlying="NIFTY") == "CE"

    # One tick below the cut: same PDIV, B3A off.
    x_lo = (cut * 0.99) * (15.0 ** 0.5)
    idx_lo = {hhmm: 25000.0 for hhmm in mins}
    idx_lo["09:41"] = 25000.0 * math.exp(x_lo)
    idx_lo["09:42"] = 25000.0
    bars_lo = _pdiv_bars(idx_by_min=idx_lo, t=t)
    rv_lo = rr.rv30(bars_lo, t)
    assert rv_lo is not None and rv_lo < cut
    assert rr.signal(pdiv, bars_lo, t, underlying="NIFTY") == "CE"
    assert rr.signal(b3a, bars_lo, t, underlying="NIFTY") is None

    opens, closed = rr.replay_underlying(bars_lo, underlying="NIFTY", day=DAY)
    books = {row["rule_id"] for row in opens + closed}
    assert rr.R01 in books
    assert rr.R01_B3A not in books


def test_r01_b3a_no_signal_when_rv30_undefined() -> None:
    t = "10:10"
    # Only 15 observed minutes in the lookback window.
    sparse = {rr.mplus(t, -j): 25000.0 for j in (0, 1, 2, 3, 4, 5, 8, 10, 12, 14, 16, 18, 20, 22, 24)}
    extra = {hhmm: 25000.0 for hhmm in _minutes("10:11", 21)}
    bars = _pdiv_bars(idx_by_min={**sparse, **extra}, t=t)
    assert len([m for m in bars if "10:" in m or m <= t]) >= 1
    assert rr.rv30(bars, t) is None
    b3a = next(r for r in rr.FROZEN_RULES if r["rule_id"] == rr.R01_B3A)
    pdiv = next(r for r in rr.FROZEN_RULES if r["rule_id"] == rr.R01)
    assert rr.signal(pdiv, bars, t, underlying="NIFTY") == "CE"
    assert rr.signal(b3a, bars, t, underlying="NIFTY") is None

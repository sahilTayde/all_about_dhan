"""Tests for chain_iv: parse, surface stats, persist/load, momentum."""

from __future__ import annotations

from trading_agents_india import chain_iv
from trading_agents_india.chain_iv import (
    IvPoint,
    compute_iv_stats,
    gather_chain_iv,
    load_iv_stats,
    parse_iv_points,
    persist_iv_stats,
    tilt_momentum,
)


def _payload(ivs: dict[float, tuple[float, float]], spot: float = 25000.0) -> dict:
    """Documented chain shape: data.oc keyed by strike string."""
    oc = {
        f"{strike:.6f}": {
            "ce": {"implied_volatility": ce, "last_price": 100.0, "oi": 10},
            "pe": {"implied_volatility": pe, "last_price": 100.0, "oi": 10},
        }
        for strike, (ce, pe) in ivs.items()
    }
    return {"data": {"last_price": spot, "oc": oc}}


def _smirk_ivs() -> dict[float, tuple[float, float]]:
    """Put smirk: PE IV rises below ATM; CE IV mildly falls above."""
    out: dict[float, tuple[float, float]] = {}
    for i, strike in enumerate(range(24750, 25300, 50)):  # 11 strikes, ATM 25000
        dist = (strike - 25000) / 50.0
        ce = 12.0 - 0.1 * dist
        pe = 12.0 - 0.8 * dist if dist < 0 else 12.0
        out[float(strike)] = (ce, pe)
    return out


def test_parse_iv_points_documented_shape() -> None:
    spot, points = parse_iv_points(_payload(_smirk_ivs()))
    assert spot == 25000.0
    assert len(points) == 11
    assert points[0].strike == 24750.0
    assert points[0].pe_iv is not None and points[0].pe_iv > 12.0
    assert points[0].mid_iv is not None


def test_parse_iv_points_bad_payload() -> None:
    spot, points = parse_iv_points({"status": "failure"})
    assert spot is None and points == []


def test_compute_iv_stats_put_smirk_positive_tilt() -> None:
    spot, points = parse_iv_points(_payload(_smirk_ivs()))
    stats = compute_iv_stats(spot, points, wing=5)
    assert stats is not None
    assert stats["atm_strike"] == 25000.0
    # Put wing IVs > call wing IVs => positive tilt (put smirk).
    assert stats["skew_tilt"] is not None and stats["skew_tilt"] > 0
    # Wings above ATM mid => positive curvature.
    assert stats["curvature"] is not None and stats["curvature"] > 0
    assert stats["iv_entropy"] is not None and 0.9 < stats["iv_entropy"] <= 1.0


def test_compute_iv_stats_flat_surface_max_entropy() -> None:
    flat = {float(s): (15.0, 15.0) for s in range(24800, 25250, 50)}
    spot, points = parse_iv_points(_payload(flat))
    stats = compute_iv_stats(spot, points, wing=4)
    assert stats is not None
    assert stats["skew_tilt"] == 0.0
    assert stats["curvature"] == 0.0
    assert abs(stats["iv_entropy"] - 1.0) < 1e-9


def test_compute_iv_stats_insufficient() -> None:
    assert compute_iv_stats(None, []) is None
    assert compute_iv_stats(25000.0, [IvPoint(strike=25000.0)]) is None


def test_persist_load_roundtrip_upsert(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(chain_iv, "chain_iv_dir", lambda: tmp_path)
    spot, points = parse_iv_points(_payload(_smirk_ivs()))
    stats = compute_iv_stats(spot, points)
    assert stats is not None
    stats["ts"] = 1000
    persist_iv_stats("NIFTY", stats, source="payload")
    # Same ts overwrites, new ts appends.
    stats2 = dict(stats, ts=1000, skew_tilt=9.9)
    persist_iv_stats("NIFTY", stats2, source="payload")
    stats3 = dict(stats, ts=2000)
    persist_iv_stats("NIFTY", stats3, source="payload")
    rows = load_iv_stats("NIFTY")
    assert [r["ts"] for r in rows] == [1000, 2000]
    assert rows[0]["skew_tilt"] == 9.9


def test_tilt_momentum() -> None:
    snaps = [{"skew_tilt": t} for t in (1.0, 1.2, 1.5, 2.0)]
    assert tilt_momentum(snaps, lookback=3) == 1.0
    assert tilt_momentum(snaps[:3], lookback=3) is None


def test_gather_from_payload_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(chain_iv, "chain_iv_dir", lambda: tmp_path)
    result = gather_chain_iv("SENSEX", payload=_payload(_smirk_ivs(), spot=25000.0))
    assert result.source == "payload"
    assert result.stats is not None and result.stats["skew_tilt"] > 0
    assert load_iv_stats("SENSEX")


def test_gather_not_live_is_data_gap() -> None:
    result = gather_chain_iv("NIFTY", prefer_live=False)
    assert result.source == "unavailable"
    assert any("DATA_INSUFFICIENT" in g for g in result.data_gaps)

from warehouse.ohlc import normalize_tf, resample_minutes, resample_weeks
from warehouse.store import Warehouse


def test_normalize_aliases() -> None:
    assert normalize_tf("1h") == "60m"
    assert normalize_tf("weekly") == "1w"
    assert normalize_tf("3") == "3m"


def test_resample_3m_from_1m() -> None:
    rows = [
        {"ts": 0, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "oi": None},
        {"ts": 60, "open": 1.5, "high": 3, "low": 1.4, "close": 2.0, "volume": 4, "oi": None},
        {"ts": 120, "open": 2.0, "high": 2.1, "low": 1.9, "close": 2.0, "volume": 1, "oi": None},
    ]
    out = resample_minutes(rows, 3)
    assert len(out) == 1
    assert out[0]["open"] == 1
    assert out[0]["high"] == 3
    assert out[0]["low"] == 0.5
    assert out[0]["close"] == 2.0
    assert out[0]["volume"] == 15


def test_load_3m_resamples_if_unstored(tmp_path) -> None:
    wh = Warehouse(tmp_path / "w.sqlite")
    wh.init()
    # Three 1-minute bars in the same 3m bucket (epoch 0 window).
    for i, close in enumerate((10.0, 11.0, 12.0)):
        wh.append_bar(
            timeframe="1m",
            symbol="NIFTY",
            ts=f"1970-01-01T00:0{i}:00+00:00",
            source="fixture",
            open_=10.0,
            high=12.0,
            low=9.0,
            close=close,
            volume=1.0,
        )
    three = wh.load_bars("NIFTY", "3m")
    assert three
    assert three[0]["timeframe"] == "3m"
    assert three[0]["close"] == 12.0


def test_resample_week() -> None:
    # Two days same ISO week
    a = {"ts": 1767225600, "open": 1, "high": 2, "low": 1, "close": 1.5, "volume": 1, "oi": None}
    b = {"ts": 1767312000, "open": 1.5, "high": 3, "low": 1.4, "close": 2.8, "volume": 2, "oi": None}
    out = resample_weeks([a, b])
    assert len(out) == 1
    assert out[0]["open"] == 1
    assert out[0]["close"] == 2.8
    assert out[0]["high"] == 3

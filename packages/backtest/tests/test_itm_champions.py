from backtest_engine.run_itm_champions import streak_stats
from backtest_engine.itm_champions import CHAMPIONS, champions_meta


def test_champions_catalog_nonempty() -> None:
    assert len(CHAMPIONS) >= 10
    meta = champions_meta()
    assert all(m["promotion"] == "NO_PROMOTE" for m in meta)
    ids = {c.id for c in CHAMPIONS}
    assert "MIX-CHAMP-EMA-ST-5M" in ids
    assert "MIX-CHAMP-EMA-ST-VWAP-5M" in ids
    assert "MIX-CHAMP-FV-V1-10M-BB15" in ids
    assert "MIX-CHAMP-FV-V1-5M-BB20" in ids
    assert all(c.id.startswith("MIX-CHAMP-") for c in CHAMPIONS)


def test_streak_stats() -> None:
    s = streak_stats([1, 1, -1, -1, -1, 2])
    assert s["current_streak"] == 1
    assert s["current_streak_kind"] == "W"
    assert s["max_win_streak"] == 2
    assert s["max_loss_streak"] == 3
    empty = streak_stats([])
    assert empty["current_streak"] == 0

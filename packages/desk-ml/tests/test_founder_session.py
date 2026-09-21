from desk_ml.founder_session import (
    STOP_REASON,
    allows_new_fill,
    load_founder_book,
    new_fill_decision,
    save_founder_book,
)
from desk_ml.paper_scalp import load_human_override, save_human_override


def test_default_book_is_nifty_only() -> None:
    book = load_founder_book(root=None)
    assert "NIFTY" in book["trade_underlyings"]
    assert book["tape_records_all"] is True
    assert book["apply_new_fills_only"] is True


def test_save_and_allow(tmp_path) -> None:
    save_founder_book(["nifty", "SENSEX", "SENSEX", "junk"], root=tmp_path)
    book = load_founder_book(root=tmp_path)
    assert book["trade_underlyings"] == ["NIFTY", "SENSEX"]
    assert allows_new_fill("NIFTY", root=tmp_path)
    assert allows_new_fill("SENSEX", root=tmp_path)
    assert not allows_new_fill("BANKNIFTY", root=tmp_path)


def test_explicit_empty_book_stops_all_new_fills(tmp_path) -> None:
    save_founder_book([], root=tmp_path)
    book = load_founder_book(root=tmp_path)
    assert book["trade_underlyings"] == []
    assert set(book["stopped_underlyings"]) == {"NIFTY", "BANKNIFTY", "SENSEX"}
    assert not allows_new_fill("NIFTY", root=tmp_path)
    decision = new_fill_decision("NIFTY", root=tmp_path)
    assert decision["allow"] is False
    assert decision["reason"] == STOP_REASON


def test_human_override_persists_priority_exit(tmp_path) -> None:
    saved = save_human_override(
        {"action": "EXIT", "trade_id": "t1", "underlying": "NIFTY", "side": "CE"},
        root=tmp_path,
    )
    assert saved["active"] is True
    loaded = load_human_override(root=tmp_path)
    assert loaded["action"] == "EXIT"
    assert loaded["trade_id"] == "t1"
    assert loaded["underlying"] == "NIFTY"
    assert loaded["side"] == "CE"
    assert loaded["orders"] == "REFUSED"

from desk_ml.founder_session import allows_new_fill, load_founder_book, save_founder_book


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

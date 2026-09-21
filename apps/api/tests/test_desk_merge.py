"""API desk_merge: top_veto_reasons / meta.veto_banner completeness."""

from __future__ import annotations

from api.desk_merge import merge_live_paper_into_desk, overlay_customer_sod_ticket


def test_live_row_reasons_become_top_veto_and_meta_banner() -> None:
    desk = {
        "meta": {"source": "mock", "asOf": "t0", "note": "n"},
        "underlyings": ["NIFTY"],
        "signals": {
            "NIFTY": {
                "id": "mock-nifty-001",
                "underlying": "NIFTY",
                "side": "HOLD",
                "entry": "DATA_INSUFFICIENT",
                "stop": "DATA_INSUFFICIENT",
                "target": "DATA_INSUFFICIENT",
            }
        },
    }
    live = {
        "kind": "paper_signal",
        "orders": "refused",
        "as_of_ist": "2026-09-07T12:00:00+05:30",
        "underlyings": {
            "NIFTY": {
                "side": "HOLD",
                "lean": "HOLD",
                "state": "VETOED",
                "reasons": [
                    "BIG_NEWS: hold customer ticket",
                    "boss: ignore me",
                    "cited_news: Demo",
                ],
                "vetoes": ["BIG_NEWS: hold customer ticket"],
            }
        },
    }
    out = merge_live_paper_into_desk(desk, live)
    row = out["signals"]["NIFTY"]
    assert row["top_veto_reasons"]
    assert "BIG_NEWS" in row["top_veto_reasons"][0]
    assert not any(r.startswith("boss:") for r in row["top_veto_reasons"])
    assert out["meta"]["veto_banner"]
    assert out["meta"]["top_veto_reasons"]


def test_overlay_hides_fixture_pe_when_no_sod_fill() -> None:
    desk = {
        "meta": {"source": "mock"},
        "signals": {
            "NIFTY": {
                "id": "mock-nifty-001",
                "underlying": "NIFTY",
                "side": "BUY_PE",
                "strike": 24850,
                "entry": "DATA_INSUFFICIENT",
                "stop": "DATA_INSUFFICIENT",
                "target": "DATA_INSUFFICIENT",
                "staged": {"state": "IN-PROGRESS"},
            }
        },
    }
    out = overlay_customer_sod_ticket(desk, board={"live_session": True, "open_trades": []})
    row = out["signals"]["NIFTY"]
    assert row["side"] == "HOLD"
    assert row["strike"] == ""
    assert row["staged"]["state"] == "HOLD"


def test_overlay_uses_sod_open_premium() -> None:
    desk = {
        "meta": {"source": "mock"},
        "signals": {
            "NIFTY": {
                "id": "mock-nifty-001",
                "underlying": "NIFTY",
                "side": "BUY_PE",
                "strike": 24850,
                "entry": "DATA_INSUFFICIENT",
                "stop": "DATA_INSUFFICIENT",
                "target": "DATA_INSUFFICIENT",
            }
        },
    }
    board = {
        "live_session": True,
        "session_ist_date": "2026-09-21",
        "open_trades": [
            {
                "book_id": "MIX-DEFAULT-BUY",
                "underlying": "NIFTY",
                "side": "CE",
                "atm_strike": 23200,
                "entry": 196.0,
                "stop": 184.24,
                "target": 210.7,
                "lots": 25,
                "trade_id": "paper-test",
                "idx_at_open": 23376.65,
            }
        ],
    }
    out = overlay_customer_sod_ticket(desk, board=board)
    row = out["signals"]["NIFTY"]
    assert row["side"] == "BUY_CE"
    assert row["strike"] == 23200
    assert row["entry"] == 196.0
    assert row["lots"] == 25
    assert row["ticket"]["levels_ready"] is True

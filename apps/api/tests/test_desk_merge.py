"""API desk_merge: top_veto_reasons / meta.veto_banner completeness."""

from __future__ import annotations

from api.desk_merge import merge_live_paper_into_desk


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

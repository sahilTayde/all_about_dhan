import json

from api.entry_spot import attach_entry_spots

DAY = "2026-01-15"


def _row(hms: str, nifty: float, bank: float) -> str:
    stamp = f"{DAY}T{hms}+05:30"
    return json.dumps(
        {
            "as_of_ist": stamp,
            "underlyings": [
                {"underlying": "NIFTY", "index_ltp": nifty},
                {"underlying": "BANKNIFTY", "index_ltp": bank},
            ],
        }
    )


def test_spot_is_the_tape_print_at_entry_not_the_latest(tmp_path) -> None:
    tape = tmp_path / f"{DAY}.jsonl"
    tape.write_text(
        "\n".join([_row("09:30:00", 20000.0, 45000.0), _row("09:31:00", 20010.5, 45020.0), _row("15:29:00", 20500.0, 46000.0)])
        + "\n{half-written",
        encoding="utf-8",
    )
    blob = {
        "closed_trades": [
            {"underlying": "NIFTY", "opened_ist": f"{DAY}T09:31:40+05:30"},
            {"underlying": "BANKNIFTY", "opened_ist": f"{DAY}T09:30:05+05:30"},
            {"underlying": "NIFTY", "opened_ist": f"{DAY}T12:00:00+05:30"},  # tape gap > 180 s
            {"underlying": "NIFTY", "opened_ist": f"{DAY}T09:31:40+05:30", "spot_at_entry": 1.0},
        ],
        "open_trades": [{"underlying": "NIFTY", "opened_ist": f"{DAY}T09:29:00+05:30"}],  # before tape
    }
    attach_entry_spots(blob, tmp_path)
    closed = blob["closed_trades"]
    assert closed[0]["spot_at_entry"] == 20010.5
    assert closed[0]["spot_at_entry_src"] == "DUAL-TAPE"
    assert closed[1]["spot_at_entry"] == 45000.0
    assert "spot_at_entry" not in closed[2]
    assert closed[3]["spot_at_entry"] == 1.0
    assert "spot_at_entry" not in blob["open_trades"][0]

    with tape.open("a", encoding="utf-8") as fh:
        fh.write("\n" + _row("15:30:00", 20600.0, 46100.0) + "\n")
    late = {"closed_trades": [{"underlying": "NIFTY", "opened_ist": f"{DAY}T15:30:10+05:30"}]}
    attach_entry_spots(late, tmp_path)
    assert late["closed_trades"][0]["spot_at_entry"] == 20600.0


def test_missing_tape_dir_is_a_no_op(tmp_path) -> None:
    blob = {"closed_trades": [{"underlying": "NIFTY", "opened_ts": 1768449600}]}
    attach_entry_spots(blob, tmp_path / "nope")
    assert "spot_at_entry" not in blob["closed_trades"][0]

"""scripts/cost_ablation.py on a synthetic dual-tape folder (tape JSONL format, bid/ask on the held
strikes). Legacy step = a plain legacy replay; slippage-only step keeps every decision."""

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import desk_ml.founder_session as fs
import desk_ml.paper_scalp as ps
from desk_ml.event_parity import synthetic_triples

REPO = Path(__file__).resolve().parents[3]
IST = timezone(timedelta(hours=5, minutes=30))
DAYS = {"2026-09-10": 23, "2026-09-11": 31}


def _load_script():
    spec = importlib.util.spec_from_file_location("cost_ablation", REPO / "scripts" / "cost_ablation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _snap(t):
    wings = {
        str(int(t.itm_ce_strike)): {"ce": t.itm_ce_close, "ce_bid": round(t.itm_ce_close - 0.1, 2),
                                    "ce_ask": round(t.itm_ce_close + 0.1, 2)},
        str(int(t.itm_pe_strike)): {"pe": t.itm_pe_close, "pe_bid": round(t.itm_pe_close - 0.1, 2),
                                    "pe_ask": round(t.itm_pe_close + 0.1, 2)},
    }
    return {"underlying": "NIFTY", "index_ltp": t.idx_close, "atm_strike": t.atm_strike, "atm_ce_ltp": t.ce_close,
            "atm_pe_ltp": t.pe_close, "itm_ce_strike": t.itm_ce_strike, "itm_pe_strike": t.itm_pe_strike,
            "itm_ce_ltp": t.itm_ce_close, "itm_pe_ltp": t.itm_pe_close, "premium_kind": "ITM",
            "index_volume": t.idx_volume, "wing_quotes": wings}


@pytest.fixture
def tape_root(tmp_path):
    folder = tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True)
    for day, seed in DAYS.items():
        lines = [json.dumps({"as_of_ist": datetime.fromtimestamp(t.ts, IST).isoformat(), "underlyings": [_snap(t)]})
                 for t in synthetic_triples(day=day, seed=seed)]
        (folder / f"{day}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", ps.resolve_lot_size)  # the script pins it; undo after
    monkeypatch.setattr(fs, "load_founder_book", fs.load_founder_book)


def _tree(root):
    return sorted((str(p.relative_to(root)), p.stat().st_size) for p in root.rglob("*") if p.is_file())


def test_ablation_steps_on_a_synthetic_tape_folder(tape_root, tmp_path, capsys):
    before = _tree(tape_root / "data")
    out_json = tmp_path / "out" / "ablation.json"
    rc = _load_script().main(["--tapes", str(tape_root / "data/recon/paper_watch/DUAL-TAPE"),
                              "--founder-start", "NIFTY", "--since", "2026-09-10", "--json", str(out_json)])
    assert rc == 0
    table = capsys.readouterr().out
    assert "| **TOTAL** |" in table and "5 +tick/trade-through" in table
    assert _tree(tape_root / "data") == before, "ablation wrote under the data root"
    res = json.loads(out_json.read_text())
    assert list(res) == list(DAYS)
    for day, st in res.items():
        board = ps.replay_paper_scalp(root=tape_root, underlyings=("NIFTY",), source="dual-tape", write=False,
                                      live_session=True, session_ist_date=day, use_event_bus=False)
        rows = [r for r in board["closed_trades"] if r["filled"]]
        assert st["0 legacy"]["n_trades"] == len(rows) >= 3
        assert st["0 legacy"]["net"] == round(sum(r["realized_pnl_inr"] for r in rows), 2)
        assert st["1 +slippage"]["decisions"] == st["0 legacy"]["decisions"]  # money moves, trades do not
        assert st["1 +slippage"]["slippage"] > 0
        assert st["0 legacy"]["slippage"] == 0.0

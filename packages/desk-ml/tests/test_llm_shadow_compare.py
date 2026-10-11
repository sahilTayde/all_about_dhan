"""Take/skip shadow compare: no look-ahead, 1.5x costs, no veto, frozen R3 lock."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from desk_ml.llm_judge import _board_fingerprint
from desk_ml.llm_shadow_compare import (
    COST_MULT,
    RANDOM_DRAWS,
    SCHEMA,
    feature_vector,
    fit_logit,
    load_founder_view,
    net_at_1_5x,
    r3_sha256,
    r4_status,
    random_skip_nets,
    run_day,
    verify_r3_lock,
)
from desk_ml.persist import code_root


def _trade(day: str, tid: str, net_gross: float, charges: float = 40.0, **kw) -> dict:
    entry = 100.0
    qty = 65
    exit_px = entry + net_gross / qty
    row = {
        "trade_id": tid,
        "day": day,
        "closed_ist": f"{day}T15:00:00+05:30",
        "opened_ist": f"{day}T10:20:00+05:30",
        "underlying": "NIFTY",
        "side": "CE",
        "book_id": "R01_PDIV_5_ALL_H20",
        "status": "CLOSED",
        "entry": entry,
        "exit": exit_px,
        "qty": qty,
        "gross_pnl_inr": net_gross,
        "charges_inr": charges,
        "realized_pnl_inr": net_gross - charges,
        "index_vs_vwap": kw.pop("index_vs_vwap", 12.0),
        "vix": kw.pop("vix", 14.0),
    }
    row.update(kw)
    return row


def _snap(vs: float, net: float, side: str = "CE") -> dict:
    return {
        "side": side,
        "hhmm": "10:20",
        "market": {
            "index_vs_vwap": vs,
            "phase": "open",
            "vix": 14.0,
            "candles_1m_15": {"net": net, "range": 20, "up": 8},
            "atm_ce": {"change": 2.0},
            "atm_pe": {"change": -1.0},
        },
    }


class FakePick:
    def __init__(self, decision: str = "SKIP") -> None:
        self.decision = decision
        self.calls = 0

    def __call__(self, *, system: str, user: str) -> dict:
        self.calls += 1
        assert "R3" in system or "TAKE|SKIP" in system
        return {
            "text": json.dumps({"decision": self.decision, "confidence": 0.6, "reason": "shadow only"}),
            "tokens_in": 20,
            "tokens_out": 10,
        }


def test_r3_lock_matches_frozen_prompt() -> None:
    check = verify_r3_lock(code_root())
    assert check["ok"] is True
    assert check["lock_ok"] is True
    folder = code_root() / "research" / "lab" / "2026-10-11_llm_judge" / "R3_PREREG"
    assert r3_sha256(folder) == check["sha256"]
    lock = json.loads((folder / "lock.json").read_text(encoding="utf-8"))
    parts = []
    for name in ("prompt.txt", "schema.json", "fields.json"):
        parts.append(name.encode() + b"\n" + (folder / name).read_bytes())
    assert hashlib.sha256(b"\n".join(parts)).hexdigest() == lock["sha256"]
    assert lock["trade"] is False


def test_r3_lock_detects_drift(tmp_path: Path) -> None:
    src = code_root() / "research" / "lab" / "2026-10-11_llm_judge"
    dest = tmp_path / "research" / "lab" / "2026-10-11_llm_judge"
    dest.mkdir(parents=True)
    import shutil

    shutil.copytree(src / "R3_PREREG", dest / "R3_PREREG")
    shutil.copytree(src / "R4_SLOT", dest / "R4_SLOT")
    (dest / "R3_PREREG" / "prompt.txt").write_text("tampered\n", encoding="utf-8")
    check = verify_r3_lock(tmp_path)
    assert check["ok"] is False
    assert check["status"] == "LOCK_MISMATCH"


def test_v2_prereg_lock_untouched() -> None:
    path = code_root() / "config" / "v2" / "forward" / "prereg.lock"
    text = path.read_text(encoding="utf-8")
    assert "R8-E1-COIL-SIDE" in text
    assert "R8-E2-P5-HV" in text
    assert "R8-E3-HV-GATE" in text
    assert "PENDING_LAB" in text


def test_net_uses_1_5x_dhan_charges() -> None:
    trade = _trade("2026-10-08", "a", net_gross=200.0, charges=80.0)
    assert COST_MULT == 1.5
    assert net_at_1_5x(trade) == 200.0 - 1.5 * 80.0


def test_logit_refuses_look_ahead() -> None:
    rows = []
    for i, day in enumerate(("2026-10-06", "2026-10-07", "2026-10-08")):
        vs = 10.0 if i == 0 else (-20.0 if i == 2 else 1.0)
        label = True if i == 0 else False
        rows.append(
            {
                "day": day,
                "features": feature_vector(_snap(vs, 5.0 if label else -8.0)),
                "label": label,
                "net_1_5x": 50.0 if label else -40.0,
            }
        )
    # pad prior days so n>=8 and both classes
    for i in range(8):
        win = i % 2 == 0
        rows.append(
            {
                "day": "2026-10-05",
                "features": feature_vector(_snap(12.0 if win else -12.0, 6.0 if win else -6.0)),
                "label": win,
                "net_1_5x": 20.0 if win else -15.0,
            }
        )
    model = fit_logit(rows, score_day="2026-10-07")
    assert model["ok"] is True
    assert model["lookahead"] is False
    assert all(d < "2026-10-07" for d in model["train_days"])
    assert "2026-10-07" not in model["train_days"]
    assert "2026-10-08" not in model["train_days"]
    leaky = fit_logit(rows, score_day="2026-10-09")
    assert "2026-10-08" in leaky["train_days"]
    assert model["weights"] != leaky["weights"]


def test_random_skip_uses_2000_draws() -> None:
    out = random_skip_nets([10.0, -4.0, 6.0, -2.0], skip_n=1, draws=RANDOM_DRAWS, seed=3)
    assert out["draws"] == 2000
    assert out["skip_n"] == 1
    assert out["p05_net_inr"] <= out["mean_net_inr"] <= out["p95_net_inr"]


def test_r4_missing_prompt_is_loud(tmp_path: Path) -> None:
    out = r4_status(tmp_path)
    assert out["status"] == "MISSING_PROMPT"
    assert out["ok"] is False
    assert out["prompt"] is None
    assert "llm_debrief" in str(out["drop_path"])
    assert out["expected_sha256_prefix"] == "cd147c1a"
    assert "SLOT_EMPTY" not in json.dumps(out)


def test_r4_lock_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "research" / "lab" / "2026-10-11_llm_debrief" / "R4" / "prompt.txt"
    path.parent.mkdir(parents=True)
    path.write_text("not the frozen r4 prompt\n", encoding="utf-8")
    out = r4_status(tmp_path)
    assert out["status"] == "LOCK_MISMATCH"
    assert out["ok"] is False
    assert out["prompt"] is None
    assert not str(out["sha256"]).startswith("cd147c1a")
    assert out["expected_sha256_prefix"] == "cd147c1a"


def test_r4_ok_when_prefix_matches(tmp_path: Path) -> None:
    path = tmp_path / "custom_r4.txt"
    body = "frozen r4 take/skip prompt\n"
    path.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    out = r4_status(tmp_path, cfg={"r4_prompt_path": str(path), "r4_sha256_prefix": digest[:8]})
    assert out["status"] == "ok"
    assert out["ok"] is True
    assert out["prompt"] == body.strip()
    assert out["sha256"] == digest


def test_run_day_is_shadow_only_and_r4_missing(tmp_path: Path) -> None:
    src = code_root() / "research" / "lab" / "2026-10-11_llm_judge"
    dest = tmp_path / "research" / "lab" / "2026-10-11_llm_judge"
    dest.mkdir(parents=True)
    import shutil

    shutil.copytree(src / "R3_PREREG", dest / "R3_PREREG")
    shutil.copytree(src / "R4_SLOT", dest / "R4_SLOT")
    prior = [_trade("2026-10-08", f"p{i}", 80.0 if i % 2 == 0 else -50.0, index_vs_vwap=10 if i % 2 == 0 else -8) for i in range(10)]
    today = [
        _trade("2026-10-10", "t-win", 120.0, index_vs_vwap=15),
        _trade("2026-10-10", "t-lose", -90.0, index_vs_vwap=-10),
    ]
    picks = [
        {"job": "PICK", "trade_id": "t-win", "snapshot": _snap(15, 8), "decision": "TAKE"},
        {"job": "PICK", "trade_id": "t-lose", "snapshot": _snap(-10, -6), "decision": "SKIP"},
    ]
    board = {"open_trades": [{"trade_id": "live", "entry": 99.0, "status": "OPEN_PAPER"}], "closed_trades": today}
    before = _board_fingerprint(board)
    fake = FakePick("SKIP")
    out = run_day(
        "2026-10-10",
        root=tmp_path,
        trades=today,
        prior_trades=prior,
        picks=picks,
        complete_fn=fake,
        persist=True,
    )
    assert out["schema"] == SCHEMA
    assert out["trade"] is False
    assert out["veto"] is False
    assert out["promote"] is False
    assert out["cost_mult"] == 1.5
    assert out["arms"]["r3"]["lock_ok"] is True
    assert out["arms"]["r4"]["status"] == "MISSING_PROMPT"
    assert "llm_debrief" in str(out["arms"]["r4"].get("drop_path") or "")
    assert out["arms"]["r4"].get("expected_sha256_prefix") == "cd147c1a"
    assert out["arms"]["logit"]["lookahead"] is False
    assert all(d < "2026-10-10" for d in (out["arms"]["logit"].get("train_days") or []))
    assert out["arms"]["random"]["draws"] == 2000
    assert (tmp_path / "data" / "recon" / "llm_shadow_compare" / "2026-10-10.json").is_file()
    view = load_founder_view(tmp_path)
    assert view["trade"] is False
    assert view["n_days"] == 1
    assert view["r4"]["status"] == "MISSING_PROMPT"
    assert "cd147c1a" in str(view["r4"].get("expected_sha256_prefix"))
    assert _board_fingerprint(board) == before
    assert board["open_trades"][0]["entry"] == 99.0

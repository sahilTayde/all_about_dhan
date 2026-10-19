"""2026-10-19 (Sahil OK): ENG_5, EP018, IB_15, MINE_PE, ORB_A, R07 SHADOW ONLY from the 2026-10-21 IST session.
Still scored as shadow; book nothing on the desk; EP010, VWAP_CONT, Q01, B2, IB_5 unchanged."""
from __future__ import annotations

import json

from desk_ml import research_rules as rr

SIX = {"PX_ENG_5", "PX_EP018", "PX_IB_15", "PX_MINE_PE", "PX_ORB_A", "PX_R07"}
KEEP = {"PX_EP010", "PX_VWAP_CONT", "PX_B2", "PX_IB_5"}


def test_config_dates_and_ids() -> None:
    assert rr.desk_shadow_only("2026-10-20") == set()
    assert rr.desk_shadow_only("2026-10-21") == SIX
    assert rr.desk_shadow_only("2026-11-30") == SIX
    assert not (KEEP | {"Q01", "PX_Q01"}) & rr.desk_shadow_only("2026-10-21")
    # the desk rules_off list is unchanged
    assert {"B2b", "R20", rr.R02, rr.R01, rr.R01_B3A} <= rr.desk_rules_off()


def _write(tmp_path, day, rows):
    p = tmp_path / "data" / "recon" / "paper_extra"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{day}.json").write_text(json.dumps({"day": day, "orders": "REFUSED", "rows": rows}))


def _closed(rid, side, sig, ent, ext, strike):
    return {"rule_id": rid, "strategy": rid, "underlying": "NIFTY", "side": side, "strike": strike, "signal_time": sig,
            "entry_time": ent, "entry_px": 100.0, "status": "CLOSED", "exit_time": ext, "exit_px": 110.0, "exit_reason": "TARGET"}


def _rows():
    rows, k = [], 25000.0
    for i, rid in enumerate(sorted(SIX | KEEP)):   # one at a time (exit before the next entry) so desk limits never bite
        m = 9 * 60 + 30 + 30 * i; hm = lambda x: f"{x // 60:02d}:{x % 60:02d}"
        rows.append(_closed(rid, "CE", hm(m), hm(m + 1), hm(m + 10), k + 100 * i))
    return rows


def test_replay_books_zero_shadow_rows_from_oct21(tmp_path) -> None:
    day = "2026-10-21"
    _write(tmp_path, day, _rows())
    res = rr.replay(tmp_path, day)
    desk = {r["rule_id"] for r in res["open"] + res["closed"]}
    sh = {r["rule_id"] for r in res["shadow_parked"]["open"] + res["shadow_parked"]["closed"]}
    assert not desk & SIX
    assert SIX <= sh                       # still logged and scored as shadow
    assert KEEP <= desk                    # others still booked
    assert all(r.get("shadow_reason", "").startswith("SHADOW_ONLY") for r in res["shadow_parked"]["closed"] if r["rule_id"] in SIX)
    assert not {b["rule_id"] for b in res["risk_blocked"] + res["guard_blocked"]} & SIX   # no slot / risk use


def test_replay_before_oct21_unchanged(tmp_path) -> None:
    day = "2026-10-20"
    _write(tmp_path, day, _rows())
    res = rr.replay(tmp_path, day)
    sh = {r["rule_id"] for r in res["shadow_parked"]["open"] + res["shadow_parked"]["closed"]}
    assert not sh & SIX

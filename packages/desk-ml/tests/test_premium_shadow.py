"""Premium-stop background shadows (EP009_P, B2_P, VWAPCONT_PE_P): port of ps_a.py one() vs Research trades_a.csv.
Fixture = 161 historical cases (all exit kinds, 3 configs) cut from the box replay (1156/1156 signals matched, 0 mismatches)."""
import json
from pathlib import Path

import pytest

from desk_ml import premium_shadow as PS

FX = json.loads((Path(__file__).parent / "fixtures" / "premium_shadow" / "fixture_ps.json").read_text())
FINAL = {"CLOSED", "NO_ENTRY", "NO_EXIT"}


def _b(c):
    return {int(m): tuple(v) for m, v in c["b"].items()}


def _run(c, last=10**9):
    S, k = PS.CONFIGS[c["name"]][2:4]
    return PS.exit_one(_b(c), c["e_m"], S, k, hold=c["hold"], capx=c["capx"], last=last)


def test_sealed_configs():
    assert PS.CONFIGS == {"EP009_P": ("EP-009", 50, 0.2, 2.0, 1, False), "B2_P": ("B2", 200, 0.3, 2.0, 0, False),
                          "VWAPCONT_PE_P": ("VWAP_CONT", 100, 0.3, 1.5, 1, True)}
    assert PS.strike(25012, 1, 50) == 24950 and PS.strike(25012, -1, 100) == 25100


@pytest.mark.parametrize("i", range(len(FX)))
def test_matches_research(i):
    c = FX[i]; e = c["exp"]; g = _run(c)
    if e["status"] != "CLOSED":
        assert g["status"] == e["status"]; return
    for f in ("status", "em", "xm", "kind"):
        assert g[f] == e[f], f
    assert g["en"] == pytest.approx(e["en"]) and g["ex"] == pytest.approx(e["ex"])
    S, k = PS.CONFIGS[c["name"]][2:4]
    assert g["stop_px"] == round(e["en"] * (1 - S), 2) and g["target_px"] == round(e["en"] + k * S * e["en"], 2)


@pytest.mark.parametrize("i", range(0, len(FX), 3))
def test_live_complete_minutes_only(i):
    """At every live minute the answer is either not final yet or already the final answer; future bars never matter."""
    c = FX[i]; fin = _run(c)
    for last in range(c["e_m"] - 1, 920):
        g = _run(c, last)
        b2 = {m: ((9e9, 9e9) if m > last else v) for m, v in _b(c).items()}   # poison every bar after `last`
        S, k = PS.CONFIGS[c["name"]][2:4]
        assert PS.exit_one(b2, c["e_m"], S, k, hold=c["hold"], capx=c["capx"], last=last) == g
        if g["status"] in FINAL:
            assert g == fin; break
        assert g["status"] in ("PENDING_ENTRY", "OPEN", "EXITING")


def test_cap_unknown_never_time_exits():
    b = {m: (100.0, 100.0) for m in range(560, 700)}
    g = PS.exit_one(b, 560, 0.3, 2.0, capx=600, cap_known=False, last=650)
    assert g["status"] == "OPEN" and g["capm"] is None
    g = PS.exit_one(b, 560, 0.3, 2.0, capx=600, cap_known=True, last=650)
    assert g["status"] == "CLOSED" and g["kind"] == "TIME" and g["xm"] == 600


def test_stop_checked_first_and_next_open_fill():
    b = {560: (100.0, 100.0), 561: (100.0, 69.0), 562: (75.0, 80.0)}
    g = PS.exit_one(b, 560, 0.3, 2.0, hold=30, last=562)
    assert (g["kind"], g["xm"], g["fill_m"], g["ex"], g["en"]) == ("STOP", 561, 562, 74.95, 100.05)
    g = PS.exit_one(b, 560, 0.3, 2.0, hold=30, last=561)
    assert g["status"] == "EXITING"

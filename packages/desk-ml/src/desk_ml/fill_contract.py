"""Written SOD fill contract. Exam grades it. Does not change overlay or live orders.

Signal = finished 1m only. Paper fill = next minute ITM print or skip.
ATM LTP must never be booked as ITM. FOLLOWS may read last-tick ATM for a *vote*.
NO_PROMOTE. No live Dhan orders.
"""

from __future__ import annotations

from typing import Any, Optional

CONTRACT_ID = "SOD_FILL_CONTRACT_V1"
SIGNAL_CLOCK = "CLOSED_1M"
FILL_CLOCK = "NEXT_1M_ITM_OR_SKIP"
FOLLOWS_CLOCK = "LAST_TICK_ATM_OK_FOR_VOTE"
OBSERVER_CLOCK = "TWO_CLOSED_1M"
WANTED_QUOTE = "ITM"
FORBIDDEN_BOOKED = frozenset({"ATM", "MISSING_ITM"})

CONTRACT_PLAIN = (
    "Decide only after a 1-minute bar is finished. "
    "Paper fill uses the next minute's ITM price, or we skip. "
    "Never book ATM and call it ITM. "
    "FOLLOWS may use the last tick for its vote only — that is not the fill."
)


def grade_fill(
    *,
    bar_closed_1m: bool,
    opened: bool,
    quote_src: Optional[str],
    tape_kind: Optional[str] = None,
    rolled_1m: bool = False,
) -> dict[str, Any]:
    src = str(quote_src or "")
    kind = str(tape_kind or "").upper()
    if opened and (src in FORBIDDEN_BOOKED or src.startswith("MISSING")):
        verdict = "ATM_AS_ITM" if src == "ATM" else "MISSING_ITM_BOOKED"
        ok = False
        actual = src or "UNKNOWN"
    elif opened and not bar_closed_1m:
        verdict = "FILL_ON_FORMING_BAR"
        ok = False
        actual = "FORMING_ITM_LTP"
    elif opened and bar_closed_1m:
        verdict = "FILL_ON_NEXT_BAR_ITM"
        ok = True
        actual = src or "ITM"
    elif kind == "ATM" and not opened:
        verdict = "ATM_TAPE_NO_ITM_SKIP"
        ok = True
        actual = "SKIP"
    else:
        verdict = "NO_FILL"
        ok = True
        actual = "SKIP"
    return {
        "contract_id": CONTRACT_ID,
        "ok": ok,
        "verdict": verdict,
        "signal_clock": SIGNAL_CLOCK if bar_closed_1m else "FORMING_OR_WARMUP",
        "fill_clock_wanted": FILL_CLOCK,
        "fill_clock_actual": actual,
        "quote_src": src or None,
        "tape_kind": kind or None,
        "rolled_1m": bool(rolled_1m),
        "plain": CONTRACT_PLAIN,
    }

"""TV tester long/short → DhanHQ index-options CE/PE **buy first**.

Not equity short as the customer default. Not a TradingView Strategy Tester clone.
"""

from __future__ import annotations

from typing import Any, Iterable

BUY_CE = "CE"
BUY_PE = "PE"
EXIT_FLAT = "EXIT"
HOLD = "HOLD"

# TV Strategy Tester vocabulary → our lean.
_TV_LONG = frozenset({"buy", "long", "long_entry", "buy_ce", "ce", "strategy.long"})
_TV_SHORT = frozenset({"sell", "short", "short_entry", "buy_pe", "pe", "strategy.short"})
_TV_FLAT = frozenset({"flat", "exit", "close", "strategy.close", "strategy.close_all", "flatten"})


def map_tv_signal(tv: str, *, long_only: bool = False) -> str:
    """Map one TV tester event to a simulator lean.

    TV long/buy → BUY_CE. TV short/sell → BUY_PE (options buy, not stock short).
    Long-only scripts still emit EXIT on sell/flat so exits are counted, not discarded.
    """
    key = str(tv or "").strip().lower()
    if key in _TV_LONG:
        return BUY_CE
    if key in _TV_SHORT:
        if long_only:
            return EXIT_FLAT
        return BUY_PE
    if key in _TV_FLAT:
        return EXIT_FLAT
    return HOLD


def to_simulator_lean(mapped: str) -> str:
    """Simulator understands CE / PE / EXIT / HOLD. EXIT flattens; it does not enter PE."""
    if mapped in (BUY_CE, "BUY_CE"):
        return BUY_CE
    if mapped in (BUY_PE, "BUY_PE"):
        return BUY_PE
    if mapped in (EXIT_FLAT, "BUY_EXIT", "FLAT"):
        return EXIT_FLAT
    return HOLD


def count_lean_sides(leans: Iterable[str]) -> dict[str, int]:
    buy_ce = buy_pe = exit_n = hold_n = 0
    for raw in leans:
        x = str(raw)
        if x in (BUY_CE, "BUY_CE"):
            buy_ce += 1
        elif x in (BUY_PE, "BUY_PE"):
            buy_pe += 1
        elif x in (EXIT_FLAT, "FLAT"):
            exit_n += 1
        else:
            hold_n += 1
    return {
        "buy_ce_signals": buy_ce,
        "buy_pe_signals": buy_pe,
        "exit_flat_signals": exit_n,
        "hold_bars": hold_n,
    }


def side_label(*, buy_ce_n: int, buy_pe_n: int, exit_n: int = 0) -> str:
    if buy_ce_n and buy_pe_n:
        return "BOTH"
    if buy_ce_n:
        return "CE"
    if buy_pe_n:
        return "PE"
    if exit_n:
        return "EXIT"
    return "NONE"


def after_cost_note(row: dict[str, Any]) -> str:
    tape = row.get("tape")
    after = row.get("after_cost_points")
    gross = row.get("gross_points")
    if row.get("gap"):
        return "n/a (no tape or unported)"
    if tape == "INDEX":
        if gross is None:
            return "INDEX proxy pts; no option haircut"
        return f"INDEX proxy gross {gross:.4f} (≠ option P/L)"
    if after is None:
        return "PREMIUM HYPOTHESIS_OPTION_RT_1PCT"
    return f"PREMIUM after-cost {after:.4f} (1% RT HYPOTHESIS)"


def tune_hint(row: dict[str, Any], *, adapter_gap: str = "") -> str:
    status = row.get("status")
    if adapter_gap:
        return adapter_gap
    if status == "DATA_INSUFFICIENT":
        return "KEEP row; fill tape or public-rule port"
    if status == "PARK":
        return "n<5 trades; longer tape or faster public params"
    if status == "TESTED_FAIL":
        return "after-cost/gross ≤0; KEEP; do not promote"
    if status == "WATCH":
        return "lab only; OOS+NORMAL still required; NO_PROMOTE"
    return "KEEP_ALL; status+reason only"

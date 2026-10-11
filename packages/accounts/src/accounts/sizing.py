"""C5 paper slot sizing: 10 lots, 15% premium stop, daily loss cap. No live broker."""

from __future__ import annotations

from typing import Any

from contracts.instruments import India

from accounts.errors import AccountClosed, AccountSafetyError
from accounts.model import Account

C5_PAPER_UNDERLYINGS = ("NIFTY", "SENSEX")
DEFAULT_C5_LOTS = 10
DEFAULT_PREMIUM_STOP_PCT = 0.15
DEFAULT_REF_PREMIUM_INR = 200


def paper_lots(account: Account) -> int:
    return account.lots if account.lots > 0 else DEFAULT_C5_LOTS


def lot_size_for(underlying: str, *, market: India | None = None) -> int:
    return (market or India()).lot_size(underlying.upper())


def paper_qty(account: Account, underlying: str, *, market: India | None = None) -> int:
    return paper_lots(account) * lot_size_for(underlying, market=market)


def stop_inr_per_lot(account: Account, underlying: str, *, market: India | None = None) -> int:
    lot = lot_size_for(underlying, market=market)
    raw = float(account.ref_premium_inr) * float(account.premium_stop_pct) * float(lot)
    stop = int(raw)
    if stop <= 0:
        raise AccountClosed("STOP_INR_INVALID")
    return stop


def stop_budget_inr(account: Account, underlying: str, *, market: India | None = None) -> int:
    return paper_lots(account) * stop_inr_per_lot(account, underlying, market=market)


def daily_loss_cap_inr(account: Account) -> int:
    return account.daily_loss_cap_inr if account.daily_loss_cap_inr > 0 else account.risk_budget_inr


def planned_paper_size(account: Account, *, market: India | None = None) -> dict[str, Any]:
    """Fail closed if risk_budget cannot fund a 10-lot 15% NIFTY stop. Paper only."""
    adapter = market or India()
    lots = paper_lots(account)
    qty = {und: paper_qty(account, und, market=adapter) for und in C5_PAPER_UNDERLYINGS}
    lot_size = {und: lot_size_for(und, market=adapter) for und in C5_PAPER_UNDERLYINGS}
    stop_budget = {und: stop_budget_inr(account, und, market=adapter) for und in C5_PAPER_UNDERLYINGS}
    nifty_need = stop_budget["NIFTY"]
    if account.risk_budget_inr < nifty_need:
        raise AccountSafetyError(
            f"V2 accounts fail-closed: risk_budget_inr {account.risk_budget_inr} "
            f"cannot fund {lots} NIFTY lots (need {nifty_need} for 15% premium stop)"
        )
    cap = daily_loss_cap_inr(account)
    if cap < nifty_need:
        raise AccountSafetyError(
            f"V2 accounts fail-closed: daily_loss_cap_inr {cap} cannot cover {lots} NIFTY lots (need {nifty_need})"
        )
    return {
        "lots": lots,
        "qty": qty,
        "lot_size": lot_size,
        "premium_stop_pct": account.premium_stop_pct,
        "ref_premium_inr": account.ref_premium_inr,
        "daily_loss_cap_inr": cap,
        "risk_budget_inr": account.risk_budget_inr,
        "stop_budget_inr": stop_budget,
        "live_broker": False,
    }

"""Optional one-shot premium bind onto desk signals for GET /paper/signal.

Used when /ws/signals has not yet populated live_paper. Soft-fail. Orders refused.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from backtest_engine.levels import bind_option_premium_levels, quarantine_index_proxy_from_customer_ticket
from backtest_engine.option_premium_ltp import fetch_atm_option_premium_ltp


def _lean_from_side(side: Any) -> Optional[str]:
    s = str(side or "").upper()
    if s in ("BUY_CE", "CE"):
        return "CE"
    if s in ("BUY_PE", "PE"):
        return "PE"
    return None


def bind_premiums_onto_desk(
    desk: dict[str, Any],
    *,
    prefer_live: bool = True,
) -> dict[str, Any]:
    """For each CE/PE signal, try ATM option LTP and fill Entry/Target (Stop may DI)."""
    out = deepcopy(desk)
    signals = dict(out.get("signals") or {})
    any_ok = False
    gaps: list[str] = []
    for name, sig in list(signals.items()):
        if not isinstance(sig, dict):
            continue
        lean = _lean_from_side(sig.get("side"))
        if lean is None:
            continue
        spot = sig.get("underlying_spot")
        if spot is None:
            spot = sig.get("spot")
        try:
            spot_f = float(spot) if spot not in (None, "", "DATA_INSUFFICIENT") else None
        except (TypeError, ValueError):
            spot_f = None
        quote = fetch_atm_option_premium_ltp(
            name,
            lean,
            prefer_live=prefer_live,
            spot_hint=spot_f,
        )
        gaps.extend(quote.data_gaps or [quote.reason])
        ticket = dict(sig.get("ticket") or {})
        # Start from existing ticket / quarantine index masquerade
        base_levels = {
            **ticket,
            "entry": sig.get("entry") if ticket.get("entry") is None else ticket.get("entry"),
            "stop": sig.get("stop") if ticket.get("stop") is None else ticket.get("stop"),
            "target": sig.get("target") if ticket.get("target") is None else ticket.get("target"),
            "strike": sig.get("strike") if ticket.get("strike") is None else ticket.get("strike"),
            "unit": ticket.get("unit") or "OPTION_PREMIUM",
        }
        # If slots look like index, quarantine first
        quarantined = quarantine_index_proxy_from_customer_ticket(
            {
                **base_levels,
                "unit": (
                    "INDEX_POINTS_PROXY"
                    if str(base_levels.get("unit", "")).upper().startswith("INDEX")
                    else base_levels.get("unit") or "OPTION_PREMIUM"
                ),
            },
            underlying_spot=spot_f,
            option_ltp=quote.ltp if quote.ok else None,
            lean=lean,
            premium_meta={
                "reason": quote.reason,
                "source": quote.source,
                "expiry": quote.expiry,
                "strike": quote.strike,
                "underlying_spot": quote.underlying_spot or spot_f,
            },
        )
        if quote.ok and quote.ltp is not None:
            bound = bind_option_premium_levels(
                option_ltp=quote.ltp,
                lean=lean,
                strike=quote.strike or sig.get("strike"),
                underlying_spot=quote.underlying_spot or spot_f,
                expiry=quote.expiry,
                premium_source=quote.source,
            )
            # Keep index_* from quarantine if present
            for k in ("index_entry", "index_stop", "index_target"):
                if quarantined.get(k) is not None:
                    bound[k] = quarantined[k]
            sig = dict(sig)
            sig["entry"] = bound["entry"]
            sig["stop"] = bound["stop"] if bound["stop"] is not None else "DATA_INSUFFICIENT"
            sig["target"] = bound["target"]
            if bound.get("strike") is not None:
                sig["strike"] = bound["strike"]
            if bound.get("expiry"):
                sig["expiry"] = bound["expiry"]
            if bound.get("underlying_spot") is not None:
                sig["underlying_spot"] = bound["underlying_spot"]
                sig["spot"] = bound["underlying_spot"]
            sig["ticket"] = bound
            sig["premium_quote"] = quote.to_dict()
            any_ok = True
        else:
            sig = dict(sig)
            sig["entry"] = "DATA_INSUFFICIENT"
            sig["stop"] = "DATA_INSUFFICIENT"
            sig["target"] = "DATA_INSUFFICIENT"
            sig["ticket"] = quarantined
            sig["premium_quote"] = quote.to_dict()
        signals[name] = sig

    meta = dict(out.get("meta") or {})
    meta["premium_bind"] = "ok" if any_ok else "DATA_INSUFFICIENT"
    meta["premium_gaps"] = list(dict.fromkeys(gaps))[:8]
    meta["orders"] = "refused"
    if any_ok:
        meta["source"] = meta.get("source") if meta.get("source") == "paper_live" else "paper_premium_bind"
        meta["label"] = meta.get("label") or "PAPER"
        meta["placeholder"] = False
        meta["note"] = (
            "Option premium Entry/Target bound from ATM optionchain LTP "
            "(MIX-SLTP-PREM-PCT). Stop: MIX-SLTP-SWING-STOP binds underlying "
            "recent-swing to index_stop when bars exist; premium Stop stays DI "
            "without greeks map (no premium-% invent). Orders refused."
        )
    out["meta"] = meta
    out["signals"] = signals
    return out

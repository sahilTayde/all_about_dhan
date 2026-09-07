"""Fetch ATM CE/PE option LTP from Dhan POST /optionchain for customer tickets.

Rate-limited (1 unique / 3s). Fail soft → DATA_INSUFFICIENT reason. Never invents
premium. Never places orders. INDEX spot stays separate from premium LTP.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# VERIFY vs instrument master — same hints as desk-intel / chain hooks.
_SCRIP_HINTS = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "SENSEX": (51, "IDX_I"),
}

# Cache TTL must respect optionchain budget (1 unique / 3s) + expiry list call.
_CACHE_TTL_SEC = 6.0
_cache: dict[str, tuple[float, "OptionPremiumQuote"]] = {}


@dataclass
class OptionPremiumQuote:
    underlying: str
    lean: str  # CE | PE
    strike: Optional[int]
    expiry: Optional[str]
    ltp: Optional[float]
    security_id: Optional[int]
    underlying_spot: Optional[float]
    source: str  # dhan_optionchain | unavailable | dry_run | cache
    ok: bool
    reason: str
    data_gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _num(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _parse_expiry_list(payload: dict[str, Any]) -> Optional[str]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list) and data:
        return str(data[0])
    if isinstance(data, dict):
        lst = data.get("expiryList") or data.get("expiries") or []
        if lst:
            return str(lst[0])
    return None


def _parse_oc_rows(oc: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(oc, dict):
        items = oc.items()
    elif isinstance(oc, list):
        items = []
        for entry in oc:
            if isinstance(entry, dict):
                strike = entry.get("strike") or entry.get("Strike") or entry.get("strikePrice")
                items.append((strike, entry))
    else:
        return rows
    for strike_key, cell in items:
        if not isinstance(cell, dict):
            continue
        ce = cell.get("ce") or cell.get("CE") or {}
        pe = cell.get("pe") or cell.get("PE") or {}
        if not isinstance(ce, dict):
            ce = {}
        if not isinstance(pe, dict):
            pe = {}
        strike = _num(strike_key if strike_key not in (None, "") else cell.get("strike"))
        if strike is None:
            continue
        rows.append(
            {
                "strike": int(round(strike)),
                "ce_ltp": _num(ce.get("last_price") or ce.get("ltp")),
                "pe_ltp": _num(pe.get("last_price") or pe.get("ltp")),
                "ce_sid": ce.get("security_id") or ce.get("securityId"),
                "pe_sid": pe.get("security_id") or pe.get("securityId"),
            }
        )
    rows.sort(key=lambda r: r["strike"])
    return rows


def _atm_row(rows: list[dict[str, Any]], spot: Optional[float]) -> Optional[dict[str, Any]]:
    if not rows:
        return None
    if spot is None:
        return rows[len(rows) // 2]
    best = rows[0]
    best_d = abs(best["strike"] - float(spot))
    for row in rows[1:]:
        d = abs(row["strike"] - float(spot))
        if d < best_d:
            best = row
            best_d = d
    return best


def _unavailable(
    underlying: str,
    lean: str,
    reason: str,
    *,
    source: str = "unavailable",
    gaps: Optional[list[str]] = None,
) -> OptionPremiumQuote:
    return OptionPremiumQuote(
        underlying=underlying,
        lean=lean,
        strike=None,
        expiry=None,
        ltp=None,
        security_id=None,
        underlying_spot=None,
        source=source,
        ok=False,
        reason=reason,
        data_gaps=list(gaps or [reason]),
    )


def fetch_atm_option_premium_ltp(
    underlying: str,
    lean: str,
    *,
    prefer_live: bool = True,
    spot_hint: Optional[float] = None,
    force: bool = False,
) -> OptionPremiumQuote:
    """ATM CE/PE last_price from POST /optionchain. Soft-fail with DI reason."""
    und = underlying.upper()
    side = lean.upper().replace("BUY_", "")
    if side not in ("CE", "PE"):
        return _unavailable(und, side or "?", "DATA_INSUFFICIENT: lean not CE/PE — no premium fetch")

    cache_key = f"{und}:{side}"
    now = time.time()
    if not force and cache_key in _cache:
        ts, quote = _cache[cache_key]
        if now - ts < _CACHE_TTL_SEC:
            cached = OptionPremiumQuote(**{**quote.to_dict(), "source": "cache"})
            return cached

    if not prefer_live:
        return _unavailable(
            und,
            side,
            "DATA_INSUFFICIENT: OPTIDX premium not fetched (prefer_live=false)",
            source="unavailable",
        )

    hint = _SCRIP_HINTS.get(und)
    if hint is None:
        return _unavailable(und, side, f"DATA_INSUFFICIENT: unknown underlying {und}")

    scrip, seg = hint
    try:
        from dhan_client import DhanClient  # type: ignore
    except Exception:
        return _unavailable(
            und,
            side,
            "DATA_INSUFFICIENT: dhan_client unavailable — OPTIDX premium not fetched",
        )

    try:
        client = DhanClient(dry_run=False)
        if getattr(client.settings, "dry_run", True):
            client.close()
            q = _unavailable(
                und,
                side,
                "DATA_INSUFFICIENT: Dhan dry_run / tokens empty — OPTIDX premium not fetched",
                source="dry_run",
            )
            _cache[cache_key] = (now, q)
            return q

        body_u = {"UnderlyingScrip": scrip, "UnderlyingSeg": seg}
        expiries = client.option_chain.expiry_list(body_u)
        expiry = _parse_expiry_list(expiries if isinstance(expiries, dict) else {})
        if not expiry:
            client.close()
            q = _unavailable(
                und,
                side,
                "DATA_INSUFFICIENT: optionchain expiry list empty/unparsed — OPTIDX premium not fetched",
            )
            _cache[cache_key] = (now, q)
            return q

        raw = client.option_chain.chain({**body_u, "Expiry": expiry})
        client.close()
        data = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(data, dict):
            q = _unavailable(
                und,
                side,
                "DATA_INSUFFICIENT: optionchain payload missing data — OPTIDX premium not fetched",
            )
            _cache[cache_key] = (now, q)
            return q

        spot = _num(data.get("last_price")) or spot_hint
        rows = _parse_oc_rows(data.get("oc"))
        atm = _atm_row(rows, spot)
        if atm is None:
            q = _unavailable(
                und,
                side,
                "DATA_INSUFFICIENT: optionchain oc empty — OPTIDX premium not fetched",
            )
            _cache[cache_key] = (now, q)
            return q

        ltp = atm["ce_ltp"] if side == "CE" else atm["pe_ltp"]
        sid = atm["ce_sid"] if side == "CE" else atm["pe_sid"]
        if ltp is None or ltp <= 0:
            q = _unavailable(
                und,
                side,
                f"DATA_INSUFFICIENT: ATM {side} last_price missing on optionchain — OPTIDX premium not fetched",
            )
            q.strike = int(atm["strike"])
            q.expiry = expiry
            q.underlying_spot = spot
            _cache[cache_key] = (now, q)
            return q

        sid_i: Optional[int] = None
        try:
            if sid not in (None, ""):
                sid_i = int(sid)
        except (TypeError, ValueError):
            sid_i = None

        q = OptionPremiumQuote(
            underlying=und,
            lean=side,
            strike=int(atm["strike"]),
            expiry=expiry,
            ltp=round(float(ltp), 2),
            security_id=sid_i,
            underlying_spot=round(float(spot), 2) if spot is not None else None,
            source="dhan_optionchain",
            ok=True,
            reason="ATM option last_price from POST /optionchain",
            data_gaps=[],
        )
        _cache[cache_key] = (now, q)
        return q
    except Exception as exc:  # noqa: BLE001
        detail = type(exc).__name__
        status = getattr(exc, "status_code", None)
        if status is not None:
            detail = f"{detail} HTTP {status}"
        q = _unavailable(
            und,
            side,
            f"DATA_INSUFFICIENT: OPTIDX/optionchain {detail} — premium not fetched",
            gaps=[f"DATA_INSUFFICIENT: OPTIDX {detail}"],
        )
        _cache[cache_key] = (now, q)
        return q


def clear_premium_ltp_cache() -> None:
    _cache.clear()

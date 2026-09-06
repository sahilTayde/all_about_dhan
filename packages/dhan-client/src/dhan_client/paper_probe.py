"""Sanitized live Data-API probe. No orders. Never writes tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.errors import DhanApiError, SafeModeError
from dhan_client.logging_util import is_secret_key

IST = timezone(timedelta(hours=5, minutes=30))

# yaml markets[] — still VERIFY against instrument master in the same run.
YAML_UNDERLYINGS = (
    ("NIFTY", 13, "IDX_I", "NSE_FNO"),
    ("BANKNIFTY", 25, "IDX_I", "NSE_FNO"),
    ("SENSEX", 51, "IDX_I", "BSE_FNO"),
)


def _keys_only(payload: Any, *, max_depth: int = 2) -> Any:
    if isinstance(payload, dict):
        if max_depth <= 0:
            return sorted(str(k) for k in payload.keys())
        out: dict[str, Any] = {}
        for key, value in payload.items():
            name = str(key)
            if is_secret_key(name) or name.lower() in {
                "dhanclientid",
                "clientid",
                "client_id",
                "tokenvalidity",
            }:
                out[name] = "REDACTED"
            elif isinstance(value, (dict, list)):
                out[name] = _keys_only(value, max_depth=max_depth - 1)
            elif isinstance(value, str) and len(value) > 80:
                out[name] = f"<str len={len(value)}>"
            else:
                out[name] = value
        return out
    if isinstance(payload, list):
        return {"len": len(payload), "sample_type": type(payload[0]).__name__ if payload else None}
    return payload


def _safe_call(label: str, fn) -> dict[str, Any]:
    try:
        data = fn()
        return {"ok": True, "label": label, "data": data}
    except DhanApiError as exc:
        return {
            "ok": False,
            "label": label,
            "status_code": exc.status_code,
            "error_type": exc.error_type,
            "error_code": exc.error_code,
            "message": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 — probe must not crash the CLI
        return {"ok": False, "label": label, "message": type(exc).__name__}


def _summarize_chain(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {"keys": list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}
    oc = data.get("oc")
    strikes = list(oc.keys()) if isinstance(oc, dict) else []
    return {
        "status": payload.get("status"),
        "last_price": data.get("last_price"),
        "strike_count": len(strikes),
    }


def _summarize_expiry(payload: dict[str, Any]) -> dict[str, Any]:
    dates = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(dates, list):
        return {"raw_keys": list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}
    return {"status": payload.get("status"), "expiry_count": len(dates), "nearest": dates[0] if dates else None, "dates_head": dates[:6]}


def _summarize_ltp(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, dict):
        return {"keys": list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}
    return {"status": payload.get("status"), "segments": {k: list(v.keys()) if isinstance(v, dict) else type(v).__name__ for k, v in data.items()}}


def _summarize_bars(payload: dict[str, Any]) -> dict[str, Any]:
    close = payload.get("close") if isinstance(payload, dict) else None
    ts = payload.get("timestamp") if isinstance(payload, dict) else None
    n = len(close) if isinstance(close, list) else None
    return {
        "bar_count": n,
        "has_volume": isinstance(payload.get("volume"), list),
        "has_oi": isinstance(payload.get("open_interest"), list),
        "first_ts": ts[0] if isinstance(ts, list) and ts else None,
        "last_ts": ts[-1] if isinstance(ts, list) and ts else None,
        "last_close": close[-1] if isinstance(close, list) and close else None,
    }


def run_paper_probe(client: DhanClient) -> dict[str, Any]:
    as_of = datetime.now(IST).isoformat()
    refused = False
    try:
        client.execution.place_order()
    except SafeModeError:
        refused = True

    profile = _safe_call("GET /profile", client.profile.get)
    if profile.get("ok"):
        profile["data"] = _keys_only(profile["data"], max_depth=1)

    idx_ltp = _safe_call(
        "POST /marketfeed/ltp IDX_I yaml scrips",
        lambda: client.quote.ltp({"IDX_I": [13, 25, 51]}),
    )
    if idx_ltp.get("ok"):
        idx_ltp["data"] = _summarize_ltp(idx_ltp["data"])

    expiries: list[dict[str, Any]] = []
    chains: list[dict[str, Any]] = []
    for name, scrip, seg, _quote_seg in YAML_UNDERLYINGS:
        exp = _safe_call(
            f"POST /optionchain/expirylist {name}",
            lambda s=scrip, g=seg: client.option_chain.expiry_list(
                {"UnderlyingScrip": s, "UnderlyingSeg": g}
            ),
        )
        if exp.get("ok"):
            summary = _summarize_expiry(exp["data"])
            exp["data"] = summary
            nearest = summary.get("nearest")
        else:
            nearest = None
        expiries.append({"underlying": name, "scrip": scrip, **{k: v for k, v in exp.items() if k != "label"}})
        if nearest:
            ch = _safe_call(
                f"POST /optionchain {name} {nearest}",
                lambda s=scrip, g=seg, e=nearest: client.option_chain.chain(
                    {"UnderlyingScrip": s, "UnderlyingSeg": g, "Expiry": e}
                ),
            )
            if ch.get("ok"):
                ch["data"] = _summarize_chain(ch["data"])
            chains.append({"underlying": name, "expiry": nearest, **{k: v for k, v in ch.items() if k != "label"}})

    # HQ 5m INDEX candles — instrument INDEX on IDX_I (spoken 3m is not in {1,5,15,25,60}).
    today = datetime.now(IST).date()
    from_d = (today - timedelta(days=5)).isoformat() + " 09:15:00"
    to_d = today.isoformat() + " 15:40:00"
    hist: list[dict[str, Any]] = []
    for name, scrip, seg, _q in YAML_UNDERLYINGS:
        row = _safe_call(
            f"POST /charts/intraday 5m INDEX {name}",
            lambda s=scrip, g=seg: client.historical.intraday(
                {
                    "securityId": str(s),
                    "exchangeSegment": g,
                    "instrument": "INDEX",
                    "interval": 5,
                    "fromDate": from_d,
                    "toDate": to_d,
                }
            ),
        )
        if row.get("ok"):
            row["data"] = _summarize_bars(row["data"])
        hist.append({"underlying": name, "scrip": scrip, **{k: v for k, v in row.items() if k != "label"}})

    return {
        "as_of_ist": as_of,
        "dry_run": client.dry_run,
        "orders": {"place_order_refused": refused},
        "rate_limits_cited": {
            "source": "https://dhanhq.co/docs/v2/",
            "order_per_sec": 10,
            "data_per_sec": 5,
            "quote_per_sec": 1,
            "non_trading_per_sec": 20,
            "option_chain_unique_seconds": 3,
            "data_per_day": 100000,
        },
        "yaml_scrips_verify": "markets[] 13/25/51 — still VERIFY vs instrument master",
        "profile": profile,
        "index_ltp": idx_ltp,
        "expiries": expiries,
        "chains": chains,
        "intraday_5m_index": hist,
        "note": (
            "Paper/data only. No live orders. Chain bodies truncated to strike_count. "
            "3m spoken STRAT-003 is not an HQ interval; 5m INDEX path is HQ-native."
        ),
    }

"""DATA-002: one-shot full chain + constituent LTPs. No poll loop. No orders."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from warehouse.constituents import INDEX_MEMBERS, ltp_from_quote, parse_equity_ids
from warehouse.feasibility import evaluate_long_premium
from warehouse.store import Warehouse

IST = timezone(timedelta(hours=5, minutes=30))
CHAIN_GAP_SEC = 3.2
UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
SCRIPS = {"NIFTY": 13, "BANKNIFTY": 25, "SENSEX": 51}


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _g(opt: dict[str, Any], name: str) -> Optional[float]:
    g = opt.get("greeks") if isinstance(opt.get("greeks"), dict) else {}
    raw = g.get(name)
    try:
        return float(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _strike_dicts(underlying: str, expiry: Optional[str], as_of: str, rows: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "underlying": underlying,
                "expiry": expiry,
                "as_of": as_of,
                "strike": row.strike,
                "ce_ltp": row.ce_ltp,
                "pe_ltp": row.pe_ltp,
                "ce_oi": row.ce_oi,
                "pe_oi": row.pe_oi,
                "ce_oi_prev": row.ce_oi_prev,
                "pe_oi_prev": row.pe_oi_prev,
                "ce_volume": row.ce_volume,
                "pe_volume": row.pe_volume,
                "ce_security_id": row.ce_security_id,
                "pe_security_id": row.pe_security_id,
                "ce_delta": row.ce_delta,
                "pe_delta": row.pe_delta,
                "ce_gamma": row.ce_gamma,
                "pe_gamma": row.pe_gamma,
                "ce_theta": getattr(row, "ce_theta", None),
                "pe_theta": getattr(row, "pe_theta", None),
                "ce_vega": getattr(row, "ce_vega", None),
                "pe_vega": getattr(row, "pe_vega", None),
                "ce_iv": getattr(row, "ce_iv", None),
                "pe_iv": getattr(row, "pe_iv", None),
            }
        )
    return out


def _levels(snapshot_id: int, underlying: str, expiry: Optional[str], as_of: str, atm: Any) -> list[dict[str, Any]]:
    if atm is None:
        return []
    out = []
    for side, ltp in (("CE", atm.ce_ltp), ("PE", atm.pe_ltp)):
        entry = float(ltp) if ltp not in (None, "") else None
        stop = round(entry * 0.75, 2) if entry else None
        target = round(entry * 1.25, 2) if entry else None
        decision = evaluate_long_premium(entry=entry, stop=stop, target=target, stage="WATCH")
        out.append(
            {
                "snapshot_id": snapshot_id,
                "underlying": underlying,
                "expiry": expiry,
                "as_of": as_of,
                "side": side,
                "strike": atm.strike,
                "entry": entry,
                "stop_hyp": stop,
                "target_hyp": target,
                "dealer_action": decision.action,
                "dealer_reason": decision.reason_code,
                "layer": "HYPOTHESIS",
            }
        )
    return out


def sync_desk_book(
    *,
    live: bool,
    warehouse: Optional[Warehouse] = None,
    sleep_s: float = CHAIN_GAP_SEC,
) -> dict[str, Any]:
    wh = warehouse or Warehouse()
    wh.init()
    report: dict[str, Any] = {
        "ok": False,
        "live": live,
        "loop_started": False,
        "orders": "refused",
        "weight_layer": "DATA_INSUFFICIENT",
        "chains": [],
        "constituents": {"resolved": 0, "quoted": 0, "missing": []},
        "gaps": [],
        "NO_PROMOTE": True,
    }
    if not live:
        report["gaps"].append("DATA_INSUFFICIENT: pass --live")
        report["status"] = wh.status()
        return report

    try:
        from dhan_client import DhanClient
        from desk_intel.option_chain_poller import atm_index, compute_chain_bias, parse_oc, unwrap_chain_payload
        from desk_intel.schema import ChainSnapshot as ChainSnap
    except Exception as exc:  # noqa: BLE001
        report["gaps"].append(f"import {type(exc).__name__}")
        report["status"] = wh.status()
        return report

    client = DhanClient(dry_run=False)
    if getattr(client.settings, "dry_run", True):
        client.close()
        report["gaps"].append("DATA_INSUFFICIENT: Dhan dry_run")
        report["status"] = wh.status()
        return report

    as_of = _now()
    try:
        text = client.instruments.fetch_scrip_master_text(detailed=True)
        all_syms = set()
        for names, _seg in INDEX_MEMBERS.values():
            all_syms.update(names)
        # Resolve NSE then BSE so Sensex names can live on BSE_EQ
        nse_ids = parse_equity_ids(text, all_syms, prefer_segment="NSE_EQ")
        bse_ids = parse_equity_ids(text, all_syms, prefer_segment="BSE_EQ")

        nse_body: list[int] = []
        bse_body: list[int] = []
        seen: set[int] = set()
        for names, seg in INDEX_MEMBERS.values():
            pool = nse_ids if seg == "NSE_EQ" else bse_ids
            for name in names:
                hit = pool.get(name) or nse_ids.get(name) or bse_ids.get(name)
                if not hit:
                    report["constituents"]["missing"].append(name)
                    continue
                sid, segment = hit
                try:
                    iid = int(sid)
                except ValueError:
                    report["constituents"]["missing"].append(name)
                    continue
                if iid in seen:
                    continue
                seen.add(iid)
                if segment == "BSE_EQ":
                    bse_body.append(iid)
                else:
                    nse_body.append(iid)
        report["constituents"]["resolved"] = len(seen)
        quote_map: dict[tuple[str, str], float] = {}
        if nse_body:
            quote_map.update(ltp_from_quote(client.quote.ltp({"NSE_EQ": nse_body})))
        if bse_body:
            time.sleep(1.05)
            quote_map.update(ltp_from_quote(client.quote.ltp({"BSE_EQ": bse_body})))
        quoted = 0
        for index_id, (names, seg) in INDEX_MEMBERS.items():
            pool = nse_ids if seg == "NSE_EQ" else bse_ids
            for name in names:
                hit = pool.get(name) or nse_ids.get(name) or bse_ids.get(name)
                ltp = None
                ok = False
                security_id = None
                segment = seg
                if hit:
                    security_id, segment = hit
                    sid_key = str(int(security_id)) if str(security_id).isdigit() else str(security_id)
                    ltp = quote_map.get((segment, sid_key))
                    if ltp is None:
                        for s in ("NSE_EQ", "BSE_EQ"):
                            ltp = quote_map.get((s, sid_key))
                            if ltp is not None:
                                segment = s
                                break
                    ok = ltp is not None
                    if ok:
                        quoted += 1
                wh.append_constituent_row(
                    {
                        "as_of": as_of,
                        "index_id": index_id,
                        "symbol": name,
                        "security_id": security_id,
                        "segment": segment,
                        "weight_pct": None,
                        "weight_layer": "DATA_INSUFFICIENT",
                        "ltp": ltp,
                        "quote_ok": ok,
                    }
                )
        report["constituents"]["quoted"] = quoted

        for i, und in enumerate(UNDERLYINGS):
            if i:
                time.sleep(sleep_s)
            body = {"UnderlyingScrip": SCRIPS[und], "UnderlyingSeg": "IDX_I"}
            exp_raw = client.option_chain.expiry_list(body)
            data = exp_raw.get("data") if isinstance(exp_raw, dict) else None
            expiry = None
            if isinstance(data, list) and data:
                expiry = str(data[0])
            if not expiry:
                report["gaps"].append(f"{und}: no expiry")
                continue
            raw = client.option_chain.chain({**body, "Expiry": expiry})
            payload = unwrap_chain_payload(raw) if isinstance(raw, dict) else {}
            spot = None
            try:
                spot = float(payload.get("last_price")) if payload.get("last_price") not in (None, "") else None
            except (TypeError, ValueError):
                spot = None
            strikes = parse_oc(payload.get("oc"))
            snap = ChainSnap(
                underlying=und,
                expiry=expiry,
                spot=spot,
                as_of_ist=as_of,
                mode="full_chain_3m",
                dry_run=False,
                strikes=strikes,
                source="dhan_option_chain",
                note="desk-book DATA-002",
            )

            class _Wing:
                atm_wing = 2

            bias = compute_chain_bias(snap, _Wing())  # type: ignore[arg-type]
            compact = {
                "underlying": und,
                "expiry": expiry,
                "spot": spot,
                "strike_count": len(strikes),
                "pcr_oi": bias.pcr_oi,
                "atm_strike": bias.atm_strike,
                "full_strikes_stored": True,
            }
            snap_id = wh.insert_chain_snapshot_row(
                underlying=und,
                expiry=expiry,
                atm=None if bias.atm_strike is None else str(bias.atm_strike),
                pcr=bias.pcr_oi,
                payload=compact,
                ts=as_of,
            )
            n_strikes = wh.append_strike_rows(snap_id, _strike_dicts(und, expiry, as_of, strikes))
            idx = atm_index(strikes, spot)
            atm = strikes[idx] if idx is not None else None
            for level in _levels(snap_id, und, expiry, as_of, atm):
                wh.append_option_level(level)
            report["chains"].append(
                {
                    "underlying": und,
                    "expiry": expiry,
                    "spot": spot,
                    "strikes": n_strikes,
                    "pcr_oi": bias.pcr_oi,
                    "atm": bias.atm_strike,
                    "snapshot_id": snap_id,
                }
            )
    finally:
        client.close()

    report["ok"] = bool(report["chains"])
    report["status"] = wh.status()
    return report

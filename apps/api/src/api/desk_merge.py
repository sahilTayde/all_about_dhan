"""Merge LIVE PAPER underlyings (premium-bound) onto the mock desk document."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[4]
_LATEST_SIGNALS = _REPO_ROOT / "data" / "recon" / "paper_latest_signals.json"
_MONITOR_STATUS = _REPO_ROOT / "data" / "recon" / "paper_ops_monitor_status.json"


def _di_or_num(value: Any) -> Any:
    if value is None or value == "":
        return "DATA_INSUFFICIENT"
    return value


def _reason_list(*sources: Any, limit: int = 3) -> list[str]:
    """Dedupe customer-facing veto/hold strings (no indicator soup)."""
    out: list[str] = []
    for src in sources:
        if not src:
            continue
        if isinstance(src, str):
            items = [src]
        elif isinstance(src, (list, tuple)):
            items = list(src)
        else:
            continue
        for raw in items:
            text = str(raw or "").strip()
            if not text or text in out:
                continue
            if text.startswith(
                ("boss:", "tech:", "chain:", "bull:", "bear:", "trader:", "input_mix:", "phd_note:")
            ):
                continue
            out.append(text)
            if len(out) >= limit:
                return out[:limit]
    return out[:limit]


def _load_latest_vetoes() -> dict[str, list[str]]:
    """Small recon snapshot — avoid scanning 47MB paper_ledger on each GET."""
    for path in (_LATEST_SIGNALS, _MONITOR_STATUS):
        if not path.is_file():
            continue
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(blob, dict):
            continue
        by_und = blob.get("top_veto_reasons") or blob.get("vetoes_by_underlying")
        if isinstance(by_und, dict) and by_und:
            return {
                str(k).upper(): _reason_list(v, limit=3)
                for k, v in by_und.items()
                if v
            }
        leans = blob.get("leans") or {}
        if isinstance(leans, dict) and isinstance(leans.get("top_veto_reasons"), dict):
            return {
                str(k).upper(): _reason_list(v, limit=3)
                for k, v in leans["top_veto_reasons"].items()
                if v
            }
    return {}


def _apply_meta_veto_banner(out: dict[str, Any]) -> None:
    """Ensure meta.veto_banner / meta.top_veto_reasons for WAITING UI."""
    meta = dict(out.get("meta") or {})
    signals = out.get("signals") or {}
    aggregated: list[str] = []
    for row in signals.values():
        if not isinstance(row, dict):
            continue
        for r in _reason_list(
            row.get("top_veto_reasons"),
            row.get("vetoes"),
            row.get("reasons"),
            limit=3,
        ):
            if r not in aggregated:
                aggregated.append(r)
            if len(aggregated) >= 3:
                break
        if len(aggregated) >= 3:
            break
    if not aggregated:
        latest = _load_latest_vetoes()
        for reasons in latest.values():
            for r in reasons:
                if r not in aggregated:
                    aggregated.append(r)
                if len(aggregated) >= 3:
                    break
            if len(aggregated) >= 3:
                break
    if aggregated:
        meta["veto_banner"] = aggregated[:3]
        meta["top_veto_reasons"] = aggregated[:3]
    out["meta"] = meta


def merge_live_paper_into_desk(
    desk: dict[str, Any],
    live: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Overlay /ws/signals paper snapshot onto GET /paper/signal shape.

    LIVE PAPER entry/stop/target win when present. Index proxy never fills
    premium slots. Orders stay refused. Always completes top_veto_reasons /
    meta.veto_banner when HOLD reasons exist (live row, reasons, or recon snapshot).
    """
    out = deepcopy(desk)
    meta = dict(out.get("meta") or {})
    if not live or not isinstance(live, dict):
        meta.setdefault("paper_live", False)
        meta.setdefault(
            "premium_path",
            "MOCK desk. Connect /ws/signals?live=1 for Dhan paper premiums.",
        )
        out["meta"] = meta
        # Overlay latest ledger vetoes onto HOLD rows when WS is down.
        latest = _load_latest_vetoes()
        if latest:
            signals = dict(out.get("signals") or {})
            for name, reasons in latest.items():
                row = dict(signals.get(name) or {})
                if not row:
                    continue
                side = str(row.get("side") or "").upper()
                if side in ("HOLD", "WAITING", "") and reasons:
                    if not row.get("top_veto_reasons"):
                        row["top_veto_reasons"] = reasons[:3]
                    signals[name] = row
            out["signals"] = signals
        _apply_meta_veto_banner(out)
        return out

    under = live.get("underlyings") or {}
    if not under:
        meta["paper_live"] = True
        meta["source"] = "paper_live_empty"
        meta["premium_path"] = live.get("note") or (
            "LIVE PAPER connected but no underlyings yet — waiting for ticks."
        )
        meta["asOf"] = live.get("as_of_ist") or meta.get("asOf")
        out["meta"] = meta
        out["live_paper"] = {
            "kind": live.get("kind"),
            "orders": live.get("orders", "refused"),
            "as_of_ist": live.get("as_of_ist"),
        }
        _apply_meta_veto_banner(out)
        return out

    signals = dict(out.get("signals") or {})
    for name, live_row in under.items():
        if not isinstance(live_row, dict):
            continue
        base = dict(signals.get(name) or {})
        ticket = live_row.get("ticket") or {}
        base["side"] = live_row.get("side") or base.get("side") or "HOLD"
        if live_row.get("strike") not in (None, ""):
            base["strike"] = live_row.get("strike")
        elif ticket.get("strike") not in (None, ""):
            base["strike"] = ticket.get("strike")
        base["entry"] = _di_or_num(live_row.get("entry") if live_row.get("entry") not in (None, "") else ticket.get("entry"))
        base["stop"] = _di_or_num(live_row.get("stop") if live_row.get("stop") not in (None, "") else ticket.get("stop"))
        base["target"] = _di_or_num(live_row.get("target") if live_row.get("target") not in (None, "") else ticket.get("target"))
        spot = (
            live_row.get("underlying_spot")
            if live_row.get("underlying_spot") is not None
            else live_row.get("spot")
            if live_row.get("spot") is not None
            else ticket.get("underlying_spot")
        )
        if spot is not None:
            base["underlying_spot"] = spot
            base["spot"] = spot
        if live_row.get("expiry"):
            base["expiry"] = live_row.get("expiry")
        base["ticket"] = ticket or {
            "unit": "OPTION_PREMIUM",
            "levels_ready": False,
            "levels_note": (
                "LIVE PAPER lean without bound option premium — DATA_INSUFFICIENT. "
                "Refusing index-as-premium."
            ),
        }
        if live_row.get("confidence"):
            base["confidence"] = live_row["confidence"]
        base["staged"] = {
            **(base.get("staged") or {}),
            "state": live_row.get("state") or (base.get("staged") or {}).get("state"),
            "headline": live_row.get("headline") or "",
            "note": live_row.get("note") or "",
            "lean": live_row.get("lean"),
        }
        base["customer"] = {
            "headline": live_row.get("headline") or "",
            "note": live_row.get("note") or "",
        }
        banner = _reason_list(
            live_row.get("top_veto_reasons"),
            live_row.get("vetoes"),
            live_row.get("reasons"),
            ticket.get("top_veto_reasons") if isinstance(ticket, dict) else None,
            limit=3,
        )
        if banner:
            base["top_veto_reasons"] = banner
        if live_row.get("vetoes"):
            base["vetoes"] = list(live_row["vetoes"])
        if live_row.get("reasons"):
            base["reasons"] = list(live_row["reasons"])[:8]
        if live_row.get("premium_quote"):
            base["premium_quote"] = live_row["premium_quote"]
        base["id"] = base.get("id") or f"paper-{name.lower()}"
        base["underlying"] = name
        signals[name] = base

    meta["source"] = "paper_live"
    meta["placeholder"] = False
    meta["paper_live"] = True
    meta["label"] = "LIVE PAPER"
    meta["asOf"] = live.get("as_of_ist") or meta.get("asOf")
    meta["note"] = (
        "LIVE PAPER overlay. Entry/SL/Target = option premium when LTP bound; "
        "else DATA_INSUFFICIENT with gap reason. Orders refused. Not advice."
    )
    meta["premium_path"] = (
        "PaperSignalEngine + POST /optionchain ATM LTP → MIX-SLTP-PREM-PCT bind"
    )
    out["meta"] = meta
    out["signals"] = signals
    out["live_paper"] = {
        "kind": live.get("kind"),
        "orders": live.get("orders", "refused"),
        "as_of_ist": live.get("as_of_ist"),
        "customer_default_mix": live.get("customer_default_mix"),
        "paper_watch_mixes": live.get("paper_watch_mixes"),
    }
    _apply_meta_veto_banner(out)
    return out

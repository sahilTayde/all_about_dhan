"""Paper staged signals from Dhan live-market-feed ticks. No orders.

Runs MIX-DEFAULT-BUY (customer ticket path). MIX-CLUB-GR stays KEEP_ALL but
PARKED on the working ticket. Chart Fanatics / Okala paper notify removed
(founder DhanHQ-only reset 2026-09-09).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from backtest_engine.algos import and_many, daily_lean_at_open, mixed_index_veto, strat_003_leans
from backtest_engine.clocks import (
    allow_007,
    flatten_009,
    in_founder_dead_band,
    session_date_ist,
    skip_open_009,
)
from backtest_engine.indicators import Bar
from backtest_engine.option_premium_ltp import fetch_atm_option_premium_ltp
from backtest_engine.patterns import lean_gap, lean_range_exp
from backtest_engine.resample import resample
from backtest_engine.ticket_confidence import (
    confidence_from_books,
    customer_ticket_levels,
)
from dhan_client.config import repo_root

IST = timezone(timedelta(hours=5, minutes=30))

YAML_INDEX = {
    13: "NIFTY",
    25: "BANKNIFTY",
    51: "SENSEX",
}

MIX_DEFAULT = "MIX-DEFAULT-BUY"
MIX_CLUB_GR = "MIX-CLUB-GR"


def news_veto_enabled() -> bool:
    return os.environ.get("NEWS_VETO_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _customer(side: str, state: str) -> dict[str, str]:
    if state == "VETOED":
        return {
            "side": "HOLD",
            "headline": "HOLD — indexes disagree or the clock is closed.",
            "note": "Not a fill. Paper lean only.",
        }
    if side == "CE" and state in ("EARLY", "CONFIRMED"):
        verb = "BUY CALL"
        wait = " Not confirmed yet." if state == "EARLY" else " Still not a fill promise."
        return {
            "side": "BUY_CE",
            "headline": f"{verb} — paper lean.{wait}",
            "note": "Education desk. Do not treat as an order.",
        }
    if side == "PE" and state in ("EARLY", "CONFIRMED"):
        verb = "BUY PUT"
        wait = " Not confirmed yet." if state == "EARLY" else " Still not a fill promise."
        return {
            "side": "BUY_PE",
            "headline": f"{verb} — paper lean.{wait}",
            "note": "Education desk. Do not treat as an order.",
        }
    return {
        "side": "HOLD",
        "headline": "HOLD — mixing. Not a signal.",
        "note": "WATCH. No CE/PE ticket.",
    }


def _read_session_kind_hint() -> tuple[Optional[str], list[str]]:
    path = repo_root() / "data" / "recon" / "paper_ops_monitor_status.json"
    if not path.is_file():
        return None, []
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, []
    if not isinstance(blob, dict):
        return None, []
    kind = blob.get("session_kind") or (blob.get("clock") or {}).get("session_kind")
    reasons: list[str] = []
    for key in ("top_veto_reasons", "vetoes", "reasons"):
        raw = blob.get(key)
        if isinstance(raw, list):
            reasons.extend(str(x) for x in raw)
        elif isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, list):
                    reasons.extend(str(x) for x in v)
                elif v:
                    reasons.append(str(v))
    return (str(kind) if kind else None), reasons


class MinuteBars:
    def __init__(self) -> None:
        self.current: Optional[Bar] = None
        self.closed: list[Bar] = []

    def on_ltp(self, ts: int, ltp: float, volume: float = 0.0) -> None:
        minute = (int(ts) // 60) * 60
        cur = self.current
        if cur is None or cur.ts != minute:
            if cur is not None:
                self.closed.append(cur)
                if len(self.closed) > 800:
                    self.closed = self.closed[-800:]
            self.current = Bar(ts=minute, open=ltp, high=ltp, low=ltp, close=ltp, volume=volume)
            return
        self.current = Bar(
            ts=cur.ts,
            open=cur.open,
            high=max(cur.high, ltp),
            low=min(cur.low, ltp),
            close=ltp,
            volume=cur.volume + volume,
        )

    def bars(self) -> list[Bar]:
        rows = list(self.closed)
        if self.current is not None:
            rows.append(self.current)
        return rows


def club_gr_leans(bars_3m: list[Bar]) -> list[str]:
    if not bars_3m:
        return []
    return and_many([lean_gap(bars_3m), lean_range_exp(bars_3m)])


class PaperSignalEngine:
    """Default ticket + Club-GR park. Orders refused. No MIX-CF notify."""

    def __init__(self, *, big_news_hold: Optional[bool] = None) -> None:
        self.books = {name: MinuteBars() for name in YAML_INDEX.values()}
        self.last: dict[str, Any] = {}
        self._last_club_lean: dict[str, str] = {}
        self.big_news_hold = big_news_hold

    def set_big_news_hold(self, hold: bool) -> None:
        self.big_news_hold = hold

    def ingest(self, packet: dict[str, Any]) -> Optional[dict[str, Any]]:
        fields = packet.get("fields") or {}
        ltp = fields.get("ltp")
        if ltp is None:
            return None
        sid = int(packet.get("security_id") or 0)
        name = YAML_INDEX.get(sid)
        if name is None:
            return None
        ts = int(fields.get("last_trade_time_epoch") or time.time())
        vol = float(fields.get("volume") or 0.0)
        self.books[name].on_ltp(ts, float(ltp), vol)
        return self.snapshot()

    def _book_row(
        self,
        *,
        name: str,
        lean: str,
        spot: Optional[float],
        state: str,
        algo: str,
        paper_watch: bool,
        mix_id: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        copy = _customer(lean if lean in ("CE", "PE") else "SKIP", state)
        row: dict[str, Any] = {
            "state": state,
            "lean": lean,
            "spot": spot,
            **copy,
            "not_a_fill": True,
            "algo": algo,
            "paper_watch": paper_watch,
            "customer_default": not paper_watch,
        }
        if mix_id:
            row["mix_id"] = mix_id
        if extra:
            row.update(extra)
        return row

    def snapshot(self) -> dict[str, Any]:
        daily: dict[str, dict[str, str]] = {}
        default_leans: dict[str, str] = {}
        club_leans: dict[str, str] = {}
        spots: dict[str, float] = {}
        for name, book in self.books.items():
            bars_1m = book.bars()
            if bars_1m:
                spots[name] = bars_1m[-1].close
            bars_3m = resample(bars_1m, 3)
            d_leans = strat_003_leans(bars_3m, equal_weight_vwap=True) if bars_3m else []
            c_leans = club_gr_leans(bars_3m) if bars_3m else []
            if d_leans:
                default_leans[name] = d_leans[-1]
                daily[name] = daily_lean_at_open(bars_3m, d_leans)
            else:
                default_leans[name] = "SKIP"
                daily[name] = {}
            club_leans[name] = c_leans[-1] if c_leans else "SKIP"
        veto = mixed_index_veto(daily)
        now_ts = int(time.time())
        today = session_date_ist(now_ts)
        default_book: dict[str, Any] = {}
        club_book: dict[str, Any] = {}
        _read_session_kind_hint()

        for name, lean in default_leans.items():
            state = "WATCH"
            use = lean
            if flatten_009(now_ts) or skip_open_009(now_ts) or not allow_007(now_ts):
                state = "VETOED"
                use = "SKIP"
            elif today in veto:
                state = "VETOED"
                use = "SKIP"
            elif use in ("CE", "PE"):
                state = "CONFIRMED"
            default_book[name] = self._book_row(
                name=name,
                lean=use,
                spot=spots.get(name),
                state=state,
                algo=f"{MIX_DEFAULT} paper",
                paper_watch=False,
                mix_id=MIX_DEFAULT,
            )

        for name, lean in club_leans.items():
            state = "WATCH"
            use = lean
            if in_founder_dead_band(now_ts):
                state = "VETOED"
                use = "SKIP"
            elif use in ("CE", "PE"):
                state = "CONFIRMED"
            club_book[name] = self._book_row(
                name=name,
                lean=use,
                spot=spots.get(name),
                state=state,
                algo=f"{MIX_CLUB_GR} PARKED working_path",
                paper_watch=False,
                mix_id=MIX_CLUB_GR,
                extra={
                    "working_path": "PARKED",
                    "keep_all": True,
                    "customer_default": False,
                    "note": (
                        "PARKED from customer scoring. After-cost FAIL; "
                        "SCORE_SAMPLE empty so not a MIX kill. KEEP_ALL."
                    ),
                },
            )

        underlyings = dict(default_book)

        for name, row in underlyings.items():
            lean = row.get("lean")
            state = str(row.get("state") or "WATCH")
            bars_3m = resample(self.books[name].bars(), 3) if name in self.books else []
            spot_val = spots.get(name)
            premium_meta: dict[str, Any] = {}
            option_ltp = None
            if lean in ("CE", "PE") and state in ("CONFIRMED", "IN-PROGRESS"):
                quote = fetch_atm_option_premium_ltp(
                    name,
                    lean,
                    prefer_live=True,
                    spot_hint=spot_val,
                )
                premium_meta = {
                    "reason": quote.reason,
                    "source": quote.source,
                    "expiry": quote.expiry,
                    "strike": quote.strike,
                    "underlying_spot": quote.underlying_spot or spot_val,
                    "ok": quote.ok,
                    "data_gaps": list(quote.data_gaps),
                }
                if quote.ok and quote.ltp is not None:
                    option_ltp = quote.ltp
                row["premium_quote"] = quote.to_dict()
            levels = customer_ticket_levels(
                underlying=name,
                lean=lean if lean in ("CE", "PE") else "SKIP",
                spot=spot_val,
                state=state,
                method_id="MIX-DEFAULT-BUY",
                bars=bars_3m,
                option_ltp=option_ltp,
                premium_meta=premium_meta or None,
                paper_starter_premium_stop=False,
            )
            conf = confidence_from_books(
                underlying=name,
                default_row=default_book.get(name) or row,
                club_row=None,
                okala_row=None,
            )
            row["underlying_spot"] = (
                levels.get("underlying_spot")
                if levels.get("underlying_spot") is not None
                else spot_val
            )
            if state == "CONFIRMED" and lean in ("CE", "PE"):
                row["strike"] = levels.get("strike") or ""
                row["entry"] = levels.get("entry") if levels.get("entry") is not None else ""
                row["stop"] = levels.get("stop") if levels.get("stop") is not None else ""
                row["target"] = levels.get("target") if levels.get("target") is not None else ""
                if levels.get("expiry"):
                    row["expiry"] = levels.get("expiry")
                row["side"] = "BUY_CE" if lean == "CE" else "BUY_PE"
                row["headline"] = (
                    f"{'BUY CALL' if lean == 'CE' else 'BUY PUT'} — paper ticket. "
                    "You decide. Not a fill."
                )
                row["note"] = levels.get("levels_note") or (
                    "DATA_INSUFFICIENT: option premium unbound. Orders refused."
                )
            elif state == "EARLY":
                row["strike"] = ""
                row["entry"] = ""
                row["stop"] = ""
                row["target"] = ""
            row["ticket"] = levels
            row["confidence"] = conf
            if name in club_book:
                club_book[name]["ticket"] = levels
                club_book[name]["confidence"] = conf
                club_book[name]["underlying_spot"] = row.get("underlying_spot")

        payload = {
            "kind": "paper_signal",
            "orders": "refused",
            "as_of_ist": datetime.now(IST).isoformat(),
            "research_ready_for_programming": False,
            "customer_default_mix": MIX_DEFAULT,
            "paper_watch_mixes": [],
            "underlyings": underlyings,
            "books": {
                MIX_DEFAULT: default_book,
                MIX_CLUB_GR: club_book,
            },
            "note": (
                "Default ticket = MIX-DEFAULT-BUY. MIX-CLUB-GR PARKED (KEEP_ALL). "
                "Chart Fanatics / Okala paper notify removed. "
                f"NEWS_VETO_ENABLED={str(news_veto_enabled()).lower()}. "
                "Confidence is not a win rate. Orders refused. NO_PROMOTE."
            ),
            "news_veto_enabled": news_veto_enabled(),
        }
        self.last = payload
        return payload

"""Paper staged signals from Dhan live-market-feed ticks. No orders. No indicator soup on customer copy.

Runs MIX-DEFAULT-BUY (customer ticket path) and MIX-CF-* FOUNDER_PAPER_ACCEPT
starters (Okala + structure overnight registry) side by side.
MIX-CLUB-GR stays KEEP_ALL catalog / BACKTEST_BOOK but is PARKED on the working
ticket (after-cost FAIL; SCORE_SAMPLE empty → not a MIX kill).
"""

from __future__ import annotations

import json
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
from backtest_engine.okala_in_paper import (
    FOUNDER_LABEL,
    OKALA_UNDERLYINGS,
    PAPER_STARTER_STOP_PCT,
    PAPER_STARTER_TARGET_PCT,
    best_okala_paper_hit,
    news_veto_enabled,
)
from backtest_engine.option_premium_ltp import fetch_atm_option_premium_ltp
from backtest_engine.paper_watch import append_paper_event
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
OKALA_MIXES = (
    "MIX-CF-OKALA-IN-LEVEL",
    "MIX-CF-OKALA-IN-FORK",
    "MIX-CF-OKALA-IN-H-CROSS",
    "MIX-CF-OKALA-IN-REPAIR",
)


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
    """Soft read recon monitor for BIG_NEWS / NEWS_DAY — never invent news."""
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
    """Frozen MIX-CLUB-GR: GAP ∧ range-expansion. Same as club backtest."""
    if not bars_3m:
        return []
    return and_many([lean_gap(bars_3m), lean_range_exp(bars_3m)])


class PaperSignalEngine:
    """Default ticket + Club-GR + Okala-IN paper watch. Orders refused."""

    def __init__(self, *, big_news_hold: Optional[bool] = None) -> None:
        self.books = {name: MinuteBars() for name in YAML_INDEX.values()}
        self.last: dict[str, Any] = {}
        self._last_club_lean: dict[str, str] = {}
        self._last_okala_lean: dict[str, str] = {}
        self._last_cf_lean: dict[str, str] = {}
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
        okala_book: dict[str, Any] = {}
        okala_by_mix: dict[str, dict[str, Any]] = {m: {} for m in OKALA_MIXES}

        session_kind, recon_vetoes = _read_session_kind_hint()
        big_news = self.big_news_hold
        if big_news is None:
            # Soft-default: NEWS_VETO_ENABLED=false → never HOLD from news tags.
            from backtest_engine.okala_in_paper import big_news_blocks_okala

            big_news = big_news_blocks_okala(
                session_kind=session_kind,
                veto_reasons=recon_vetoes,
            )
        elif big_news and not news_veto_enabled() and self.big_news_hold is not True:
            # Constructor default None already handled; explicit False stays False.
            big_news = False

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
            row = self._book_row(
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
                    "recorded_optimistic_wr": "0.694_n36_WEAK_not_promote",
                    "recorded_after_cost_wr": "0.444_n36_FAIL_as_promote",
                    "note": (
                        "PARKED from customer scoring. After-cost FAIL; "
                        "SCORE_SAMPLE empty so not a MIX kill. KEEP_ALL."
                    ),
                },
            )
            club_book[name] = row
            # Do not append_paper_event — working-path park (KEEP_ALL row remains).

        # Okala India FOUNDER_PAPER_ACCEPT — NIFTY / BANKNIFTY / SENSEX.
        for name in YAML_INDEX.values():
            if name not in OKALA_UNDERLYINGS:
                continue
            bars_1m = self.books[name].bars() if name in self.books else []
            hit = best_okala_paper_hit(
                name,
                bars_1m,
                big_news_hold=bool(big_news),
                session_kind=session_kind if news_veto_enabled() else "NORMAL",
                veto_reasons=recon_vetoes if news_veto_enabled() else [],
            )
            if hit is None:
                row = self._book_row(
                    name=name,
                    lean="SKIP",
                    spot=spots.get(name),
                    state="WATCH" if not big_news else "VETOED",
                    algo=f"MIX-CF-OKALA-IN-* {FOUNDER_LABEL}",
                    paper_watch=True,
                    mix_id="MIX-CF-OKALA-IN-H-CROSS",
                    extra={
                        "founder_label": FOUNDER_LABEL,
                        "NO_PROMOTE": True,
                        "paper_enable": True,
                        "win_rate_claim": None,
                        "news_veto_enabled": news_veto_enabled(),
                        "note_extra": (
                            "BIG_NEWS hold — Okala paper ticket paused."
                            if big_news
                            else "No Okala pattern on this tick."
                        ),
                    },
                )
                if big_news:
                    row["top_veto_reasons"] = [
                        "BIG_NEWS: hold customer ticket — Okala PAPER notify suppressed"
                    ]
                okala_book[name] = row
                continue

            state = "CONFIRMED"
            use = hit.lean
            if in_founder_dead_band(now_ts):
                state = "VETOED"
                use = "SKIP"
            row = self._book_row(
                name=name,
                lean=use,
                spot=spots.get(name),
                state=state,
                algo=f"{hit.mix_id} {FOUNDER_LABEL}",
                paper_watch=True,
                mix_id=hit.mix_id,
                extra={
                    "founder_label": FOUNDER_LABEL,
                    "NO_PROMOTE": True,
                    "paper_enable": True,
                    "win_rate_claim": None,
                    "eligibility": hit.eligibility,
                    "okala_cell": hit.cell,
                    "okala_setup": hit.setup,
                    "okala_regime": hit.regime,
                    "okala_tf_min": hit.tf_min,
                    "okala_magnet_pair": list(hit.magnet_pair),
                    "research_wr_robust": (
                        hit.wr_robust if hit.eligibility == "FOUNDER_PAPER_ACCEPT_CELL" else None
                    ),
                    "research_n": hit.n if hit.eligibility == "FOUNDER_PAPER_ACCEPT_CELL" else None,
                    "reasons": hit.reasons,
                    "news_veto_enabled": news_veto_enabled(),
                },
            )
            if use in ("CE", "PE"):
                verb = "BUY CALL" if use == "CE" else "BUY PUT"
                caution = (
                    " Extended starter (BN/SENSEX)."
                    if hit.eligibility == "FOUNDER_STARTER_EXTEND"
                    else ""
                )
                row["headline"] = (
                    f"{verb} — Okala India paper starter ({FOUNDER_LABEL})."
                    f"{caution} Not a fill. Not live."
                )
                row["note"] = (
                    f"{hit.mix_id} · {hit.setup} · {hit.regime} · {hit.tf_min}m. "
                    "Confidence ≠ win rate. Optimize later. NO_PROMOTE."
                )
                row["side"] = "BUY_CE" if use == "CE" else "BUY_PE"
            okala_book[name] = row
            okala_by_mix[hit.mix_id][name] = row
            prev = self._last_okala_lean.get(name)
            sig_key = f"{hit.mix_id}:{use}"
            if sig_key != prev and use in ("CE", "PE", "SKIP"):
                append_paper_event(
                    hit.mix_id,
                    {
                        "underlying": name,
                        "lean": use,
                        "prev_lean": prev,
                        "state": state,
                        "spot": spots.get(name),
                        "founder_label": FOUNDER_LABEL,
                        "eligibility": hit.eligibility,
                        "cell": hit.cell,
                        "setup": hit.setup,
                        "regime": hit.regime,
                        "tf_min": hit.tf_min,
                        "magnet_pair": list(hit.magnet_pair),
                        "research_wr_robust": hit.wr_robust,
                        "research_n": hit.n,
                        "NO_PROMOTE": True,
                        "note": (
                            "PAPER notify only. VALIDATION cell WR is research-only. "
                            "Orders refused. NO_PROMOTE live."
                        ),
                        "attention": (
                            f"Okala paper signal {name} {use} via {hit.mix_id}"
                            if use in ("CE", "PE")
                            else None
                        ),
                    },
                )
                self._last_okala_lean[name] = sig_key

        # Structure CF overnight FOUNDER_PAPER_ACCEPT (plugin registry sibling).
        structure_book: dict[str, Any] = {}
        try:
            from backtest_engine.cf_structure_paper import detect_structure_paper_signals
        except ImportError:
            detect_structure_paper_signals = None  # type: ignore[assignment]
        if detect_structure_paper_signals is not None:
            for name in YAML_INDEX.values():
                bars_1m = self.books[name].bars() if name in self.books else []
                hits = detect_structure_paper_signals(
                    name,
                    bars_1m,
                    big_news_hold=bool(big_news),
                    session_kind=session_kind if news_veto_enabled() else "NORMAL",
                    veto_reasons=recon_vetoes if news_veto_enabled() else [],
                )
                if not hits:
                    structure_book[name] = self._book_row(
                        name=name,
                        lean="SKIP",
                        spot=spots.get(name),
                        state="WATCH",
                        algo=f"MIX-CF-structure {FOUNDER_LABEL}",
                        paper_watch=True,
                        mix_id="MIX-CF-STRUCTURE",
                        extra={
                            "founder_label": FOUNDER_LABEL,
                            "NO_PROMOTE": True,
                            "plugin_id": "cf_structure_in",
                        },
                    )
                    continue
                hit = hits[0]
                use = hit.lean
                state = "CONFIRMED"
                if in_founder_dead_band(now_ts):
                    state = "VETOED"
                    use = "SKIP"
                row = self._book_row(
                    name=name,
                    lean=use,
                    spot=spots.get(name),
                    state=state,
                    algo=f"{hit.mix_id} {FOUNDER_LABEL}",
                    paper_watch=True,
                    mix_id=hit.mix_id,
                    extra={
                        "founder_label": FOUNDER_LABEL,
                        "NO_PROMOTE": True,
                        "paper_enable": True,
                        "eligibility": hit.eligibility,
                        "cf_setup": hit.setup,
                        "cf_family": hit.family,
                        "cf_cell": hit.cell,
                        "research_wr_robust": (
                            hit.wr_robust
                            if hit.eligibility == "FOUNDER_PAPER_ACCEPT_CELL"
                            else None
                        ),
                        "plugin_id": "cf_structure_in",
                        "reasons": hit.reasons,
                    },
                )
                if use in ("CE", "PE"):
                    verb = "BUY CALL" if use == "CE" else "BUY PUT"
                    row["headline"] = (
                        f"{verb} — CF structure paper starter ({FOUNDER_LABEL}). "
                        "Not a fill. Not live."
                    )
                    row["side"] = "BUY_CE" if use == "CE" else "BUY_PE"
                structure_book[name] = row
                prev = self._last_cf_lean.get(name)
                sig_key = f"{hit.mix_id}:{use}"
                if sig_key != prev and use in ("CE", "PE", "SKIP"):
                    append_paper_event(
                        hit.mix_id,
                        {
                            "underlying": name,
                            "lean": use,
                            "prev_lean": prev,
                            "state": state,
                            "spot": spots.get(name),
                            "founder_label": FOUNDER_LABEL,
                            "family": hit.family,
                            "NO_PROMOTE": True,
                            "plugin_id": "cf_structure_in",
                            "note": "PAPER notify only. Orders refused.",
                        },
                    )
                    self._last_cf_lean[name] = sig_key

        # Prefer CF PAPER CE/PE (Okala then structure) when default is quiet.
        underlyings: dict[str, Any] = {}
        for name, drow in default_book.items():
            o_row = okala_book.get(name)
            s_row = structure_book.get(name)
            if (
                drow.get("lean") not in ("CE", "PE")
                and o_row
                and o_row.get("lean") in ("CE", "PE")
                and o_row.get("state") == "CONFIRMED"
            ):
                notify = dict(o_row)
                notify["customer_default"] = False
                notify["paper_watch"] = True
                notify["notify_source"] = "MIX-CF-OKALA-IN"
                underlyings[name] = notify
            elif (
                drow.get("lean") not in ("CE", "PE")
                and s_row
                and s_row.get("lean") in ("CE", "PE")
                and s_row.get("state") == "CONFIRMED"
            ):
                notify = dict(s_row)
                notify["customer_default"] = False
                notify["paper_watch"] = True
                notify["notify_source"] = "MIX-CF-STRUCTURE"
                underlyings[name] = notify
            else:
                underlyings[name] = drow

        # Attach paper ticket + confidence for customer desk (you decide; no orders).
        for name, row in underlyings.items():
            lean = row.get("lean")
            state = str(row.get("state") or "WATCH")
            bars_3m = resample(self.books[name].bars(), 3) if name in self.books else []
            spot_val = spots.get(name)
            premium_meta: dict[str, Any] = {}
            option_ltp = None
            okala_notify = row.get("notify_source") in (
                "MIX-CF-OKALA-IN",
                "MIX-CF-STRUCTURE",
            )
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
                if okala_notify:
                    premium_meta["paper_starter_premium_stop"] = True
                    premium_meta["stop_pct"] = PAPER_STARTER_STOP_PCT
                    premium_meta["target_pct"] = PAPER_STARTER_TARGET_PCT
            levels = customer_ticket_levels(
                underlying=name,
                lean=lean if lean in ("CE", "PE") else "SKIP",
                spot=spot_val,
                state=state,
                method_id="MIX-DESK-IQ-ATR-RR2",
                bars=bars_3m,
                option_ltp=option_ltp,
                premium_meta=premium_meta or None,
                paper_starter_premium_stop=okala_notify,
            )
            conf = confidence_from_books(
                underlying=name,
                default_row=default_book.get(name) or row,
                club_row=None,
                okala_row=okala_book.get(name),
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
                if row.get("notify_source") in ("MIX-CF-OKALA-IN", "MIX-CF-STRUCTURE"):
                    src = (
                        "Okala India"
                        if row.get("notify_source") == "MIX-CF-OKALA-IN"
                        else "CF structure"
                    )
                    row["headline"] = (
                        f"{'BUY CALL' if lean == 'CE' else 'BUY PUT'} — "
                        f"{src} paper starter ({FOUNDER_LABEL}). You decide. Not a fill."
                    )
                    row["note"] = levels.get("levels_note") or (
                        "DATA_INSUFFICIENT: option premium unbound. "
                        "Directional intent kept. Orders refused."
                    )
                else:
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
            if name in okala_book:
                okala_book[name]["ticket"] = levels
                okala_book[name]["confidence"] = conf
                okala_book[name]["underlying_spot"] = row.get("underlying_spot")

        paper_watch_mixes = [*OKALA_MIXES, "MIX-CF-STRUCTURE"]
        books_out: dict[str, Any] = {
            MIX_DEFAULT: default_book,
            MIX_CLUB_GR: club_book,
            "MIX-CF-OKALA-IN": okala_book,
            "MIX-CF-STRUCTURE": structure_book,
        }
        for mix_id, und_map in okala_by_mix.items():
            if und_map:
                books_out[mix_id] = und_map

        payload = {
            "kind": "paper_signal",
            "orders": "refused",
            "as_of_ist": datetime.now(IST).isoformat(),
            "research_ready_for_programming": False,
            "customer_default_mix": MIX_DEFAULT,
            "paper_watch_mixes": paper_watch_mixes,
            "founder_paper_accept": {
                "label": FOUNDER_LABEL,
                "family": "MIX-CF-OKALA-IN-* + MIX-CF-STRUCTURE overnight",
                "NO_PROMOTE": True,
                "optimize": "next_quarter",
                "plugin_registry": True,
            },
            "underlyings": underlyings,
            "books": books_out,
            "note": (
                "Default ticket = MIX-DEFAULT-BUY. "
                "MIX-CLUB-GR is PARKED on the working ticket (KEEP_ALL; not killed — "
                "SCORE_SAMPLE empty). MIX-CF-OKALA-IN-* + structure CF overnight are PAPER_WATCH. "
                f"Robust WR>50% cells = {FOUNDER_LABEL} via cf_paper_registry. "
                f"NEWS_VETO_ENABLED={str(news_veto_enabled()).lower()}. "
                "Confidence is agreement / data-quality, not a win rate. "
                "Customer decides. Orders refused. NO_PROMOTE live."
            ),
            "news_veto_enabled": news_veto_enabled(),
        }
        self.last = payload
        return payload

"""Evaluate one spec on one tape day: same kernel over TapeSource, causal fills."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from brokers.fills import Quote, fcmeas_half_spread
from contracts.clock import IST, SimClock
from contracts.envelope import Envelope
from contracts.ids import event_id
from events.bus import MemoryBus
from ledger.charges import load_rates, order_charges
from marketdata.sources import TapeSource
from runtime.kernel import Engine
from runtime.sources import EnvelopeSource
from runtime.store import InMemoryLedgerStore

from .bars import FwdBars, bar_state, deflated_sharpe
from .report import ForwardReport
from .spec import ForwardSpec, compute_lock_digest, plugin_source, verify_lock

TICK = 0.05
CHASE_TICKS = 2
LOT_SIZE = 65
SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)


class ForwardRefused(ValueError):
    """Harness refused the spec or the session."""


@dataclass(frozen=True)
class TapeQuote:
    available_ts: datetime
    instrument_id: str
    bid: float | None
    ask: float | None
    ltp: float | None
    bucket: str


def _parse_ts(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def load_tape_quotes(path: Path) -> list[TapeQuote]:
    """Read bid/ask/ltp from the same JSONL TapeSource consumes. Extra keys survive."""
    out: list[TapeQuote] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        row = obj["payload"] if isinstance(obj.get("payload"), dict) else obj
        inst = row.get("instrument_id")
        ts_raw = row.get("exchange_ts") or row.get("timestamp") or obj.get("event_ts")
        if not isinstance(inst, str) or not isinstance(ts_raw, str):
            continue
        out.append(
            TapeQuote(
                available_ts=_parse_ts(ts_raw),
                instrument_id=inst,
                bid=_opt_float(row.get("bid")),
                ask=_opt_float(row.get("ask")),
                ltp=_opt_float(row.get("ltp")),
                bucket=str(row.get("bucket") or "ATM"),
            )
        )
    return out


def _opt_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)  # type: ignore[arg-type]


def envelopes_from_tape(path: Path, clock: SimClock) -> list[Envelope]:
    """TapeSource → kernel envelopes (one code path with Engine)."""
    del clock
    source = TapeSource(path)
    out: list[Envelope] = []
    for index, event in enumerate(source.events()):
        if event.event_type != "TICK":
            continue
        tick = event.payload
        ts = event.available_ts.isoformat()
        payload: dict[str, Any] = {
            "instrument_id": getattr(tick, "instrument_id", ""),
            "ltp": getattr(tick, "ltp", None),
            "ltq": getattr(tick, "ltq", None),
            "volume": getattr(tick, "volume", None),
            "oi": getattr(tick, "oi", None),
            "exchange_ts": getattr(tick, "exchange_ts", ts),
        }
        out.append(
            Envelope(
                v=2,
                event_type="MARKET_TICK",
                event_id=event_id("forward", f"tape-{index}", 0),
                stream="md:tape",
                source="forward-eval",
                event_ts=str(payload["exchange_ts"]),
                available_ts=ts,
                timestamp=ts,
                account_id=None,
                correlation_id=None,
                causation_id=None,
                payload=payload,
            )
        )
    return out


def run_kernel(path: Path, start: datetime) -> tuple[int, str]:
    clock = SimClock(start)
    envs = envelopes_from_tape(path, clock)
    summary = Engine(
        EnvelopeSource(envs), SimClock(start), MemoryBus(), [], InMemoryLedgerStore()
    ).run()
    return summary.envelope_count, summary.output_hash


def last_quote(quotes: list[TapeQuote], instrument_id: str, asof: datetime) -> TapeQuote | None:
    visible = [q for q in quotes if q.instrument_id == instrument_id and q.available_ts <= asof]
    return visible[-1] if visible else None


def depth_coverage(quotes: list[TapeQuote], instruments: set[str], session: datetime) -> float:
    """Share of observed spec-strike minutes that carry bid+ask (95% gate)."""
    day = session.date()
    start = datetime.combine(day, SESSION_OPEN, tzinfo=IST)
    end = datetime.combine(day, SESSION_CLOSE, tzinfo=IST)
    by_minute: dict[int, bool] = {}
    for q in quotes:
        if q.instrument_id not in instruments:
            continue
        if not (start <= q.available_ts < end):
            continue
        minute = int((q.available_ts - start).total_seconds() // 60)
        has_depth = q.bid is not None and q.ask is not None
        by_minute[minute] = by_minute.get(minute, False) or has_depth
    if not by_minute:
        return 0.0
    return sum(1 for ok in by_minute.values() if ok) / len(by_minute)


def _qty(signal: dict[str, Any]) -> int:
    return int(signal.get("lots") or 1) * int(signal.get("lot_size") or LOT_SIZE)


def _charges(side: str, qty: int, price: float) -> float:
    rates = load_rates(by_exchange=True)
    return float(order_charges(side, qty, price, rates, exchange="NSE")["total"])


def _round_trip(entry: float, exit_px: float, qty: int) -> tuple[float, float]:
    gross = (exit_px - entry) * qty
    net = gross - _charges("BUY", qty, entry) - _charges("SELL", qty, exit_px)
    return gross, net


def _depth_entry(q: TapeQuote, mode: str) -> float | None:
    if q.ask is None:
        return None
    if mode == "CHASE":
        return round(q.ask + CHASE_TICKS * TICK, 2)
    if mode.startswith("LIMIT"):
        return q.ask
    return None


def _depth_exit(q: TapeQuote) -> float | None:
    return q.bid


def _fcmeas_pair(q_in: TapeQuote, q_out: TapeQuote) -> tuple[float, float] | None:
    if q_in.ltp is None or q_out.ltp is None:
        return None
    slip_in = fcmeas_half_spread(q_in.bucket, q_in.available_ts)
    slip_out = fcmeas_half_spread(q_out.bucket, q_out.available_ts)
    return q_in.ltp + slip_in, q_out.ltp - slip_out


def _price_leg(
    quotes: list[TapeQuote],
    instrument_id: str,
    entry_ts: datetime,
    exit_ts: datetime,
    qty: int,
    mode: str,
) -> dict[str, float] | None:
    q_in = last_quote(quotes, instrument_id, entry_ts)
    q_out = last_quote(quotes, instrument_id, exit_ts)
    if q_in is None or q_out is None:
        return None
    if mode == "WAIT":
        return {"gross_inr": 0.0, "net_depth_inr": 0.0, "net_fcmeas_inr": 0.0}
    entry = _depth_entry(q_in, mode)
    exit_px = _depth_exit(q_out)
    if entry is None or exit_px is None:
        return None
    gross, net_d = _round_trip(entry, exit_px, qty)
    fc = _fcmeas_pair(q_in, q_out)
    net_f = _round_trip(fc[0], fc[1], qty)[1] if fc else net_d
    return {"gross_inr": gross, "net_depth_inr": net_d, "net_fcmeas_inr": net_f}


def evaluate_session(
    spec: ForwardSpec,
    tape: Path,
    session: str,
    *,
    lock: dict[str, Any] | None = None,
    prior_nets: list[float] | None = None,
    prior_gross: float = 0.0,
) -> tuple[ForwardReport, list[dict[str, Any]]]:
    if lock is not None:
        digest = verify_lock(spec, lock)
    else:
        digest = compute_lock_digest(spec.raw, plugin_source(spec.plugin), spec.coefficients)
    quotes = load_tape_quotes(tape)
    start = datetime.combine(
        _parse_ts(session + "T09:15:00+05:30").date(), SESSION_OPEN, tzinfo=IST
    )
    env_count, env_hash = run_kernel(tape, start)
    instruments = {q.instrument_id for q in quotes}
    coverage = depth_coverage(quotes, instruments, start)
    bars = FwdBars.from_mapping(spec.bars)
    trades: list[dict[str, Any]] = []
    legs: dict[str, dict[str, float]] = {}
    session_net = 0.0
    session_gross = 0.0

    if coverage < 0.95:
        state = bar_state(
            n=len(prior_nets or []),
            gross=prior_gross,
            nets=list(prior_nets or []),
            bars=bars,
            depth_coverage=coverage,
        )
        n = len(prior_nets or [])
        report = _report(
            spec,
            digest,
            session,
            n,
            state,
            prior_nets or [],
            lock,
            coverage,
            {},
            env_count,
            env_hash,
            prior_gross,
        )
        return report, trades

    for sig in spec.signals:
        entry_ts = _parse_ts(str(sig["decision_ts"]))
        exit_own = _parse_ts(str(sig.get("exit_ts") or sig["decision_ts"]))
        if "exit_ts_round11" in sig:
            exit_r11 = _parse_ts(str(sig["exit_ts_round11"]))
        else:
            exit_r11 = entry_ts.replace(hour=15, minute=15, second=0, microsecond=0)
        qty = _qty(sig)
        chosen_id = str(sig["instrument_id"])
        alts: dict[str, str] = dict(sig.get("alternatives") or {})
        plans: list[tuple[str, str, str, datetime]] = [
            ("chosen", chosen_id, "CHASE", exit_own),
            ("strike:ATM", alts.get("ATM", chosen_id), "CHASE", exit_own),
            ("strike:ITM100", alts.get("ITM100", chosen_id), "CHASE", exit_own),
            ("strike:ITM200", alts.get("ITM200", chosen_id), "CHASE", exit_own),
            ("entry:CHASE", chosen_id, "CHASE", exit_own),
            ("entry:LIMIT:fvg", chosen_id, "LIMIT:fvg", exit_own),
            ("entry:WAIT", chosen_id, "WAIT", exit_own),
            ("exit:own", chosen_id, "CHASE", exit_own),
            ("exit:round11", chosen_id, "CHASE", exit_r11),
        ]
        if "side_flip" in spec.placebos:
            plans.append(("placebo:side_flip", chosen_id, "CHASE", exit_own))
        if "random_minute" in spec.placebos:
            shifted = entry_ts + timedelta(minutes=1)
            plans.append(("placebo:random_minute", chosen_id, "CHASE", exit_own))
        else:
            shifted = entry_ts
        for name, inst, mode, exit_ts in plans:
            use_entry = shifted if name == "placebo:random_minute" else entry_ts
            priced = _price_leg(quotes, inst, use_entry, exit_ts, qty, mode)
            if priced is None:
                continue
            if name == "placebo:side_flip":
                priced = {k: -v for k, v in priced.items()}
            legs[name] = priced
            trades.append(
                {
                    "spec_id": spec.spec_id,
                    "spec_hash": digest,
                    "session": session,
                    "signal_id": str(sig.get("signal_id") or "sg_fwd"),
                    "leg": name,
                    "entry_ts": use_entry.isoformat(),
                    "exit_ts": exit_ts.isoformat(),
                    "exit_reason": "TIME_STOP" if name != "exit:round11" else "ROUND11",
                    **priced,
                }
            )
        chosen = legs.get("chosen")
        if chosen:
            session_net += chosen["net_depth_inr"]
            session_gross += chosen["gross_inr"]

    hist_nets = [*(prior_nets or []), session_net]
    hist_gross = prior_gross + session_gross
    state = bar_state(
        n=len(hist_nets),
        gross=hist_gross,
        nets=hist_nets,
        bars=bars,
        depth_coverage=coverage,
    )
    report = _report(
        spec,
        digest,
        session,
        len(hist_nets),
        state,
        hist_nets,
        lock,
        coverage,
        legs,
        env_count,
        env_hash,
        hist_gross,
    )
    return report, trades


def _report(
    spec: ForwardSpec,
    digest: str,
    session: str,
    n: int,
    state: str,
    nets: list[float],
    lock: dict[str, Any] | None,
    coverage: float,
    legs: dict[str, dict[str, float]],
    env_count: int,
    env_hash: str,
    gross: float,
) -> ForwardReport:
    trials = int((lock or {}).get("cumulative_trials") or 4621)
    total_net = sum(nets)
    return ForwardReport(
        spec_id=spec.spec_id,
        spec_hash=digest,
        session=session,
        n=n,
        state=state,
        stage="shadow",
        headline_total_net=total_net,
        net_depth_inr=total_net,
        net_fcmeas_inr=float((legs.get("chosen") or {}).get("net_fcmeas_inr") or 0.0),
        gross_inr=gross,
        deflated_sharpe=deflated_sharpe(nets, trials),
        cumulative_trials=trials,
        depth_coverage=coverage,
        legs=legs,
        kernel_envelopes=env_count,
        kernel_hash=env_hash,
    )


def quote_from_tape(q: TapeQuote) -> Quote:
    """Adapter for brokers.fills.Quote (causal: caller already filtered asof)."""
    return Quote(
        available_ts=q.available_ts,
        bid=q.bid,
        ask=q.ask,
        ltp=q.ltp,
        instrument_id=q.instrument_id,
    )

"""Market-hours poll loop: re-run agent graph; append paper ledger.

Default tick 45s (30–60s band). Faster ticks documented, not default.
Dead-band / outside shell → HOLD-only paper emission.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional, Sequence

from trading_agents_india.config import Settings, load_settings
from trading_agents_india.candidate_audit import build_candidate_observations
from trading_agents_india.ledger import PAPER_WATCH_MIXES, append_agent_paper_tick
from trading_agents_india.paper_ledger import (
    CandidateAuditRecord,
    PaperLedger,
    PaperTrade,
    Provenance,
    SignalRecord,
)
from trading_agents_india.pipeline import run_session
from trading_agents_india.schemas import SessionResult
from trading_agents_india.session_clock import (
    DEFAULT_TICK_SECONDS,
    DOCUMENTED_FASTER_TICK_SECONDS,
    IST,
    ClockSnapshot,
    clamp_tick_seconds,
    snapshot,
)


@dataclass
class TickRecord:
    tick_index: int
    clock: dict[str, Any]
    result: SessionResult
    ledger_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick_index": self.tick_index,
            "clock": self.clock,
            "session": self.result.to_dict(),
            "ledger_paths": self.ledger_paths,
        }


@dataclass
class RunnerResult:
    ticks: list[TickRecord]
    mode: str
    tick_seconds: int
    simulated: bool
    stopped_reason: str
    documented_faster_tick_seconds: int = DOCUMENTED_FASTER_TICK_SECONDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "tick_seconds": self.tick_seconds,
            "simulated": self.simulated,
            "stopped_reason": self.stopped_reason,
            "documented_faster_tick_seconds": self.documented_faster_tick_seconds,
            "tick_count": len(self.ticks),
            "ticks": [t.to_dict() for t in self.ticks],
            "execution": "refused",
            "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
            "path_toward_faster": (
                f"Default {DEFAULT_TICK_SECONDS}s (band 30–60). "
                f"Documented future floor {DOCUMENTED_FASTER_TICK_SECONDS}s once "
                "option-chain 1/3s budget + graph cost allow; not enabled by default."
            ),
        }


def _force_hold_tickets(
    result: SessionResult,
    clock: ClockSnapshot,
    *,
    paper_paused: bool = False,
    calendar_known: bool = True,
) -> SessionResult:
    """Outside active paper window: keep audit trail but force HOLD leans."""
    guard_reason = ""
    if paper_paused:
        guard_reason = "global PAPER pause"
    elif not calendar_known:
        guard_reason = "calendar UNKNOWN — PAPER pause"
    if clock.allow_directional_paper and not guard_reason:
        return result
    for t in result.tickets:
        t.lean = "HOLD"
        t.stage = "WATCH" if not clock.in_dead_band else "VETOED"
        if clock.in_dead_band or guard_reason:
            t.risk_veto = True
            note = (
                f"paper_guard: {guard_reason}"
                if guard_reason
                else f"session_clock: {clock.reason}"
            )
            if note not in t.reasons:
                t.reasons = [note] + list(t.reasons)
            veto = (
                "PAPER_PAUSED"
                if paper_paused
                else "CALENDAR_UNKNOWN"
                if not calendar_known
                else "MIX-CLOCK-CAS dead-band"
            )
            if veto not in t.vetoes:
                t.vetoes = list(t.vetoes) + [veto]
        else:
            note = f"session_clock: {clock.reason}"
            if note not in t.reasons:
                t.reasons = [note] + list(t.reasons)
        t.execution = "refused"
    return result


def run_market_hours_loop(
    *,
    underlyings: Optional[Sequence[str]] = None,
    mode: str = "PAPER",
    tick_seconds: int = DEFAULT_TICK_SECONDS,
    max_ticks: int = 1,
    simulate: bool = False,
    simulate_clocks: Optional[Sequence[datetime]] = None,
    use_llm: bool = False,
    prefer_desk: bool = False,
    gather_india_news: bool = False,
    prefer_live_chain: bool = False,
    persist: bool = True,
    write_paper_watch: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep,
    settings: Optional[Settings] = None,
    stop_outside_shell: bool = False,
    paper_paused: bool = False,
    calendar_known: bool = True,
) -> RunnerResult:
    """Poll loop. ``simulate=True`` runs max_ticks without sleeping (dry session)."""
    settings = settings or load_settings()
    tick_seconds = clamp_tick_seconds(tick_seconds)
    resolved_mode = (mode or "PAPER").strip().upper()
    if resolved_mode not in ("PAPER", "LIVE"):
        resolved_mode = "PAPER"

    ticks: list[TickRecord] = []
    stopped = "completed_max_ticks"
    sim_clocks = list(simulate_clocks or [])

    for i in range(max(1, int(max_ticks))):
        if simulate and i < len(sim_clocks):
            clock = snapshot(sim_clocks[i])
        elif simulate:
            # Mid-window weekday default for dry simulation
            clock = snapshot(datetime(2026, 9, 4, 11, 0, tzinfo=IST))  # Thu mid-window

        else:
            clock = snapshot()

        if stop_outside_shell and not clock.in_session_shell and not simulate:
            stopped = "outside_session_shell"
            break

        result = run_session(
            underlyings=underlyings,
            dry_run=resolved_mode != "LIVE",
            use_llm=use_llm,
            prefer_desk=prefer_desk,
            gather_india_news=gather_india_news,
            prefer_live_chain=prefer_live_chain,
            persist=persist,
            mode=resolved_mode,
            settings=settings,
            clock_snapshot=clock.to_dict(),
        )
        result = _force_hold_tickets(
            result,
            clock,
            paper_paused=paper_paused,
            calendar_known=calendar_known,
        )

        ledger_paths: list[str] = []
        if write_paper_watch and resolved_mode == "PAPER":
            paths = append_agent_paper_tick(
                settings.repo_root,
                session_payload=result.to_dict(),
                tick_index=i,
                clock=clock.to_dict(),
                mixes=PAPER_WATCH_MIXES,
            )
            ledger_paths = [str(p) for p in paths]
            # Re-persist forced HOLD tickets if we mutated after first KB write
            if persist:
                from trading_agents_india.kb import AgentKB

                AgentKB(settings.kb_path).save_session(result.to_dict())

            # The typed ledger is a second, append-only audit surface.  Every
            # signal gets a shadow outcome, including SKIPPED/HOLD/VETOED
            # signals; none of these are customer fills or commission events.
            ledger = PaperLedger(
                settings.kb_path,
                settings.repo_root
                / "data"
                / "recon"
                / "paper_ledger"
                / f"{clock.as_of_ist.date().isoformat()}.jsonl",
            )
            for ticket in result.tickets:
                # Include as_of_ist so restarting market-hours (tick_index resets)
                # still appends new SIGNAL/SHADOW rows instead of colliding on day:tick.
                signal_id = f"{result.as_of_ist}:{i}:{ticket.underlying}"
                provenance = Provenance(
                    source="trading_agents_india.fixture_or_desk",
                    layer=ticket.layer,
                    observed_at_ist=result.as_of_ist,
                    freshness_status="UNKNOWN"
                    if ticket.data_gaps
                    else "FIXTURE",
                    data_gaps=list(ticket.data_gaps),
                )
                ledger.append_contract(
                    "SIGNAL",
                    SignalRecord(
                        signal_id=signal_id,
                        underlying=ticket.underlying,
                        lean=ticket.lean,
                        stage=ticket.stage,
                        as_of_ist=result.as_of_ist,
                        strategy_or_mix_id=ticket.default_mix_cited,
                        provenance=provenance,
                        vetoed=ticket.risk_veto,
                        reasons=list(ticket.reasons),
                        vetoes=list(ticket.vetoes),
                        top_veto_reasons=list(getattr(ticket, "top_veto_reasons", []) or []),
                        session_kind=str(ticket.session_kind),
                    ),
                    {"signal_id": signal_id},
                )
                for observation in build_candidate_observations(
                    ticket,
                    as_of_ist=result.as_of_ist,
                    tick_index=i,
                    bars=list(getattr(ticket, "index_bars", None) or []),
                ):
                    ledger.record_candidate_observation(
                        CandidateAuditRecord(**observation.to_dict())
                    )
                ledger.append_contract(
                    "SHADOW_TRADE",
                    PaperTrade(
                        trade_id=f"{signal_id}:shadow",
                        signal_id=signal_id,
                        underlying=ticket.underlying,
                        side=ticket.lean,
                        status="SHADOW_OPEN" if ticket.lean != "HOLD" else "SHADOW_SKIPPED",
                        quantity_lots=None,
                        entry=None,
                        exit=None,
                        realized_pnl=None,
                        shadow=True,
                        as_of_ist=result.as_of_ist,
                        provenance=provenance,
                    ),
                    {"trade_id": f"{signal_id}:shadow"},
                )

        ticks.append(
            TickRecord(
                tick_index=i,
                clock=clock.to_dict(),
                result=result,
                ledger_paths=ledger_paths,
            )
        )

        # Ops heartbeat: long --max-ticks runs otherwise print nothing until exit.
        leans = {t.underlying: t.lean for t in result.tickets}
        llm_err = None
        for gap in list(getattr(result, "data_gaps", None) or []):
            g = str(gap)
            if "rate-limit" in g.lower() or "ratelimit" in g.lower():
                llm_err = "RateLimitError" if "rate-limited" in g.lower() else "RateLimitCooldown"
                break
            if "connection cooldown" in g.lower():
                llm_err = "APIConnectionCooldown"
                break
            if "OpenAI call failed (" in g:
                # Class name only — never message body / secrets.
                start = g.rfind("(") + 1
                end = g.rfind(")")
                if start > 0 and end > start:
                    llm_err = g[start:end]
                    break
            if "last_error_class=" in g:
                llm_err = g.split("last_error_class=", 1)[-1].strip(" )")
                break
        heartbeat = {
            "event": "market_hours_tick",
            "tick_index": i,
            "max_ticks": int(max_ticks),
            "mode": resolved_mode,
            "as_of_ist": result.as_of_ist,
            "in_session_shell": clock.in_session_shell,
            "allow_directional_paper": clock.allow_directional_paper,
            "leans": leans,
            "openai_used": bool(getattr(result, "openai_used", False)),
            "use_llm": bool(use_llm),
            "prefer_live_chain": bool(prefer_live_chain),
            "llm_last_error_class": llm_err,
            "llm_calls_per_tick": sum(
                1
                for t in result.tickets
                for r in (t.reports or [])
                if isinstance(r, dict) and r.get("used_llm")
            ),
            "top_veto_reasons": {
                t.underlying: list(getattr(t, "top_veto_reasons", []) or [])[:3]
                for t in result.tickets
            },
            "index_bars": {
                t.underlying: int((getattr(t, "index_bar_meta", None) or {}).get("bar_count") or 0)
                for t in result.tickets
            },
            "index_bar_source": {
                t.underlying: str(
                    (getattr(t, "index_bar_meta", None) or {}).get("source") or "unavailable"
                )
                for t in result.tickets
            },
            "chain_metrics": {
                t.underlying: {
                    "lean": (t.premium_lean or {}).get("lean"),
                    "spot": (t.premium_lean or {}).get("spot"),
                    "pcr_oi": (t.premium_lean or {}).get("pcr_oi"),
                    "strikes": (t.premium_lean or {}).get("strike_count"),
                    "option_ltp": (t.premium_lean or {}).get("option_ltp"),
                    "entry": (t.premium_lean or {}).get("entry"),
                    "stop": (t.premium_lean or {}).get("stop"),
                    "target": (t.premium_lean or {}).get("target"),
                    "source": (t.premium_lean or {}).get("source"),
                }
                for t in result.tickets
            },
            "ledger_paths": ledger_paths,
            "execution": "refused",
            "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
            "promote": "NO_PROMOTE",
        }
        print(json.dumps(heartbeat, ensure_ascii=False), flush=True)

        if i + 1 >= max_ticks:
            break
        if not simulate:
            sleep_fn(float(tick_seconds))

    return RunnerResult(
        ticks=ticks,
        mode=resolved_mode,
        tick_seconds=tick_seconds,
        simulated=simulate,
        stopped_reason=stopped,
    )

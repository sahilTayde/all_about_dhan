"""Market-hours poll loop: re-run agent graph; append paper ledger.

Default tick 45s (30–60s band). Faster ticks documented, not default.
Dead-band / outside shell → HOLD-only paper emission.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional, Sequence

from trading_agents_india.config import Settings, load_settings
from trading_agents_india.ledger import PAPER_WATCH_MIXES, append_agent_paper_tick
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


def _force_hold_tickets(result: SessionResult, clock: ClockSnapshot) -> SessionResult:
    """Outside active paper window: keep audit trail but force HOLD leans."""
    if clock.allow_directional_paper:
        return result
    for t in result.tickets:
        t.lean = "HOLD"
        t.stage = "WATCH" if not clock.in_dead_band else "VETOED"
        if clock.in_dead_band:
            t.risk_veto = True
            note = f"session_clock: {clock.reason}"
            if note not in t.reasons:
                t.reasons = [note] + list(t.reasons)
            if "MIX-CLOCK-CAS" not in t.vetoes:
                t.vetoes = list(t.vetoes) + ["MIX-CLOCK-CAS dead-band"]
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
        result = _force_hold_tickets(result, clock)

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

        ticks.append(
            TickRecord(
                tick_index=i,
                clock=clock.to_dict(),
                result=result,
                ledger_paths=ledger_paths,
            )
        )

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

"""Desk intelligence records.

Bias / risk regime only. Education ≠ advice. Not an order ticket.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

RiskBias = Literal["RISK_ON", "RISK_OFF", "MIXED", "NO_TRADE"]
ChainLean = Literal["CE", "PE", "NEUTRAL", "NO_TRADE"]
SignalLean = Literal["BUY_CE", "BUY_PE", "NEUTRAL", "NO_TRADE"]
PollMode = Literal[
    "full_chain",
    "full_chain_3m",
    "full_chain_15m",  # legacy snapshot files; treat as full chain
    "strike_buildup_1m",
    "morning",
    "pre_market",
]
SignalStage = Literal[
    "WATCH",
    "EARLY",
    "CONFIRMED",
    "IN_PROGRESS",  # customer copy: IN-PROGRESS — live after CONFIRMED
    "EXPIRED",
    "VETOED",
]
SentimentHorizon = Literal["10m", "15m", "30m", "1h"]
SignalOutcome = Literal[
    "ACHIEVED",
    "STOPPED",
    "INVALIDATED",
    "EXPIRED",
    "LOST",
    "COMPLETED",
    "SHADOW_CLOSED",
]
SessionKind = Literal["NEWS_DAY", "EXPIRY", "NORMAL"]
# Nightly emits BACKTEST_REQUIRED only. 06 may later set REJECTED / PROMOTE_CANDIDATE.
RetuneStatus = Literal["BACKTEST_REQUIRED", "REJECTED", "PROMOTE_CANDIDATE"]

# Stages that may still be shown as live *until* an outcome is stamped.
ACTIVE_STAGES: frozenset[str] = frozenset({"WATCH", "EARLY", "CONFIRMED", "IN_PROGRESS"})
DEFAULT_SENTIMENT_WINDOWS: tuple[str, ...] = ("10m", "15m", "30m", "1h")
TERMINAL_OUTCOMES: frozenset[str] = frozenset(
    {
        "ACHIEVED",
        "STOPPED",
        "INVALIDATED",
        "EXPIRED",
        "LOST",
        "COMPLETED",
        "SHADOW_CLOSED",
    }
)

COMPLIANCE_NOTE = (
    "Education ≠ advice. MARKET_SIGNAL is a bias / risk-regime record, "
    "not a guaranteed call and not an order. See docs/COMPLIANCE.md."
)


def normalize_poll_mode(raw: Any) -> PollMode:
    text = str(raw or "").strip() or "full_chain_3m"
    if text in ("full_chain", "full_chain_3m", "full_chain_15m"):
        return "full_chain_3m" if text != "full_chain_15m" else "full_chain_15m"
    if text in ("strike_buildup_1m", "morning", "pre_market"):
        return text  # type: ignore[return-value]
    return "full_chain_3m"


def _dump(obj: Any) -> dict[str, Any]:
    return asdict(obj)


@dataclass
class NewsEvent:
    event: str
    time_ist: str
    source_id: str
    source_url: str
    headline: str
    tags: list[str]
    risk_bias: RiskBias
    surprise_vs_consensus: Optional[float] = None
    surprise_note: str = "UNKNOWN — RSS/official feeds usually have no consensus print"
    keywords_hit: list[str] = field(default_factory=list)
    cited_url: str = ""
    summary: str = ""
    layer: str = "HYPOTHESIS"

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class StrikeRow:
    strike: float
    ce_oi: int = 0
    pe_oi: int = 0
    ce_oi_prev: int = 0
    pe_oi_prev: int = 0
    ce_volume: int = 0
    pe_volume: int = 0
    ce_ltp: Optional[float] = None
    pe_ltp: Optional[float] = None
    ce_security_id: Optional[int] = None
    pe_security_id: Optional[int] = None
    ce_gamma: Optional[float] = None
    pe_gamma: Optional[float] = None
    ce_delta: Optional[float] = None
    pe_delta: Optional[float] = None

    @property
    def ce_oi_change(self) -> int:
        return int(self.ce_oi) - int(self.ce_oi_prev)

    @property
    def pe_oi_change(self) -> int:
        return int(self.pe_oi) - int(self.pe_oi_prev)


@dataclass
class ChainSnapshot:
    underlying: str
    expiry: Optional[str]
    spot: Optional[float]
    as_of_ist: str
    mode: PollMode
    dry_run: bool
    strikes: list[StrikeRow]
    source: str = "dhan_option_chain"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class ChainBias:
    underlying: str
    expiry: Optional[str]
    spot: Optional[float]
    atm_strike: Optional[float]
    pcr_oi: Optional[float]
    pcr_volume: Optional[float]
    max_pain_stub: Optional[float]
    ce_oi_wall: Optional[float]
    pe_oi_wall: Optional[float]
    atm_ce_oi: int
    atm_pe_oi: int
    atm_ce_buildup: int
    atm_pe_buildup: int
    wing_ce_buildup: int
    wing_pe_buildup: int
    gamma_load_stub: Optional[float]
    lean: ChainLean
    reasons: list[str]
    as_of_ist: str
    dry_run: bool = False
    mode: PollMode = "full_chain_3m"
    vs_last_as_of_ist: Optional[str] = None
    has_prior_snapshot: bool = False
    pcr_oi_delta: Optional[float] = None
    pcr_volume_delta: Optional[float] = None
    total_ce_oi_delta: Optional[int] = None
    total_pe_oi_delta: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class SentimentWindow:
    """News+chain lean on a named horizon. Mock until rolling windows exist."""

    horizon: str
    lean: SignalLean
    confidence: float
    news_bias: RiskBias
    chain_lean: ChainLean
    mock: bool = True
    note: str = (
        "Schema stub for dashboard bind. Not a measured rolling window. Not edge."
    )

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class MarketSignal:
    """Fused bias record. Maps later to GET /paper/signal (directional leans only)."""

    id: str
    underlying: str
    lean: SignalLean
    confidence: float
    risk_regime: RiskBias
    reasons: list[str]
    vetoes: list[str]
    timestamp: str
    news_bias: RiskBias
    chain_bias: ChainLean
    tags: list[str]
    expiry: Optional[str] = None
    atm_strike: Optional[float] = None
    dry_run: bool = True
    layer: str = "HYPOTHESIS"
    compliance: str = COMPLIANCE_NOTE
    paper_signal: Optional[dict[str, Any]] = None
    stage: SignalStage = "WATCH"
    outcome: Optional[SignalOutcome] = None
    still_valid: bool = False
    sentiment_windows: list[SentimentWindow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class TapePrint:
    """One VERIFY/TODO/RSS tape row. Never a Dhan-invented quote."""

    id: str
    bucket: str  # gift_nifty | sgx | pre_open | global_us | global_asia
    status: str  # FIXTURE | RSS | VERIFY | TODO | DATA_INSUFFICIENT
    headline: str
    source_url: str
    note: str
    level: Optional[float] = None
    vs_cash_note: str = ""
    tags: list[str] = field(default_factory=list)
    layer: str = "HYPOTHESIS"

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class PremarketBrief:
    as_of_ist: str
    job: str
    before_ist: str
    news_count: int
    tape: list[TapePrint]
    regime_note: str
    missing: list[str]
    compliance: str = COMPLIANCE_NOTE

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class UserFill:
    """Customer took the idea. Lots / spot / reported P/L — not a live order."""

    took_trade: bool
    lots: Optional[int] = None
    spot: Optional[float] = None
    reported_pnl: Optional[float] = None
    recorded_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class ShadowPaper:
    """Platform papers the signal for learning. Never a live order."""

    active: bool
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    last_mark: Optional[float] = None
    pnl_pts: Optional[float] = None
    closed_as: Optional[SignalOutcome] = None
    note: str = "Shadow paper ledger only. Execution refused."

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class LifecycleRecord:
    """Stage (WATCH/EARLY/CONFIRMED/IN-PROGRESS) plus terminal outcome.

    Stale CONFIRMED/IN-PROGRESS is forbidden once an outcome is stamped.
    """

    signal_id: str
    underlying: str
    lean: str
    stage: SignalStage
    outcome: Optional[SignalOutcome]
    still_valid: bool
    user: UserFill
    shadow: ShadowPaper
    reasons: list[str] = field(default_factory=list)
    lagging_late: list[str] = field(default_factory=list)
    as_of_ist: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class SessionTag:
    """NEWS_DAY / EXPIRY / NORMAL. Event days are not a retune sample."""

    kind: SessionKind
    flags: list[str]
    reasons: list[str] = field(default_factory=list)
    usable_for_retune_sample: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)


@dataclass
class RetuneProposal:
    """Nightly candidate packet. Never a production param write.

    status is always BACKTEST_REQUIRED from POST_MARKET. backtest_results stays
    None — do not invent metrics. PhD handoff is REVIEW, not auto-apply.
    """

    kind: str = "RETUNE_PROPOSAL"
    status: RetuneStatus = "BACKTEST_REQUIRED"
    keep_current_strategy: bool = True
    production_params_written: bool = False
    handoff: str = "REVIEW"
    backtest_owner: str = "06_backtesting"
    session_kind: SessionKind = "NORMAL"
    session_flags: list[str] = field(default_factory=lambda: ["NORMAL"])
    session_usable_for_retune_sample: bool = True
    oos_non_event_required: bool = True
    metrics_required: list[str] = field(
        default_factory=lambda: ["expectancy", "profit_factor", "max_drawdown"]
    )
    one_day_pnl_is_not_evidence: bool = True
    backtest_results: Optional[dict[str, Any]] = None
    candidate_notes: list[str] = field(default_factory=list)
    note: str = (
        "Default: keep current strategy. Do not invent backtest results. "
        "Do not live-trade."
    )

    def to_dict(self) -> dict[str, Any]:
        return _dump(self)

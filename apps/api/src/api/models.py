"""Dashboard paper-desk payload — same shape as apps/web/public/mock/signal.json.

The Vite UI loads GET ${VITE_API_URL}/paper/signal (see apps/web/src/lib/signalApi.js).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Underlying(str, Enum):
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    SENSEX = "SENSEX"


class SignalSide(str, Enum):
    BUY_CE = "BUY_CE"
    BUY_PE = "BUY_PE"


class SystemOutcome(BaseModel):
    mtmPts: float
    comment: str
    outcome: Optional[
        Literal[
            "ACHIEVED",
            "STOPPED",
            "INVALIDATED",
            "EXPIRED",
            "LOST",
            "COMPLETED",
            "SHADOW_CLOSED",
        ]
    ] = None
    shadow: bool = False


class LifecycleShadow(BaseModel):
    """Mock paper path when the user skipped. Not a live fill."""

    mtmPts: float
    comment: str = ""


class SignalLifecycle(BaseModel):
    """Terminal ticket label so lunch-return is not a leftover CONFIRMED.

    TODO(jobs): nightly recon stamps outcome; not live Dhan from the browser.
    """

    outcome: Optional[
        Literal[
            "ACHIEVED",
            "STOPPED",
            "INVALIDATED",
            "EXPIRED",
            "LOST",
            "COMPLETED",
            "SHADOW_CLOSED",
        ]
    ] = None
    priorStage: Optional[Literal["WATCH", "EARLY", "CONFIRMED", "EXPIRED", "VETOED"]] = None
    headline: str = ""
    note: str = ""
    closedAt: str = ""
    stillValid: bool = False
    shadowPaper: Optional[LifecycleShadow] = None


class StagedLight(BaseModel):
    id: str
    label: str
    state: Literal["idle", "leaning", "lagging", "confirm", "against"]
    detail: str = ""


class StagedFactor(BaseModel):
    id: str
    label: str
    on: bool
    detail: str = ""


class StagedSignal(BaseModel):
    """Honesty labels for the paper desk. Not a fillable ticket.

    TODO(api): keep this in GET /paper/signal when the dashboard is wired remote.
    TODO(desk_intel): map MARKET_SIGNAL + factor flags later.
    TODO(ohlc): do not compute Supertrend/RSI/EMA9/MACD here yet.
    """

    state: Literal["WATCH", "EARLY", "CONFIRMED", "EXPIRED", "VETOED"]
    waiting: bool = False
    waitLabel: str = ""
    lean: SignalSide
    headline: str
    note: str
    outcome: Optional[
        Literal[
            "ACHIEVED",
            "STOPPED",
            "INVALIDATED",
            "EXPIRED",
            "LOST",
            "COMPLETED",
            "SHADOW_CLOSED",
        ]
    ] = None
    stillValid: bool = False
    lights: List[StagedLight] = Field(default_factory=list)
    factors: List[StagedFactor] = Field(default_factory=list)


class DeskSignal(BaseModel):
    id: str
    underlying: Underlying
    side: SignalSide
    strike: Optional[float] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    expiry: Optional[str] = Field(
        default=None,
        description="Mock uses the string 'placeholder'. Live expiry format: VERIFY / leave room.",
    )
    systemOutcome: Optional[SystemOutcome] = None
    lifecycle: Optional[SignalLifecycle] = None
    staged: Optional[StagedSignal] = None


class PaperMeta(BaseModel):
    source: Literal["mock"] = "mock"
    placeholder: bool = True
    asOf: str
    note: str


class PaperDesk(BaseModel):
    """Exact dashboard document (plus optional dry_run on /signals if we want it)."""

    meta: PaperMeta
    underlyings: List[str]
    signals: Dict[str, DeskSignal]


class TookTradeBody(BaseModel):
    took_trade: bool
    lots: Optional[int] = None
    spot: Optional[float] = None
    reported_pnl: Optional[float] = None


class TookTradeRecord(BaseModel):
    signal_id: str
    took_trade: bool
    recorded_at: str
    lots: Optional[int] = None
    spot: Optional[float] = None
    reported_pnl: Optional[float] = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def mock_desk() -> PaperDesk:
    """Numbers match apps/web/public/mock/signal.json so UI wiring is identical."""
    path = (
        Path(__file__).resolve().parents[3] / "web" / "public" / "mock" / "signal.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PaperDesk.model_validate(payload)

"""Dashboard paper-desk payload — same shape as apps/web/public/mock/signal.json.

The Vite UI loads GET ${VITE_API_URL}/paper/signal (see apps/web/src/lib/signalApi.js).

Entry/stop/target may be float (option premium) or DATA_INSUFFICIENT string.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class Underlying(str, Enum):
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    SENSEX = "SENSEX"


class SignalSide(str, Enum):
    BUY_CE = "BUY_CE"
    BUY_PE = "BUY_PE"
    HOLD = "HOLD"


LevelValue = Optional[Union[float, int, str]]


class SystemOutcome(BaseModel):
    model_config = ConfigDict(extra="allow")

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

    model_config = ConfigDict(extra="allow")

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
    priorStage: Optional[str] = None
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
    """Honesty labels for the paper desk. Not a fillable ticket."""

    model_config = ConfigDict(extra="allow")

    state: str
    waiting: bool = False
    waitLabel: str = ""
    lean: Optional[str] = None
    headline: str = ""
    note: str = ""
    outcome: Optional[str] = None
    stillValid: bool = False
    lights: List[StagedLight] = Field(default_factory=list)
    factors: List[StagedFactor] = Field(default_factory=list)


class TicketLevels(BaseModel):
    model_config = ConfigDict(extra="allow")

    unit: str = "OPTION_PREMIUM"
    levels_ready: bool = False
    levels_note: str = ""
    entry: LevelValue = None
    stop: LevelValue = None
    target: LevelValue = None
    strike: LevelValue = None
    underlying_spot: LevelValue = None
    index_entry: LevelValue = None
    index_stop: LevelValue = None
    index_target: LevelValue = None


class DeskSignal(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    underlying: str
    side: str
    strike: LevelValue = None
    entry: LevelValue = None
    stop: LevelValue = None
    target: LevelValue = None
    expiry: Optional[str] = Field(
        default=None,
        description="Mock uses the string 'placeholder'. Live expiry format: VERIFY.",
    )
    systemOutcome: Optional[SystemOutcome] = None
    lifecycle: Optional[SignalLifecycle] = None
    staged: Optional[StagedSignal] = None
    ticket: Optional[TicketLevels] = None
    underlying_spot: LevelValue = None
    spot: LevelValue = None
    customer: Optional[Dict[str, Any]] = None
    confidence: Optional[Dict[str, Any]] = None


class PaperMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str = "mock"
    placeholder: bool = True
    asOf: str
    note: str
    label: Optional[str] = None


class PaperDesk(BaseModel):
    """Dashboard document. Extra keys (todaysBook, fixtureBook, cas…) allowed."""

    model_config = ConfigDict(extra="allow")

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


def mock_desk_payload() -> dict[str, Any]:
    """Raw dashboard JSON (includes todaysBook / fixtureBook / ticket DI)."""
    path = (
        Path(__file__).resolve().parents[3] / "web" / "public" / "mock" / "signal.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def mock_desk() -> PaperDesk:
    """Numbers match apps/web/public/mock/signal.json so UI wiring is identical."""
    return PaperDesk.model_validate(mock_desk_payload())

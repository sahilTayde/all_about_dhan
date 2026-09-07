"""Local fixture adapter for PAPER customer actions and EOD exports.

This is intentionally not an HTTP or broker adapter.  Customer actions are
declarations against signal IDs, never broker fills or execution requests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from trading_agents_india.paper_ledger import (
    CustomerAction,
    CustomerActionKind,
    PaperLedger,
)


class PaperFixtureAdapter:
    """Small broker-independent API over :class:`PaperLedger`."""

    def __init__(self, ledger: PaperLedger) -> None:
        self.ledger = ledger

    def record_action(
        self,
        *,
        signal_id: str,
        action: CustomerActionKind,
        recorded_at_ist: str,
        correction_of: Optional[str] = None,
        lots: Optional[int] = None,
        reported_pnl: Optional[float] = None,
    ) -> bool:
        return self.ledger.record_customer_action(
            CustomerAction(
                signal_id=signal_id,
                action=action,
                recorded_at_ist=recorded_at_ist,
                correction_of=correction_of,
                lots=lots,
                reported_pnl=reported_pnl,
            )
        )

    def export_eod(self, day: str, output_path: Optional[Path] = None) -> dict:
        return self.ledger.export_eod(day, output_path)

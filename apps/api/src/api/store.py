"""In-memory mock paper desk. Replace later; keep the JSON shape stable."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.models import TookTradeRecord, mock_desk_payload, utc_now_iso


class SignalStore:
    def __init__(self) -> None:
        self.desk: dict[str, Any] = mock_desk_payload()
        self.took_trade: Dict[str, TookTradeRecord] = {}

    def paper_desk(self) -> dict[str, Any]:
        return self.desk

    def signal_by_id(self, signal_id: str) -> Optional[dict[str, Any]]:
        signals = self.desk.get("signals") or {}
        for row in signals.values():
            if isinstance(row, dict) and row.get("id") == signal_id:
                return row
        return None

    def record_took_trade(
        self,
        signal_id: str,
        took_trade: bool,
        *,
        lots: Optional[int] = None,
        spot: Optional[float] = None,
        reported_pnl: Optional[float] = None,
    ) -> Optional[TookTradeRecord]:
        if self.signal_by_id(signal_id) is None:
            return None
        rec = TookTradeRecord(
            signal_id=signal_id,
            took_trade=took_trade,
            recorded_at=utc_now_iso(),
            lots=lots,
            spot=spot,
            reported_pnl=reported_pnl,
        )
        self.took_trade[signal_id] = rec
        return rec

    def took_trade_list(self) -> List[TookTradeRecord]:
        return list(self.took_trade.values())

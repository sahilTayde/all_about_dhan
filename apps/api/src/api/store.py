"""In-memory mock paper desk. Replace later; keep the JSON shape stable."""

from __future__ import annotations

from typing import Dict, List, Optional

from api.models import PaperDesk, TookTradeRecord, mock_desk, utc_now_iso


class SignalStore:
    def __init__(self) -> None:
        self.desk: PaperDesk = mock_desk()
        self.took_trade: Dict[str, TookTradeRecord] = {}

    def paper_desk(self) -> PaperDesk:
        return self.desk

    def signal_by_id(self, signal_id: str):
        for row in self.desk.signals.values():
            if row.id == signal_id:
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

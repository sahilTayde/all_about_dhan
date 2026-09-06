"""Facade: one object for REST helpers + feed + refused execution."""

from __future__ import annotations

from typing import Optional

from dhan_client.config import Settings, load_settings
from dhan_client.execution import ExecutionClient
from dhan_client.feed import MarketFeedCollector
from dhan_client.historical import HistoricalClient
from dhan_client.instruments import InstrumentClient
from dhan_client.option_chain import OptionChainClient
from dhan_client.profile import ProfileClient
from dhan_client.quote import QuoteClient
from dhan_client.rest import RestClient
from dhan_client.types import FeedInstrument, FeedMode


class DhanClient:
    def __init__(self, settings: Optional[Settings] = None, *, dry_run: Optional[bool] = None) -> None:
        self.settings = settings or load_settings(dry_run=dry_run)
        self.rest = RestClient(self.settings)
        self.quote = QuoteClient(self.rest)
        self.historical = HistoricalClient(self.rest)
        self.option_chain = OptionChainClient(self.rest)
        self.instruments = InstrumentClient(self.rest)
        self.profile = ProfileClient(self.rest)
        self.execution = ExecutionClient(self.settings)

    @property
    def dry_run(self) -> bool:
        return self.settings.dry_run

    def close(self) -> None:
        self.rest.close()

    def __enter__(self) -> DhanClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def feed_collector(
        self,
        instruments: list[FeedInstrument],
        *,
        mode: FeedMode = FeedMode.TICKER,
        reconnect: bool = True,
    ) -> MarketFeedCollector:
        return MarketFeedCollector(
            self.settings,
            instruments,
            mode=mode,
            reconnect=reconnect,
        )

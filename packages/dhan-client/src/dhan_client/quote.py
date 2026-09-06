"""Market quote snapshots — documented paths only.

https://dhanhq.co/docs/v2/market-quote/

POST /marketfeed/ltp | /marketfeed/ohlc | /marketfeed/quote
Body example: ``{"NSE_EQ":[11536], "NSE_FNO":[49081,49082]}``
Headers: access-token, client-id
Limit: 1000 instruments / request, 1 request per second.
"""

from __future__ import annotations

from typing import Sequence

from dhan_client import endpoints
from dhan_client.rate_limit import MinIntervalGate
from dhan_client.rest import RestClient
from dhan_client.types import JsonDict, QuoteBody, SecurityId


def _normalize_quote_body(securities: QuoteBody) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    total = 0
    for segment, ids in securities.items():
        if not isinstance(ids, Sequence) or isinstance(ids, (str, bytes)):
            raise ValueError(f"security id list for {segment!r} must be a sequence")
        parsed: list[int] = []
        for raw in ids:
            parsed.append(int(raw))
        out[str(segment)] = parsed
        total += len(parsed)
    if total > endpoints.QUOTE_MAX_INSTRUMENTS:
        raise ValueError(
            f"quote APIs allow at most {endpoints.QUOTE_MAX_INSTRUMENTS} instruments"
        )
    if total < 1:
        raise ValueError("quote body is empty")
    return out


class QuoteClient:
    def __init__(self, rest: RestClient) -> None:
        self._rest = rest
        # Official intro: Quote APIs 1 request / second.
        self._gate = MinIntervalGate(1.0 / endpoints.RATE_LIMIT_QUOTE_PER_SEC)

    def _wait(self) -> None:
        if self._rest.settings.dry_run:
            return
        self._gate.wait()

    def ltp(self, securities: QuoteBody) -> JsonDict:
        self._wait()
        return self._rest.request(
            "POST",
            endpoints.MARKETFEED_LTP,
            json_body=_normalize_quote_body(securities),
        )

    def ohlc(self, securities: QuoteBody) -> JsonDict:
        self._wait()
        return self._rest.request(
            "POST",
            endpoints.MARKETFEED_OHLC,
            json_body=_normalize_quote_body(securities),
        )

    def quote(self, securities: QuoteBody) -> JsonDict:
        self._wait()
        return self._rest.request(
            "POST",
            endpoints.MARKETFEED_QUOTE,
            json_body=_normalize_quote_body(securities),
        )


# Re-export for type checkers / callers building a body.
__all__ = ["QuoteClient", "SecurityId"]

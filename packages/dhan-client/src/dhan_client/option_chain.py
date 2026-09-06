"""Option chain — documented paths only.

https://dhanhq.co/docs/v2/option-chain/

POST /optionchain
  Body: UnderlyingScrip (int), UnderlyingSeg (enum), Expiry (YYYY-MM-DD)
POST /optionchain/expirylist
  Body: UnderlyingScrip, UnderlyingSeg

Rate limit: one unique request every 3 seconds.

Do **not** hardcode NIFTY / BANKNIFTY / SENSEX security IDs here.
The official example uses ``UnderlyingScrip: 13``, ``UnderlyingSeg: "IDX_I"``
without naming the index. Look IDs up from the instrument master.
"""

from __future__ import annotations

from dhan_client import endpoints
from dhan_client.errors import NotImplementedInSkeleton
from dhan_client.rate_limit import MinIntervalGate
from dhan_client.rest import RestClient
from dhan_client.types import JsonDict, OptionChainBody, OptionExpiryListBody


def _require_underlying(body: dict) -> dict:
    if body.get("UnderlyingScrip") in (None, ""):
        raise ValueError("UnderlyingScrip is required")
    if not body.get("UnderlyingSeg"):
        raise ValueError("UnderlyingSeg is required")
    out = dict(body)
    out["UnderlyingScrip"] = int(out["UnderlyingScrip"])
    out["UnderlyingSeg"] = str(out["UnderlyingSeg"])
    return out


class OptionChainClient:
    def __init__(self, rest: RestClient) -> None:
        self._rest = rest
        # Docs: 1 unique option-chain request / 3 s (expiry list + chain share the budget).
        self._gate = MinIntervalGate(endpoints.RATE_LIMIT_OPTION_CHAIN_SECONDS)

    def _wait_rate_limit(self) -> None:
        if self._rest.settings.dry_run:
            return
        self._gate.wait()

    def expiry_list(self, body: OptionExpiryListBody) -> JsonDict:
        self._wait_rate_limit()
        return self._rest.request(
            "POST",
            endpoints.OPTION_CHAIN_EXPIRY_LIST,
            json_body=_require_underlying(dict(body)),
        )

    def chain(self, body: OptionChainBody) -> JsonDict:
        payload = _require_underlying(dict(body))
        if not payload.get("Expiry"):
            raise ValueError("Expiry is required (YYYY-MM-DD)")
        payload["Expiry"] = str(payload["Expiry"])
        self._wait_rate_limit()
        return self._rest.request(
            "POST",
            endpoints.OPTION_CHAIN,
            json_body=payload,
        )

    def rolling_expired(self, *_args: object, **_kwargs: object) -> JsonDict:
        """Charts rollingoption is a Data API. Use ``DhanClient.historical.rolling_option``."""
        raise NotImplementedInSkeleton(
            "POST /charts/rollingoption is gated as Data API 5/s. "
            "Call client.historical.rolling_option (not this chain 3s bucket). "
            f"Path: {endpoints.CHARTS_ROLLING_OPTION}"
        )

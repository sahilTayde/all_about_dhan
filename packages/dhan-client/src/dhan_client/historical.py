"""Historical candles — documented paths only.

https://dhanhq.co/docs/v2/historical-data/

POST /charts/historical  — daily OHLC; toDate is non-inclusive
POST /charts/intraday    — 1, 5, 15, 25, 60 min; max 90 days per call

Official daily curl shows ``access-token`` only (no ``client-id``).
Intraday sample uses ``interval`` as the string ``"1"`` while the table says
enum integer. Both are accepted here and sent through. VERIFY FROM DOCS.
"""

from __future__ import annotations

from dhan_client import endpoints
from dhan_client.rate_limit import MinIntervalGate
from dhan_client.rest import RestClient
from dhan_client.types import HistoricalDailyBody, HistoricalIntradayBody, JsonDict, RollingOptionBody

INTRADAY_INTERVALS = (1, 5, 15, 25, 60)


def _require(body: dict, *keys: str) -> None:
    missing = [k for k in keys if body.get(k) in (None, "")]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")


class HistoricalClient:
    def __init__(self, rest: RestClient) -> None:
        self._rest = rest
        # Official intro: Data APIs 5 requests / second (charts/historical + intraday).
        self._gate = MinIntervalGate(1.0 / endpoints.RATE_LIMIT_DATA_PER_SEC)

    def _wait(self) -> None:
        if self._rest.settings.dry_run:
            return
        self._gate.wait()

    def daily(self, body: HistoricalDailyBody) -> JsonDict:
        payload = dict(body)
        _require(payload, "securityId", "exchangeSegment", "instrument", "fromDate", "toDate")
        payload["securityId"] = str(payload["securityId"])
        self._wait()
        return self._rest.request(
            "POST",
            endpoints.CHARTS_HISTORICAL,
            json_body=payload,
        )

    def intraday(self, body: HistoricalIntradayBody) -> JsonDict:
        payload = dict(body)
        _require(
            payload,
            "securityId",
            "exchangeSegment",
            "instrument",
            "interval",
            "fromDate",
            "toDate",
        )
        payload["securityId"] = str(payload["securityId"])
        interval = payload["interval"]
        try:
            interval_n = int(interval)
        except (TypeError, ValueError) as exc:
            raise ValueError("interval must be 1, 5, 15, 25, or 60") from exc
        if interval_n not in INTRADAY_INTERVALS:
            raise ValueError("interval must be 1, 5, 15, 25, or 60")
        # Official sample JSON uses a string; table says integer. Send string like the sample.
        payload["interval"] = str(interval_n)
        self._wait()
        return self._rest.request(
            "POST",
            endpoints.CHARTS_INTRADAY,
            json_body=payload,
        )

    def rolling_option(self, body: RollingOptionBody) -> JsonDict:
        """POST /charts/rollingoption — expired/rolling OPTIDX. Data API 5/s, 30 days/call.

        https://dhanhq.co/docs/v2/expired-options-data/
        """
        payload = dict(body)
        _require(
            payload,
            "exchangeSegment",
            "interval",
            "securityId",
            "instrument",
            "expiryFlag",
            "expiryCode",
            "strike",
            "drvOptionType",
            "requiredData",
            "fromDate",
            "toDate",
        )
        payload["securityId"] = str(payload["securityId"])
        try:
            expiry_code = int(payload["expiryCode"])
        except (TypeError, ValueError) as exc:
            raise ValueError("expiryCode must be an integer") from exc
        # Annexure lists 0 = near. Live POST 2026-09-03 returns
        # "expiryCode is required" when the JSON value is 0. Send 1 (next).
        if expiry_code < 1:
            expiry_code = 1
        payload["expiryCode"] = expiry_code
        payload["interval"] = str(int(payload["interval"]))
        payload["expiryFlag"] = str(payload["expiryFlag"]).upper()
        payload["drvOptionType"] = str(payload["drvOptionType"]).upper()
        if payload["expiryFlag"] not in ("WEEK", "MONTH"):
            raise ValueError("expiryFlag must be WEEK or MONTH")
        if payload["drvOptionType"] not in ("CALL", "PUT"):
            raise ValueError("drvOptionType must be CALL or PUT")
        self._wait()
        return self._rest.request(
            "POST",
            endpoints.CHARTS_ROLLING_OPTION,
            json_body=payload,
        )

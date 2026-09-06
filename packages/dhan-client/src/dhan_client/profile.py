"""GET /profile — Non Trading API (official intro table: 20/s).

https://dhanhq.co/docs/v2/authentication/ and https://dhanhq.co/docs/v2/
Never log token values. Callers must sanitize PII before writing reports.
"""

from __future__ import annotations

from dhan_client import endpoints
from dhan_client.rest import RestClient
from dhan_client.types import JsonDict


class ProfileClient:
    def __init__(self, rest: RestClient) -> None:
        self._rest = rest

    def get(self) -> JsonDict:
        return self._rest.request("GET", endpoints.PROFILE)

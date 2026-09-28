from __future__ import annotations

import httpx
from dhan_client.config import Credentials, Settings
from dhan_client.endpoints import (
    MARKETFEED_LTP,
    OPTION_CHAIN,
    OPTION_CHAIN_EXPIRY_LIST,
    RATE_LIMIT_DATA_PER_SEC,
    RATE_LIMIT_OPTION_CHAIN_SECONDS,
    RATE_LIMIT_QUOTE_PER_SEC,
)
from dhan_client.errors import DhanApiError
from dhan_client.rate_limit import (
    RATE_LIMIT_429_BACKOFF_CAP_S,
    RATE_LIMIT_429_BACKOFF_START_S,
    EndpointRateLimiter,
    MinIntervalGate,
    bucket_for,
    is_rate_limit_error,
    min_interval_s,
)
from dhan_client.rest import RestClient


def test_documented_caps() -> None:
    assert RATE_LIMIT_QUOTE_PER_SEC == 1
    assert RATE_LIMIT_DATA_PER_SEC == 5
    assert RATE_LIMIT_OPTION_CHAIN_SECONDS == 3


def test_gate_zero_first_call() -> None:
    g = MinIntervalGate(0.01)
    slept = g.wait()
    assert slept >= 0.0


def test_central_limiter_per_endpoint_documented_limits() -> None:
    clock = [1000.0]
    slept: list[float] = []

    def mono() -> float:
        return clock[0]

    def sleep(s: float) -> None:
        slept.append(s)
        clock[0] += s

    lim = EndpointRateLimiter(clock=mono, sleep=sleep)
    assert bucket_for(OPTION_CHAIN) == bucket_for(OPTION_CHAIN_EXPIRY_LIST)
    assert min_interval_s(bucket_for(OPTION_CHAIN)) == 3.0
    assert min_interval_s(bucket_for(MARKETFEED_LTP)) == 1.0
    assert min_interval_s(bucket_for("/charts/historical")) == 0.2
    lim.acquire(OPTION_CHAIN)
    lim.acquire(OPTION_CHAIN_EXPIRY_LIST)
    assert slept == [3.0]
    lim.acquire(MARKETFEED_LTP)
    assert slept == [3.0]  # first quote call: no wait
    lim.acquire(MARKETFEED_LTP)
    assert slept[-1] == 1.0


def test_429_805_backoff_exponential_never_retries_immediately() -> None:
    clock = [0.0]
    slept: list[float] = []

    def mono() -> float:
        return clock[0]

    def sleep(s: float) -> None:
        slept.append(s)
        clock[0] += s

    lim = EndpointRateLimiter(clock=mono, sleep=sleep)
    first = lim.note_rate_limit(OPTION_CHAIN)
    assert first == RATE_LIMIT_429_BACKOFF_START_S
    assert lim.hits(OPTION_CHAIN) == 1
    assert lim.remaining_s(OPTION_CHAIN) == 60.0
    lim.acquire(OPTION_CHAIN)
    assert slept == [60.0]
    second = lim.note_rate_limit(OPTION_CHAIN)
    assert second == 120.0
    clock[0] += 120.0
    last = 0.0
    for _ in range(8):
        last = lim.note_rate_limit(OPTION_CHAIN)
        clock[0] += last
    assert last == RATE_LIMIT_429_BACKOFF_CAP_S


def test_is_rate_limit_error_http_429_and_code_805() -> None:
    assert is_rate_limit_error(DhanApiError("slow", status_code=429))
    assert is_rate_limit_error(DhanApiError("Too many requests", error_code="805"))
    assert is_rate_limit_error(
        DhanApiError(
            "Too many requests. Further requests may result in the user being blocked."
        )
    )
    assert not is_rate_limit_error(
        DhanApiError("bad", status_code=400, error_code="DH-905")
    )


def test_rest_client_handles_429_and_805_body() -> None:
    clock = [0.0]
    slept: list[float] = []

    def mono() -> float:
        return clock[0]

    def sleep(s: float) -> None:
        slept.append(s)
        clock[0] += s

    lim = EndpointRateLimiter(clock=mono, sleep=sleep)
    hits = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        hits["n"] += 1
        return httpx.Response(
            429,
            json={
                "805": "Too many requests. Further requests may result in the user being blocked."
            },
        )

    settings = Settings(
        credentials=Credentials(client_id="cid", access_token="tok"),
        dry_run=False,
    )
    client = RestClient(settings, limiter=lim)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        try:
            client.request(
                "POST",
                OPTION_CHAIN,
                json_body={"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"},
            )
        except DhanApiError as exc:
            assert exc.status_code == 429
            assert exc.error_code == "805"
            assert "Too many requests" in str(exc)
        else:
            raise AssertionError("expected DhanApiError")
        assert lim.hits(OPTION_CHAIN) == 1
        assert hits["n"] == 1
        try:
            client.request(
                "POST",
                OPTION_CHAIN,
                json_body={"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I"},
            )
        except DhanApiError:
            pass
        assert slept[0] == RATE_LIMIT_429_BACKOFF_START_S
        assert hits["n"] == 2
    finally:
        client.close()

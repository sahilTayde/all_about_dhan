"""Spot fallback: no chain after index ticks; 60 s cadence; 429/805 backoff."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from dhan_client.endpoints import OPTION_CHAIN
from dhan_client.errors import DhanApiError
from dhan_client.rate_limit import default_limiter, reset_default_limiter
from md_fake_dhan import StubSource, ist, make_universe, read_rows, run_session

from marketdata.config import RecorderConfig


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    reset_default_limiter()
    yield
    reset_default_limiter()


def test_no_option_chain_spot_once_index_ticks_arrive(tmp_path: Path) -> None:
    source = StubSource()
    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 1),
            source=source,
            universe=make_universe(),
            config_kw={"spot_fallback_after_s": 1.0, "spot_poll_s": 1.0},
            step=0.25,
        )
    )
    assert source.calls.count("option_chain") == 0
    assert s.recorder._index_tick_seen


def test_spot_fallback_polls_at_most_once_per_configured_interval(tmp_path: Path) -> None:
    assert RecorderConfig(tape_root=tmp_path).spot_poll_s == 60.0
    source = StubSource()
    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 1, 10),
            source=source,
            universe=make_universe(),
            market_kw={"silent": {13: [(ist(10, 0), ist(10, 5))]}},
            config_kw={"spot_fallback_after_s": 5.0, "spot_poll_s": 60.0},
            step=1.0,
        )
    )
    n = source.calls.count("option_chain")
    assert n == 2  # first after 5 s, next at 65 s; a 30 s poll would have been 3+
    assert not s.recorder._index_tick_seen


def test_429_805_backoff_logged_once_counted_no_immediate_retry(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    err = DhanApiError(
        "Too many requests. Further requests may result in the user being blocked.",
        status_code=429,
        error_code="805",
    )
    source = StubSource(fail={"option_chain": [err, err, err]})
    with caplog.at_level(logging.WARNING):
        s = asyncio.run(
            run_session(
                tmp_path,
                ist(10, 0),
                ist(10, 0, 25),
                source=source,
                universe=make_universe(),
                market_kw={"silent": {13: [(ist(10, 0), ist(10, 1))]}},
                config_kw={"spot_fallback_after_s": 2.0, "spot_poll_s": 1.0},
                step=0.25,
            )
        )
    assert source.calls.count("option_chain") == 1
    assert default_limiter().hits(OPTION_CHAIN) == 1
    assert default_limiter().remaining_s(OPTION_CHAIN) > 0
    logs = [r.message for r in caplog.records if "429/805" in r.message]
    assert len(logs) == 1
    rows = read_rows(tmp_path / "tape" / "2026-09-28" / "feed_status.jsonl")
    assert rows[-1]["payload"]["rest_429s"] >= 1
    with caplog.at_level(logging.INFO):
        s.recorder._log_status(ist(10, 0))
    assert "rest_429s=" in caplog.text

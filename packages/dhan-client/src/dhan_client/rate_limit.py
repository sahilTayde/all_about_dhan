"""Minimum-interval gates and 429/805 backoff for documented DhanHQ rate limits.

Option chain: one unique request every 3 seconds
(https://dhanhq.co/docs/v2/option-chain/). Quote: 1 request/second.
Data APIs: 5/s. Non-trading: 20/s. On HTTP 429 or Dhan code 805 the next
call waits exponentially (60 s, cap 15 min) — never retry immediately.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from dhan_client import endpoints

log = logging.getLogger(__name__)

RATE_LIMIT_429_BACKOFF_START_S = 60.0
RATE_LIMIT_429_BACKOFF_CAP_S = 900.0  # 15 min

_RATE_CODES = frozenset({"429", "805"})


def bucket_for(path: str) -> str:
    """Map a REST path to the documented Dhan limit bucket."""
    p = path if path.startswith("/") else f"/{path}"
    if p in {endpoints.OPTION_CHAIN, endpoints.OPTION_CHAIN_EXPIRY_LIST}:
        return "option_chain"
    if p in {
        endpoints.MARKETFEED_LTP,
        endpoints.MARKETFEED_OHLC,
        endpoints.MARKETFEED_QUOTE,
    }:
        return "quote"
    if p in {
        endpoints.CHARTS_HISTORICAL,
        endpoints.CHARTS_INTRADAY,
        endpoints.CHARTS_ROLLING_OPTION,
    }:
        return "data"
    return "non_trading"


def min_interval_s(bucket: str) -> float:
    if bucket == "option_chain":
        return float(endpoints.RATE_LIMIT_OPTION_CHAIN_SECONDS)
    if bucket == "quote":
        return 1.0 / float(endpoints.RATE_LIMIT_QUOTE_PER_SEC)
    if bucket == "data":
        return 1.0 / float(endpoints.RATE_LIMIT_DATA_PER_SEC)
    return 1.0 / float(endpoints.RATE_LIMIT_NON_TRADING_PER_SEC)


def is_rate_limit_error(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    code = str(getattr(exc, "error_code", None) or "")
    if code in _RATE_CODES:
        return True
    return "too many requests" in str(exc).lower()


class MinIntervalGate:
    """Serialize calls so ``seconds`` elapse between ``wait()`` returns.

    Live option-chain REST is 1 unique request / 3 s. Skip this gate in
    dry-run (no HTTP). ROOM TO EDIT: jitter, per-underlying keys.
    """

    def __init__(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("seconds must be >= 0")
        self.seconds = float(seconds)
        self._lock = threading.Lock()
        self._last_monotonic = 0.0

    def wait(self) -> float:
        """Block until the interval has elapsed. Returns seconds slept."""
        with self._lock:
            now = time.monotonic()
            elapsed = (
                now - self._last_monotonic if self._last_monotonic else self.seconds
            )
            sleep_for = max(0.0, self.seconds - elapsed)
            if sleep_for:
                time.sleep(sleep_for)
            self._last_monotonic = time.monotonic()
            return sleep_for


class _Bucket:
    last_call_mono: float = 0.0
    backoff_until_mono: float = 0.0
    streak: int = 0
    hits: int = 0
    last_hit_mono: float = 0.0


class EndpointRateLimiter:
    """Process-wide per-bucket limiter: documented interval + 429/805 backoff."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        backoff_start_s: float = RATE_LIMIT_429_BACKOFF_START_S,
        backoff_cap_s: float = RATE_LIMIT_429_BACKOFF_CAP_S,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self.backoff_start_s = float(backoff_start_s)
        self.backoff_cap_s = float(backoff_cap_s)
        self._lock = threading.Lock()
        self._buckets: dict[str, _Bucket] = {}

    def _state(self, path: str) -> _Bucket:
        key = bucket_for(path)
        st = self._buckets.get(key)
        if st is None:
            st = _Bucket()
            self._buckets[key] = st
        return st

    def remaining_s(self, path: str) -> float:
        with self._lock:
            return self._remaining_unlocked(path)

    def _remaining_unlocked(self, path: str) -> float:
        st = self._state(path)
        now = self._clock()
        interval = min_interval_s(bucket_for(path))
        since = (now - st.last_call_mono) if st.last_call_mono else interval
        wait_interval = max(0.0, interval - since)
        wait_backoff = max(0.0, st.backoff_until_mono - now)
        return max(wait_interval, wait_backoff)

    def acquire(self, path: str, *, block: bool = True) -> float:
        """Wait until the call is allowed. Returns seconds slept. Does not HTTP-retry."""
        with self._lock:
            wait_for = self._remaining_unlocked(path)
            if wait_for > 0:
                if not block:
                    return wait_for
                self._sleep(wait_for)
            self._state(path).last_call_mono = self._clock()
            return wait_for

    def note_success(self, path: str) -> None:
        with self._lock:
            self._state(path).streak = 0

    def note_rate_limit(self, path: str) -> float:
        """Record a 429/805. Log once per backoff. Returns backoff seconds."""
        with self._lock:
            st = self._state(path)
            now = self._clock()
            if (
                st.hits
                and now - st.last_hit_mono < 0.05
                and now < st.backoff_until_mono
            ):
                return max(0.0, st.backoff_until_mono - now)
            st.hits += 1
            st.streak += 1
            st.last_hit_mono = now
            delay = min(
                self.backoff_start_s * (2 ** (st.streak - 1)), self.backoff_cap_s
            )
            st.backoff_until_mono = now + delay
            log.warning(
                "REST %s rate-limited (429/805); backing off %.0fs (hit %d)",
                bucket_for(path),
                delay,
                st.hits,
            )
            return float(delay)

    def hits(self, path: str | None = None) -> int:
        with self._lock:
            if path is None:
                return sum(st.hits for st in self._buckets.values())
            return self._state(path).hits


_DEFAULT: EndpointRateLimiter | None = None
_DEFAULT_LOCK = threading.Lock()


def default_limiter() -> EndpointRateLimiter:
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = EndpointRateLimiter()
        return _DEFAULT


def reset_default_limiter(
    limiter: EndpointRateLimiter | None = None,
) -> EndpointRateLimiter:
    """Replace the process limiter (tests)."""
    global _DEFAULT
    with _DEFAULT_LOCK:
        _DEFAULT = limiter if limiter is not None else EndpointRateLimiter()
        return _DEFAULT


def rate_limit_hits() -> int:
    return default_limiter().hits()


__all__ = [
    "RATE_LIMIT_429_BACKOFF_CAP_S",
    "RATE_LIMIT_429_BACKOFF_START_S",
    "EndpointRateLimiter",
    "MinIntervalGate",
    "bucket_for",
    "default_limiter",
    "is_rate_limit_error",
    "min_interval_s",
    "rate_limit_hits",
    "reset_default_limiter",
]

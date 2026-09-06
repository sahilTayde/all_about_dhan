"""Minimum-interval gates for documented DhanHQ rate limits.

Option chain: one unique request every 3 seconds
(https://dhanhq.co/docs/v2/option-chain/). Quote: 1 request/second.
"""

from __future__ import annotations

import threading
import time


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
            elapsed = now - self._last_monotonic if self._last_monotonic else self.seconds
            sleep_for = max(0.0, self.seconds - elapsed)
            if sleep_for:
                time.sleep(sleep_for)
            self._last_monotonic = time.monotonic()
            return sleep_for

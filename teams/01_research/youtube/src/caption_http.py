"""Shared timedtext HTTP client. Public captions only; never scrapes third-party sites.

YouTube Data API captions.download requires OAuth of the *owning* channel and
cannot fetch @DhanHQ caption text with an API key. This module uses the same
public timedtext/Innertube path as youtube-transcript-api, with a browser-like
User-Agent, delay, and exponential backoff on 429 / bot-detection blocks.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable, Optional, TypeVar

from requests import Session

from .sanitize import sanitize

log = logging.getLogger(__name__)

# Legitimate desktop Chrome UA. python-requests' default UA is a common bot signal.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

T = TypeVar("T")


def is_block_error(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    tokens = (
        "ipblocked",
        "requestblocked",
        "too many requests",
        "blocked",
        "sign in to confirm",
        "not a bot",
        "429",
    )
    return any(token in name or token in msg for token in tokens)


def build_session() -> Session:
    session = Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return session


def build_transcript_api() -> Any:
    from youtube_transcript_api import YouTubeTranscriptApi

    return YouTubeTranscriptApi(http_client=build_session())


def with_backoff(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 20.0,
    max_delay: float = 120.0,
    label: str = "timedtext",
) -> T:
    """Retry fn on IP/request blocks. Raises the last block error if all attempts fail."""
    last: Optional[BaseException] = None
    tries = max(1, attempts)
    for i in range(tries):
        try:
            return fn()
        except Exception as exc:
            if not is_block_error(exc):
                raise
            last = exc
            if i + 1 >= tries:
                break
            delay = min(base_delay * (2**i), max_delay)
            delay += random.uniform(0, min(5.0, delay * 0.1))
            log.warning(
                "%s blocked (%s); backing off %.1fs (attempt %s/%s)",
                label,
                type(exc).__name__,
                delay,
                i + 1,
                tries,
            )
            time.sleep(delay)
    assert last is not None
    raise last


def list_transcripts(video_id: str) -> Any:
    """Return a TranscriptList (v1) or equivalent listing."""
    api = build_transcript_api()
    if hasattr(api, "list"):
        return api.list(video_id)
    from youtube_transcript_api import YouTubeTranscriptApi

    if hasattr(YouTubeTranscriptApi, "list_transcripts"):
        return YouTubeTranscriptApi.list_transcripts(video_id)
    raise RuntimeError("Unsupported youtube-transcript-api version.")


def track_inventory(listing: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        tracks = list(listing)
    except TypeError:
        return rows
    for track in tracks:
        rows.append(
            {
                "language_code": getattr(track, "language_code", None),
                "language": getattr(track, "language", None),
                "is_generated": getattr(track, "is_generated", None),
                "is_translatable": bool(getattr(track, "is_translatable", False)),
            }
        )
    return rows


def sanitize_block_message(exc: BaseException) -> str:
    return sanitize(str(exc))

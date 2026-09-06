"""YouTube Data API v3 client. Rate-limit aware. Never logs the API key."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Iterator, Optional

import requests

from .sanitize import sanitize

log = logging.getLogger(__name__)

BASE_URL = "https://www.googleapis.com/youtube/v3"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 4


class YouTubeApiError(Exception):
    def __init__(self, http_status: int, reason: str, message: str):
        self.http_status = http_status
        self.reason = reason
        self.message = message
        super().__init__(f"HTTP {http_status} {reason}: {message}")


def _error_reason(payload: Any, http_status: int) -> str:
    if not isinstance(payload, dict):
        return "unknown"
    err = payload.get("error") or {}
    errors = err.get("errors") or []
    if errors and isinstance(errors, list):
        reason = errors[0].get("reason")
        if reason:
            return str(reason)
    status = err.get("status")
    if status:
        return str(status)
    return f"http_{http_status}"


def _error_message(payload: Any, fallback: str, secret: str) -> str:
    if isinstance(payload, dict):
        err = payload.get("error") or {}
        msg = err.get("message")
        if msg:
            return sanitize(str(msg), secret)
    return sanitize(fallback, secret)


class YouTubeClient:
    def __init__(self, api_key: str, pause_seconds: float = 0.2):
        self._key = api_key
        self._pause = pause_seconds
        self.quota_units_used = 0
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "all-about-dhan-research/0.1"}
        )

    def close(self) -> None:
        self.session.close()

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        query = dict(params)
        query["key"] = self._key
        url = f"{BASE_URL}/{endpoint}"
        last_error: Optional[YouTubeApiError] = None
        for attempt in range(MAX_RETRIES):
            if attempt:
                sleep_for = min(2 ** attempt, 16)
                log.info("Retrying %s after %.1fs (attempt %s)", endpoint, sleep_for, attempt + 1)
                time.sleep(sleep_for)
            try:
                response = self.session.get(url, params=query, timeout=DEFAULT_TIMEOUT)
            except requests.RequestException as exc:
                last_error = YouTubeApiError(
                    0, "network_error", sanitize(str(exc), self._key)
                )
                continue

            self.quota_units_used += 1
            time.sleep(self._pause)

            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    raise YouTubeApiError(
                        response.status_code,
                        "invalid_json",
                        "Response was not JSON.",
                    )

            payload: Any
            try:
                payload = response.json()
            except json.JSONDecodeError:
                payload = {}
            reason = _error_reason(payload, response.status_code)
            message = _error_message(payload, response.text[:300], self._key)

            if response.status_code in (429, 500, 502, 503, 504):
                last_error = YouTubeApiError(response.status_code, reason, message)
                continue
            if response.status_code == 403 and reason in (
                "quotaExceeded",
                "dailyLimitExceeded",
                "rateLimitExceeded",
                "userRateLimitExceeded",
            ):
                raise YouTubeApiError(response.status_code, reason, message)

            raise YouTubeApiError(response.status_code, reason, message)

        assert last_error is not None
        raise last_error

    def paginate(
        self, endpoint: str, params: dict[str, Any]
    ) -> Iterator[dict[str, Any]]:
        page_params = dict(params)
        while True:
            data = self._get(endpoint, page_params)
            yield data
            token = data.get("nextPageToken")
            if not token:
                return
            page_params["pageToken"] = token

    def channels_by_handle(self, handle: str) -> dict[str, Any]:
        handle = handle.lstrip("@")
        data = self._get(
            "channels",
            {
                "part": "id,snippet,contentDetails,statistics",
                "forHandle": handle,
            },
        )
        items = data.get("items") or []
        if not items:
            raise YouTubeApiError(
                200,
                "channel_not_found",
                f"No channel returned for handle {handle}.",
            )
        return items[0]

    def list_playlists(self, channel_id: str) -> list[dict[str, Any]]:
        playlists: list[dict[str, Any]] = []
        for page in self.paginate(
            "playlists",
            {
                "part": "id,snippet,contentDetails",
                "channelId": channel_id,
                "maxResults": 50,
            },
        ):
            playlists.extend(page.get("items") or [])
        return playlists

    def list_playlist_items(self, playlist_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for page in self.paginate(
            "playlistItems",
            {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            },
        ):
            items.extend(page.get("items") or [])
        return items

    def videos_by_ids(self, video_ids: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        chunk_size = 50
        for i in range(0, len(video_ids), chunk_size):
            chunk = video_ids[i : i + chunk_size]
            if not chunk:
                continue
            data = self._get(
                "videos",
                {
                    "part": "snippet,contentDetails,statistics,status",
                    "id": ",".join(chunk),
                    "maxResults": 50,
                },
            )
            out.extend(data.get("items") or [])
        return out

    def captions_list(self, video_id: str) -> dict[str, Any]:
        """Data API captions.list. API key can list tracks; download still needs OAuth."""
        return self._get(
            "captions",
            {
                "part": "id,snippet",
                "videoId": video_id,
            },
        )

    def captions_download(self, caption_id: str) -> tuple[int, str]:
        """GET captions.download. API keys are not accepted; records status only.

        Returns (http_status, sanitized_reason). Never logs the key.
        """
        url = f"{BASE_URL}/captions/{caption_id}"
        try:
            response = self.session.get(
                url,
                params={"key": self._key, "tfmt": "srt"},
                timeout=DEFAULT_TIMEOUT,
            )
        except Exception as exc:
            return 0, sanitize(str(exc), self._key)
        reason = "ok"
        try:
            payload = response.json()
            reason = _error_reason(payload, response.status_code)
        except json.JSONDecodeError:
            reason = f"http_{response.status_code}"
        return response.status_code, sanitize(reason, self._key)

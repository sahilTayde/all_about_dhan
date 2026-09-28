"""Thin HTTP wrapper around documented DhanHQ v2 REST paths.

Headers follow the quote / option-chain pages: ``access-token`` and ``client-id``.
Historical and profile curls on the docs site omit ``client-id`` — we still send
both; VERIFY FROM DOCS if a call fails with DH-905.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from dhan_client.config import Settings
from dhan_client.errors import DhanApiError
from dhan_client.logging_util import get_logger, redact_mapping, redact_url
from dhan_client.rate_limit import (
    EndpointRateLimiter,
    default_limiter,
    is_rate_limit_error,
)

log = get_logger(__name__)


def dry_run_envelope(method: str, path: str, body: Any = None) -> dict[str, Any]:
    return {
        "status": "dry_run",
        "method": method,
        "path": path,
        "request": body,
        "data": None,
        "note": (
            "No HTTP call. Fill DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in "
            "repo-root .env for live requests."
        ),
    }


class RestClient:
    def __init__(
        self,
        settings: Settings,
        *,
        timeout: float = 180.0,
        limiter: EndpointRateLimiter | None = None,
    ) -> None:
        self.settings = settings
        self._timeout = timeout
        self._http: httpx.Client | None = None
        self._limiter = limiter if limiter is not None else default_limiter()

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    def __enter__(self) -> RestClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=self._timeout)
        return self._http

    def _headers(self) -> dict[str, str]:
        creds = self.settings.require_live()
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": creds.access_token,
            "client-id": creds.client_id,
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        extra_headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        path = path if path.startswith("/") else f"/{path}"
        if self.settings.dry_run:
            log.info("dry-run REST %s %s", method.upper(), path)
            return dry_run_envelope(method.upper(), path, json_body)

        self._limiter.acquire(path)
        url = f"{self.settings.api_base.rstrip('/')}{path}"
        headers = self._headers()
        if extra_headers:
            headers.update(dict(extra_headers))

        log.info("REST %s %s", method.upper(), redact_url(url))
        try:
            response = self._client().request(
                method.upper(),
                url,
                headers=headers,
                json=json_body,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise DhanApiError(f"network error calling {path}") from exc

        try:
            parsed = self._parse_response(path, response)
        except DhanApiError as exc:
            if is_rate_limit_error(exc):
                self._limiter.note_rate_limit(path)
            raise
        self._limiter.note_success(path)
        return parsed

    def get_public(self, url: str) -> httpx.Response:
        """Unauthenticated GET (scrip-master CSVs on images.dhan.co)."""
        if self.settings.dry_run:
            raise DhanApiError("dry-run: public GET skipped")
        log.info("GET %s", redact_url(url))
        try:
            return self._client().get(url)
        except httpx.HTTPError as exc:
            raise DhanApiError("network error on public GET") from exc

    def _parse_response(self, path: str, response: httpx.Response) -> dict[str, Any]:
        try:
            payload: Any = response.json()
        except ValueError:
            payload = None

        if response.is_success:
            if isinstance(payload, dict):
                return payload
            return {"status": "success", "data": payload}

        error_type = error_code = None
        message = f"HTTP {response.status_code} from {path}"
        if isinstance(payload, dict):
            # Documented error shape: errorType, errorCode, errorMessage.
            # Live 429 also arrives as {'805': 'Too many requests. ...'}.
            error_type = payload.get("errorType")
            error_code = payload.get("errorCode")
            err_msg = payload.get("errorMessage")
            if error_code is None:
                for key, value in payload.items():
                    if str(key) in {"805", "429"}:
                        error_code = str(key)
                        if err_msg is None:
                            err_msg = value
                        break
            if err_msg:
                message = str(err_msg)
            else:
                message = f"HTTP {response.status_code} from {path}"
            log.info(
                "REST error path=%s status=%s body=%s",
                path,
                response.status_code,
                redact_mapping(payload),
            )
        raise DhanApiError(
            message,
            status_code=response.status_code,
            error_type=str(error_type) if error_type else None,
            error_code=str(error_code) if error_code else None,
        )

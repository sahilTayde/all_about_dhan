"""OpenAI helper with honest fallbacks. Never print API keys.

Shared cooldown file lets respawned market-hours PIDs inherit RateLimit backoff
(P0-4 / P2-4 process fix 2026-09-07). Never logs secrets.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

# Temporary rule-fallback window after rate-limit (seconds). Retry LLM when elapsed.
_RATE_LIMIT_COOLDOWN_UNTIL: float = 0.0
_RATE_LIMIT_BACKOFF_BASE = 30.0
_RATE_LIMIT_BACKOFF_CAP = 300.0
_rate_limit_strikes = 0

# Transient connection cooldown — avoid burning a whole tick on N agents × retries.
_CONN_COOLDOWN_UNTIL: float = 0.0
_CONN_BACKOFF_BASE = 20.0
_CONN_BACKOFF_CAP = 120.0
_conn_strikes = 0

# In-call retries for transient transport / 5xx (founder: if failing, hit again).
_TRANSIENT_RETRIES = 2
_TRANSIENT_BACKOFF_BASE = 1.0
_OPENAI_TIMEOUT_S = 20.0

# Cross-process cooldown (survives ops-monitor respawns).
_SHARED_COOLDOWN_ENV = "TAI_LLM_COOLDOWN_PATH"
_DEFAULT_COOLDOWN_REL = Path("data/recon/llm_cooldown.json")


def _shared_cooldown_path() -> Path:
    raw = (os.getenv(_SHARED_COOLDOWN_ENV) or "").strip()
    if raw:
        return Path(raw)
    # Prefer repo-relative from CWD; fall back to /tmp.
    cand = Path.cwd() / _DEFAULT_COOLDOWN_REL
    try:
        cand.parent.mkdir(parents=True, exist_ok=True)
        return cand
    except OSError:
        return Path("/tmp/tai_llm_cooldown.json")


def _read_shared_cooldown() -> dict[str, Any]:
    path = _shared_cooldown_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_shared_cooldown(payload: dict[str, Any]) -> None:
    path = _shared_cooldown_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _sync_from_shared() -> None:
    """Pull disk cooldown into process globals (respawn-safe)."""
    global _RATE_LIMIT_COOLDOWN_UNTIL, _rate_limit_strikes
    global _CONN_COOLDOWN_UNTIL, _conn_strikes
    blob = _read_shared_cooldown()
    now = time.time()
    rl_until = float(blob.get("rate_limit_until") or 0.0)
    cn_until = float(blob.get("conn_until") or 0.0)
    if rl_until > _RATE_LIMIT_COOLDOWN_UNTIL:
        _RATE_LIMIT_COOLDOWN_UNTIL = rl_until
        _rate_limit_strikes = max(_rate_limit_strikes, int(blob.get("rate_limit_strikes") or 0))
    if cn_until > _CONN_COOLDOWN_UNTIL:
        _CONN_COOLDOWN_UNTIL = cn_until
        _conn_strikes = max(_conn_strikes, int(blob.get("conn_strikes") or 0))
    # Drop expired keys quietly
    if rl_until and rl_until < now and cn_until < now:
        pass


def _persist_shared() -> None:
    _write_shared_cooldown(
        {
            "rate_limit_until": _RATE_LIMIT_COOLDOWN_UNTIL,
            "rate_limit_strikes": _rate_limit_strikes,
            "conn_until": _CONN_COOLDOWN_UNTIL,
            "conn_strikes": _conn_strikes,
            "updated_at": time.time(),
            "note": "Shared LLM cooldown — no secrets",
        }
    )


def uses_max_completion_tokens(model: str) -> bool:
    """True for gpt-6 / astra / o-series models that reject max_tokens and/or temperature."""
    m = (model or "").strip().lower()
    if not m:
        return False
    if "astra" in m or "gpt-6" in m:
        return True
    # o1 / o3 / o4 reasoning-style ids (o1, o1-mini, o3-mini, …)
    if re.match(r"^o[0-9]", m):
        return True
    return False


def build_chat_completion_params(
    model: str,
    *,
    max_tokens: int,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Model-aware chat.completions.create kwargs (excluding messages / response_format).

    gpt-6-astra and o-series: max_completion_tokens, no temperature.
    gpt-4o / gpt-5.4 and peers: temperature + max_tokens (existing behavior).
    """
    params: dict[str, Any] = {"model": model}
    if uses_max_completion_tokens(model):
        params["max_completion_tokens"] = max_tokens
    else:
        params["temperature"] = temperature
        params["max_tokens"] = max_tokens
    return params


class LlmClient:
    """Thin wrapper. If key or package missing → DATA_INSUFFICIENT path."""

    def __init__(self, model: str, enabled: bool = True) -> None:
        self.model = model
        self._key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()
        self.enabled = bool(enabled and self._key and len(self._key) > 8)
        self._client = None
        self.last_error: Optional[str] = None
        self.success_count = 0
        self.fail_count = 0
        self.skip_all = False  # set by pipeline on big-news / closed calendar
        self.call_count = 0
        self.max_calls_per_tick = int(os.getenv("TAI_LLM_MAX_CALLS_PER_TICK") or "6")
        _sync_from_shared()
        if self.enabled:
            try:
                from openai import OpenAI  # type: ignore

                # Bound waits so a dead socket cannot stall the whole market-hours tick.
                # max_retries=0: we own transient backoff in complete_json.
                self._client = OpenAI(
                    api_key=self._key,
                    timeout=_OPENAI_TIMEOUT_S,
                    max_retries=0,
                )
            except Exception as exc:  # noqa: BLE001 — honest fallback
                self.enabled = False
                self.last_error = f"openai_import_or_init: {type(exc).__name__}"
                self._client = None

    @property
    def key_present(self) -> bool:
        return bool(self._key and len(self._key) > 8)

    @property
    def last_error_class(self) -> Optional[str]:
        """Exception class / short class label only — never secrets."""
        if not self.last_error:
            return None
        # Strip any accidental payload; keep ClassName or openai_import_or_init:Name
        m = re.match(r"^(openai_import_or_init:\s*)?([A-Za-z_][A-Za-z0-9_]*)$", self.last_error)
        if m:
            return self.last_error
        return re.split(r"[:\s]", self.last_error, maxsplit=1)[0] or "UnknownError"

    def _in_rate_limit_cooldown(self) -> bool:
        return time.time() < _RATE_LIMIT_COOLDOWN_UNTIL

    def _in_conn_cooldown(self) -> bool:
        return time.time() < _CONN_COOLDOWN_UNTIL

    def _mark_rate_limited(self) -> float:
        global _RATE_LIMIT_COOLDOWN_UNTIL, _rate_limit_strikes
        _sync_from_shared()
        _rate_limit_strikes += 1
        delay = min(
            _RATE_LIMIT_BACKOFF_CAP,
            _RATE_LIMIT_BACKOFF_BASE * (2 ** min(_rate_limit_strikes - 1, 4)),
        )
        new_until = time.time() + delay
        # Keep the later of local-new vs any concurrent shared mark.
        _RATE_LIMIT_COOLDOWN_UNTIL = max(_RATE_LIMIT_COOLDOWN_UNTIL, new_until)
        _persist_shared()
        return max(0.0, _RATE_LIMIT_COOLDOWN_UNTIL - time.time())

    def _mark_conn_failed(self) -> float:
        global _CONN_COOLDOWN_UNTIL, _conn_strikes
        _sync_from_shared()
        _conn_strikes += 1
        delay = min(
            _CONN_BACKOFF_CAP,
            _CONN_BACKOFF_BASE * (2 ** min(_conn_strikes - 1, 3)),
        )
        new_until = time.time() + delay
        _CONN_COOLDOWN_UNTIL = max(_CONN_COOLDOWN_UNTIL, new_until)
        _persist_shared()
        return max(0.0, _CONN_COOLDOWN_UNTIL - time.time())

    def _clear_rate_limit(self) -> None:
        """Clear local RL cooldown without wiping a fresher shared mark (respawn race)."""
        global _RATE_LIMIT_COOLDOWN_UNTIL, _rate_limit_strikes
        blob = _read_shared_cooldown()
        shared_until = float(blob.get("rate_limit_until") or 0.0)
        # Another process extended cooldown after our call started — keep it.
        if shared_until > _RATE_LIMIT_COOLDOWN_UNTIL + 0.5:
            _sync_from_shared()
            return
        _RATE_LIMIT_COOLDOWN_UNTIL = 0.0
        _rate_limit_strikes = 0
        _persist_shared()

    def _clear_conn_cooldown(self) -> None:
        """Clear local conn cooldown without wiping a fresher shared mark."""
        global _CONN_COOLDOWN_UNTIL, _conn_strikes
        blob = _read_shared_cooldown()
        shared_until = float(blob.get("conn_until") or 0.0)
        if shared_until > _CONN_COOLDOWN_UNTIL + 0.5:
            _sync_from_shared()
            return
        _CONN_COOLDOWN_UNTIL = 0.0
        _conn_strikes = 0
        _persist_shared()

    @staticmethod
    def _is_rate_limit_error(exc: BaseException) -> bool:
        name = type(exc).__name__.lower()
        msg = str(exc).lower()
        if "ratelimit" in name or "rate_limit" in name:
            return True
        if "429" in msg or "rate limit" in msg or "too many requests" in msg:
            return True
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        return status == 429

    @staticmethod
    def _is_transient_error(exc: BaseException) -> bool:
        name = type(exc).__name__.lower()
        msg = str(exc).lower()
        if LlmClient._is_rate_limit_error(exc):
            return False  # handled via cooldown path, not tight retry
        if any(
            tok in name
            for tok in (
                "apiconnection",
                "timeout",
                "apitimeout",
                "internalserver",
                "serviceunavailable",
                "connection",
            )
        ):
            return True
        if any(
            tok in msg
            for tok in (
                "connection",
                "timed out",
                "timeout",
                "temporarily unavailable",
                "503",
                "502",
                "504",
            )
        ):
            return True
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        return status in (408, 500, 502, 503, 504)

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 700,
    ) -> tuple[Optional[dict[str, Any]], list[str]]:
        """Return (parsed_dict_or_None, data_gaps).

        gpt-6 / astra / o-series spend completion budget on reasoning — bump floor
        so visible JSON is not truncated to empty ``finish_reason=length``.

        On rate limit: temporary rule fallback with exponential backoff; retry LLM
        when the cooldown window elapses (founder-authorized ~$10 budget path).

        On transient connection/5xx: short in-call retries with backoff, then DI.
        """
        global _RATE_LIMIT_COOLDOWN_UNTIL  # noqa: PLW0603 — process-local cooldown
        gaps: list[str] = []
        _sync_from_shared()
        if self.skip_all:
            gaps.append(
                "DATA_INSUFFICIENT: LLM skipped this tick (big-news veto / calendar / budget)"
            )
            self.last_error = "SkipAll"
            return None, gaps
        if not self.enabled or self._client is None:
            gaps.append(
                "DATA_INSUFFICIENT: OPENAI_API_KEY missing or openai package not installed — rule fallback"
            )
            if self.last_error:
                gaps.append(f"UNKNOWN: {self.last_error}")
            return None, gaps
        if self.call_count >= self.max_calls_per_tick:
            gaps.append(
                f"DATA_INSUFFICIENT: LLM tick budget exhausted "
                f"({self.max_calls_per_tick} calls) — rule fallback"
            )
            self.last_error = "TickBudget"
            return None, gaps
        if self._in_rate_limit_cooldown():
            remaining = max(0.0, _RATE_LIMIT_COOLDOWN_UNTIL - time.time())
            gaps.append(
                f"DATA_INSUFFICIENT: OpenAI rate-limit cooldown "
                f"({remaining:.0f}s remaining) — temporary rule fallback; will retry LLM"
            )
            self.last_error = "RateLimitCooldown"
            return None, gaps
        if self._in_conn_cooldown():
            remaining = max(0.0, _CONN_COOLDOWN_UNTIL - time.time())
            gaps.append(
                f"DATA_INSUFFICIENT: OpenAI connection cooldown "
                f"({remaining:.0f}s remaining) — temporary rule fallback; will retry LLM"
            )
            self.last_error = "APIConnectionCooldown"
            return None, gaps
        budget = int(max_tokens)
        if uses_max_completion_tokens(self.model):
            budget = max(budget, 4000)
        params = build_chat_completion_params(self.model, max_tokens=budget)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        last_exc: Optional[BaseException] = None
        for attempt in range(_TRANSIENT_RETRIES):
            try:
                self.call_count += 1
                resp = self._client.chat.completions.create(
                    **params,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
                text = (resp.choices[0].message.content or "").strip()
                if not text:
                    gaps.append(
                        "DATA_INSUFFICIENT: OpenAI returned empty content "
                        f"(finish may be length; model={self.model})"
                    )
                    self.last_error = "EmptyContent"
                    self.fail_count += 1
                    return None, gaps
                parsed = extract_json_object(text)
                if parsed is None:
                    gaps.append(
                        "DATA_INSUFFICIENT: OpenAI content was not valid JSON object"
                    )
                    self.last_error = "InvalidJson"
                    self.fail_count += 1
                    return None, gaps
                self._clear_rate_limit()
                self._clear_conn_cooldown()
                self.last_error = None
                self.success_count += 1
                return parsed, gaps
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if self._is_rate_limit_error(exc):
                    delay = self._mark_rate_limited()
                    gaps.append(
                        f"DATA_INSUFFICIENT: OpenAI rate-limited ({type(exc).__name__}); "
                        f"temporary rule fallback for {delay:.0f}s then retry"
                    )
                    self.last_error = "RateLimitError"
                    self.fail_count += 1
                    return None, gaps
                if self._is_transient_error(exc) and attempt + 1 < _TRANSIENT_RETRIES:
                    time.sleep(_TRANSIENT_BACKOFF_BASE * (2**attempt))
                    continue
                if self._is_transient_error(exc):
                    delay = self._mark_conn_failed()
                    gaps.append(
                        f"DATA_INSUFFICIENT: OpenAI call failed ({type(exc).__name__}); "
                        f"temporary rule fallback for {delay:.0f}s then retry"
                    )
                    self.last_error = type(exc).__name__
                    self.fail_count += 1
                    return None, gaps
                gaps.append(
                    f"DATA_INSUFFICIENT: OpenAI call failed ({type(exc).__name__})"
                )
                self.last_error = type(exc).__name__
                self.fail_count += 1
                return None, gaps
        # Unreachable, but keep honest fallback if loop exits oddly.
        name = type(last_exc).__name__ if last_exc else "UnknownError"
        gaps.append(f"DATA_INSUFFICIENT: OpenAI call failed ({name})")
        self.last_error = name
        self.fail_count += 1
        return None, gaps


_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> Optional[dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_FENCE.search(text)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

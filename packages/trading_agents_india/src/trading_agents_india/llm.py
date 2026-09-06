"""OpenAI helper with honest fallbacks. Never print API keys."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional


class LlmClient:
    """Thin wrapper. If key or package missing → DATA_INSUFFICIENT path."""

    def __init__(self, model: str, enabled: bool = True) -> None:
        self.model = model
        self._key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()
        self.enabled = bool(enabled and self._key and len(self._key) > 8)
        self._client = None
        self.last_error: Optional[str] = None
        if self.enabled:
            try:
                from openai import OpenAI  # type: ignore

                self._client = OpenAI(api_key=self._key)
            except Exception as exc:  # noqa: BLE001 — honest fallback
                self.enabled = False
                self.last_error = f"openai_import_or_init: {type(exc).__name__}"
                self._client = None

    @property
    def key_present(self) -> bool:
        return bool(self._key and len(self._key) > 8)

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 700,
    ) -> tuple[Optional[dict[str, Any]], list[str]]:
        """Return (parsed_dict_or_None, data_gaps)."""
        gaps: list[str] = []
        if not self.enabled or self._client is None:
            gaps.append(
                "DATA_INSUFFICIENT: OPENAI_API_KEY missing or openai package not installed — rule fallback"
            )
            if self.last_error:
                gaps.append(f"UNKNOWN: {self.last_error}")
            return None, gaps
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
            return json.loads(text), gaps
        except Exception as exc:  # noqa: BLE001
            gaps.append(f"DATA_INSUFFICIENT: OpenAI call failed ({type(exc).__name__})")
            self.last_error = type(exc).__name__
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

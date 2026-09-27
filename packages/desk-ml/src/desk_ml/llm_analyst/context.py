"""Compact, scrubbed, hashable context for the LLM analyst. Pure functions; no I/O.

Everything the model sees passes through `scrub` (credential/account redaction) and every piece of
free text from outside the engine (news, pre-market notes) passes through `untrusted_text`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Iterable, Mapping, Optional, Sequence

CONTEXT_VERSION = 1
DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
REDACTED = "[REDACTED]"

MAX_NEWS_ITEMS = 8
MAX_NEWS_CHARS = 240
MAX_NOTE_CHARS = 400

# Key names (split on non-alphanumerics) that never reach a prompt or the log.
_SECRET_TOKENS = frozenset({
    "token", "secret", "password", "passwd", "pwd", "auth", "authorization", "otp", "pin", "totp",
    "account", "acct", "credential", "credentials", "apikey", "jwt", "cookie", "bearer", "dhan",
})
_SECRET_PAIRS = ({"api", "key"}, {"client", "id"}, {"access", "key"}, {"private", "key"}, {"session", "id"})
_SECRET_VALUE_RES = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),  # OpenAI-style keys
    re.compile(r"eyJ[\w\-]{6,}\.[\w\-]{6,}\.[\w\-]{6,}"),  # JWT (Dhan access tokens are JWTs)
    re.compile(r"\b(?:AIza|ya29\.)[\w\-]{12,}"),  # Google keys/tokens
    re.compile(r"\b\d{8,}\b"),  # account / client ids, phone numbers
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),  # long hex secrets
)
_ENV_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|CLIENT_ID|PIN", re.I)

# Instruction-shaped phrases stripped from news before it is quoted to the model.
_INJECTION_RES = (
    re.compile(r"(?i)\b(ignore|disregard|forget|override)\b[^.!?\n]{0,60}\b(instructions?|prompts?|rules?|above|previous|system)\b[^.!?\n]*"),
    re.compile(r"(?i)\b(you are|act as|pretend to be|roleplay as|from now on)\b[^.!?\n]*"),
    re.compile(r"(?i)\b(system|assistant|developer|user)\s*(prompt|message)?\s*[:>]"),
    re.compile(r"(?i)\b(respond|reply|answer|output|return|say|print)\b[^.!?\n]{0,40}\b(json|verdict|agree|disagree|abstain|only|exactly)\b[^.!?\n]*"),
    re.compile(r"(?i)\b(new|updated|real)\s+instructions?\b[^.!?\n]*"),
    re.compile(r"(?i)\b(api[_ ]?key|password|token|credentials?)\b[^.!?\n]*"),
)
_TAG_RE = re.compile(r"<[^>]{0,200}>|\[/?(?:INST|SYS|system|assistant|user)[^\]]{0,40}\]", re.I)
_FENCE_RE = re.compile(r"`{3,}|~{3,}")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
_BRACES_RE = re.compile(r"[{}]")


def untrusted_text(raw: Any, *, limit: int = MAX_NEWS_CHARS) -> str:
    """News / notes as inert data: no controls, tags, fences, URLs, braces or instruction phrases."""
    text = _CTRL_RE.sub(" ", str(raw or ""))
    text = _TAG_RE.sub(" ", text)
    text = _FENCE_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    for rx in _INJECTION_RES:
        text = rx.sub(" [removed] ", text)
    text = _BRACES_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(\[removed\]\s*)+", "[removed] ", text).strip()
    return text[:limit]


def _secret_key(name: str) -> bool:
    toks = set(t for t in re.split(r"[^a-z0-9]+", str(name).lower()) if t)
    return bool(toks & _SECRET_TOKENS) or any(pair <= toks for pair in _SECRET_PAIRS)


_ENV_STAMP: Optional[tuple[Any, ...]] = None
_ENV_VALS: tuple[str, ...] = ()


def _env_secret_values() -> tuple[str, ...]:
    """Secret-shaped env values. Recomputed only when the environment changes."""
    global _ENV_STAMP, _ENV_VALS
    try:
        stamp = (len(os.environ), hash(tuple(os.environ.values())))
    except TypeError:
        stamp = None
    if stamp is not None and stamp == _ENV_STAMP:
        return _ENV_VALS
    vals = tuple(v for k, v in os.environ.items() if _ENV_SECRET_NAME.search(k) and v and len(v.strip()) >= 8)
    if stamp is not None:
        _ENV_STAMP, _ENV_VALS = stamp, vals
    return vals


def _scrub_str(s: str, env_vals: Sequence[str]) -> str:
    for val in env_vals:
        if val in s:
            s = s.replace(val, REDACTED)
    for rx in _SECRET_VALUE_RES:
        s = rx.sub(REDACTED, s)
    return s


def scrub(obj: Any, _env: Optional[Sequence[str]] = None) -> Any:
    """Drop credential/account-shaped keys and redact secret-shaped strings, recursively."""
    env_vals = _env_secret_values() if _env is None else _env
    if isinstance(obj, Mapping):
        return {str(k): scrub(v, env_vals) for k, v in obj.items() if not _secret_key(str(k))}
    if isinstance(obj, (list, tuple)):
        return [scrub(v, env_vals) for v in obj]
    if isinstance(obj, str):
        return _scrub_str(obj, env_vals)
    return obj


def canonical(obj: Any) -> Any:
    """Round floats (2 dp) so float noise does not change the hash; drop None."""
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, float):
        return round(obj, 2) if obj == obj else None
    if isinstance(obj, Mapping):
        return {str(k): canonical(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0])) if v is not None}
    if isinstance(obj, (list, tuple)):
        return [canonical(v) for v in obj]
    return obj


def dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def context_hash(ctx: Mapping[str, Any]) -> str:
    return hashlib.sha256(dumps(ctx).encode("utf-8")).hexdigest()[:20]


def _num(raw: Any) -> Optional[float]:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _pick(src: Any, keys: Iterable[str]) -> dict[str, Any]:
    src = src if isinstance(src, Mapping) else {}
    return {k: src[k] for k in keys if src.get(k) is not None and not isinstance(src.get(k), (dict, list))}


def premarket_block(brief: Any) -> Optional[dict[str, Any]]:
    """Pre-market brief (desk_intel PRE_MARKET payload or `{premarket: ...}`) -> sanitized data."""
    if not isinstance(brief, Mapping):
        return None
    pm = brief.get("premarket") if isinstance(brief.get("premarket"), Mapping) else brief
    note = pm.get("regime_note") or brief.get("regime_note")
    news_raw = pm.get("news") or brief.get("news") or pm.get("headlines") or brief.get("headlines") or []
    news: list[str] = []
    for item in news_raw if isinstance(news_raw, list) else []:
        text = item.get("title") or item.get("headline") or item.get("text") if isinstance(item, Mapping) else item
        clean = untrusted_text(text)
        if clean:
            news.append(clean)
        if len(news) >= MAX_NEWS_ITEMS:
            break
    out: dict[str, Any] = {}
    if note:
        out["regime_note_untrusted"] = untrusted_text(note, limit=MAX_NOTE_CHARS)
    if news:
        out["news_untrusted"] = news
    missing = pm.get("missing") or brief.get("tape_missing")
    if isinstance(missing, list):
        out["missing"] = [untrusted_text(m, limit=40) for m in missing[:6]]
    return out or None


def intermarket_block(brief: Any) -> Any:
    im = brief.get("intermarket") if isinstance(brief, Mapping) else None
    if not isinstance(im, Mapping):
        return DATA_INSUFFICIENT
    out: dict[str, Any] = {}
    for k, v in list(im.items())[:12]:
        name = untrusted_text(k, limit=32)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[name] = float(v)
        elif isinstance(v, str):
            out[name] = untrusted_text(v, limit=48)
    return out or DATA_INSUFFICIENT


def build_context(
    *,
    underlying: str,
    tick_ts: int,
    ist_time: Optional[str] = None,
    signal: Mapping[str, Any],
    regime: Optional[Mapping[str, Any]] = None,
    levels: Optional[Mapping[str, Any]] = None,
    chain: Any = None,
    book: Optional[Mapping[str, Any]] = None,
    expiry: Any = None,
    vol: Optional[Mapping[str, Any]] = None,
    brief: Any = None,
) -> dict[str, Any]:
    """The one compact context. Whitelisted fields only, scrubbed, canonical (hash-stable)."""
    sig = dict(signal)
    ctx = {
        "v": CONTEXT_VERSION,
        "underlying": str(underlying).upper(),
        "tick_ts": int(tick_ts),
        "ist_time": ist_time,
        "signal": {
            "side": sig.get("side"),
            "strike": _num(sig.get("strike")),
            "confidence": _num(sig.get("confidence")),
            "votes": _pick(sig.get("votes"), ("CE", "PE", "silent")),
            "voters": {str(k): v for k, v in dict(sig.get("voters") or {}).items() if v in ("CE", "PE")},
            "picker_detail": sig.get("picker_detail"),
        },
        "regime": _pick(regime, ("regime", "direction", "reason", "er", "rsi", "vwap", "ema", "range_over_atr", "flip_frac"))
        or DATA_INSUFFICIENT,
        "levels": dict(levels) if levels else DATA_INSUFFICIENT,
        "chain_oi": chain if chain else DATA_INSUFFICIENT,
        "intermarket": intermarket_block(brief),
        "premarket": premarket_block(brief) or DATA_INSUFFICIENT,
        "book": dict(book) if book else DATA_INSUFFICIENT,
        "expiry": expiry if expiry is not None else DATA_INSUFFICIENT,
        "vol": _pick(vol, ("rv30", "rng60_atr", "chasing", "high_vol")) or DATA_INSUFFICIENT,
    }
    return canonical(scrub(ctx))

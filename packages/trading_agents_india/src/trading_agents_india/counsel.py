"""Cheap dual-provider counsel: Gemini Flash-Lite first, OpenAI nano fallback.

Uses .env names only. Never prints keys. Not a live order path.
Web scrape is out of scope — pass cited facts in; this module reasons on them.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Optional

from trading_agents_india.config import load_settings

_CTX = ssl.create_default_context()
_TIMEOUT = 25

ROLES = ("reason", "validate", "review", "confirm", "counsel")


def _gemini_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or "").strip()


def _openai_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()


def counsel_settings() -> dict[str, Any]:
    load_settings()
    return {
        "provider": (os.getenv("COUNSEL_PROVIDER") or "both").strip().lower(),
        "gemini_model": (os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite").strip(),
        "openai_model": (os.getenv("OPENAI_MODEL") or "gpt-5.4-nano").strip(),
        "gemini_key_present": len(_gemini_key()) > 8,
        "openai_key_present": len(_openai_key()) > 8,
    }


def _http(method: str, url: str, *, headers: Optional[dict[str, str]] = None, body: Optional[bytes] = None) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_CTX) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:800]
    except Exception as exc:  # noqa: BLE001
        return 0, type(exc).__name__


def _complete_gemini(prompt: str, model: str) -> dict[str, Any]:
    key = _gemini_key()
    if len(key) <= 8:
        return {"ok": False, "gap": "DATA_INSUFFICIENT: GEMINI_KEY missing"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    code, raw = _http("POST", url, headers={"Content-Type": "application/json"}, body=payload)
    if code != 200:
        return {"ok": False, "gap": f"DATA_INSUFFICIENT: gemini HTTP {code}"}
    try:
        blob = json.loads(raw)
        text = blob["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {"ok": False, "gap": "DATA_INSUFFICIENT: gemini empty/unparsed"}
    return {"ok": True, "text": str(text).strip(), "provider": "gemini", "model": model}


def _complete_openai(prompt: str, model: str) -> dict[str, Any]:
    key = _openai_key()
    if len(key) <= 8:
        return {"ok": False, "gap": "DATA_INSUFFICIENT: OPENAI_API_KEY missing"}
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 400,
        }
    ).encode()
    code, raw = _http(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        body=payload,
    )
    if code != 200:
        return {"ok": False, "gap": f"DATA_INSUFFICIENT: openai HTTP {code}"}
    try:
        blob = json.loads(raw)
        text = blob["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {"ok": False, "gap": "DATA_INSUFFICIENT: openai empty/unparsed"}
    return {"ok": True, "text": str(text).strip(), "provider": "openai", "model": model}


def _full_prompt(prompt: str, role: str, facts: str) -> str:
    preamble = (
        f"Role: {role}. India index-options desk (NIFTY/BANKNIFTY/SENSEX). "
        "PAPER only. No win rates as fact. No live orders. "
        "If facts are missing, say DATA_INSUFFICIENT.\n"
    )
    if facts.strip():
        preamble += f"Cited facts:\n{facts.strip()}\n"
    return preamble + "\n" + prompt.strip()


def _verdict_token(text: str) -> str:
    head = (text or "").strip().split("\n", 1)[0].upper()
    for token in ("AGREE_WITH_CAVEATS", "DISAGREE", "AGREE", "HOLD", "DATA_INSUFFICIENT"):
        if token in head:
            return token
    return "OTHER"


def _together(g_ok: bool, o_ok: bool, g_text: str, o_text: str) -> str:
    if g_ok and o_ok:
        gv, ov = _verdict_token(g_text), _verdict_token(o_text)
        if gv == ov:
            return "ALIGNED"
        return "SPLIT"
    if g_ok or o_ok:
        return "ONE_ONLY"
    return "NONE"


def complete_panel(
    prompt: str,
    *,
    role: str = "counsel",
    facts: str = "",
) -> dict[str, Any]:
    """Ask Gemini and OpenAI the same brief. Desk compares; neither generates a signal."""
    load_settings()
    role = role if role in ROLES else "counsel"
    full = _full_prompt(prompt, role, facts)
    cfg = counsel_settings()
    g = _complete_gemini(full, cfg["gemini_model"]) if cfg["gemini_key_present"] else {
        "ok": False,
        "gap": "GEMINI_KEY missing",
        "text": "",
        "model": cfg["gemini_model"],
        "provider": "gemini",
    }
    o = _complete_openai(full, cfg["openai_model"]) if cfg["openai_key_present"] else {
        "ok": False,
        "gap": "OPENAI_API_KEY missing",
        "text": "",
        "model": cfg["openai_model"],
        "provider": "openai",
    }
    g_text = str(g.get("text") or "")
    o_text = str(o.get("text") or "")
    gaps: list[str] = []
    if not g.get("ok"):
        gaps.append(str(g.get("gap") or "gemini failed"))
    if not o.get("ok"):
        gaps.append(str(o.get("gap") or "openai failed"))
    return {
        "ok": bool(g.get("ok") or o.get("ok")),
        "role": role,
        "together": _together(bool(g.get("ok")), bool(o.get("ok")), g_text, o_text),
        "panel": {
            "gemini": {
                "ok": bool(g.get("ok")),
                "model": cfg["gemini_model"],
                "text": g_text,
                "gap": g.get("gap"),
            },
            "openai": {
                "ok": bool(o.get("ok")),
                "model": cfg["openai_model"],
                "text": o_text,
                "gap": o.get("gap"),
            },
        },
        "provider": "both",
        "text": g_text or o_text,
        "data_gaps": gaps,
    }


def complete(
    prompt: str,
    *,
    role: str = "counsel",
    facts: str = "",
    both: bool = True,
) -> dict[str, Any]:
    """Default: both models. `both=False` keeps a single-provider fallback path."""
    if both:
        return complete_panel(prompt, role=role, facts=facts)
    load_settings()
    role = role if role in ROLES else "counsel"
    full = _full_prompt(prompt, role, facts)
    cfg = counsel_settings()
    order = ["gemini", "openai"]
    if cfg["provider"] == "openai":
        order = ["openai", "gemini"]
    elif cfg["provider"] == "gemini":
        order = ["gemini", "openai"]
    gaps: list[str] = []
    for who in order:
        hit = (
            _complete_gemini(full, cfg["gemini_model"])
            if who == "gemini"
            else _complete_openai(full, cfg["openai_model"])
        )
        if hit.get("ok"):
            return {
                "ok": True,
                "role": role,
                "provider": hit["provider"],
                "model": hit["model"],
                "text": hit["text"],
                "data_gaps": gaps,
                "together": "ONE_ONLY",
            }
        gaps.append(str(hit.get("gap") or f"{who} failed"))
    return {
        "ok": False,
        "role": role,
        "provider": None,
        "model": None,
        "text": "",
        "together": "NONE",
        "data_gaps": gaps or ["DATA_INSUFFICIENT: both counsel providers failed"],
    }


def ping() -> dict[str, Any]:
    """Auth + one-token-class check. Never logs secrets."""
    cfg = counsel_settings()
    out: dict[str, Any] = {"config": {k: v for k, v in cfg.items()}}
    if cfg["gemini_key_present"]:
        g = _complete_gemini("Reply with exactly: OK", cfg["gemini_model"])
        out["gemini"] = {"ok": g.get("ok"), "model": cfg["gemini_model"], "gap": g.get("gap")}
    else:
        out["gemini"] = {"ok": False, "gap": "GEMINI_KEY not in env"}
    if cfg["openai_key_present"]:
        o = _complete_openai("Reply with exactly: OK", cfg["openai_model"])
        out["openai"] = {"ok": o.get("ok"), "model": cfg["openai_model"], "gap": o.get("gap")}
    else:
        out["openai"] = {"ok": False, "gap": "OPENAI_API_KEY not in env"}
    return out

"""One joint review of the FACTORY DESIGN — not per-strategy. Token-cheap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FACTORY_PROMPT = """You are 02 math + 04 quant reviewing a BACKTEST FACTORY (not a strategy).
PAPER only. NO_PROMOTE. No live Dhan orders. KEEP_ALL STRAT-001–014. New IDs = MIX-TV-EP-*.

Design facts JSON:
{facts}

Reply in <= 12 lines:
1) AGREE/DISAGREE: factory (registry + grid + stub rows) is the right way to scale ~1000 TV EPs.
2) INDEX vs PREMIUM: what MUST stay separate so we do not fake option P/L.
3) One port-effectiveness note (01/04): how to port public rules so premium tape is testable.
4) What MUST NOT be claimed from this board.
No invented win rates. No STRAT-015+.
"""


def factory_facts() -> dict[str, Any]:
    return {
        "namespace": "MIX-TV-EP-*",
        "adapters": ["sma_cross", "macd_hist", "stub"],
        "grid": {
            "tf": ["1m", "3m", "5m", "15m"],
            "underlyings": ["NIFTY", "SENSEX", "BANKNIFTY_if_cache"],
            "tapes": ["INDEX", "PREMIUM"],
        },
        "regime": "SMA50 slope 10 bars / close >= 0.002 → TREND else RANGE",
        "costs": "HYPOTHESIS_OPTION_RT_1PCT; statutory UNKNOWN",
        "event_days": "NEWS_CALENDAR empty → SCORE_SAMPLE DATA_INSUFFICIENT",
        "statuses": ["WATCH", "TESTED_FAIL", "PARK", "DATA_INSUFFICIENT"],
        "never": ["customer /", "STRAT-015+", "Pine dump", "live orders", "promote"],
        "paper_live_later": "same data/recon/tv_ep_leaderboard.json",
    }


def counsel_factory_design() -> dict[str, Any]:
    facts = factory_facts()
    prompt = FACTORY_PROMPT.format(facts=json.dumps(facts, indent=2))
    out: dict[str, Any] = {
        "scope": "FACTORY_DESIGN",
        "not": "per_strategy",
        "prompt": prompt,
        "promotion": "NO_PROMOTE",
    }
    try:
        from trading_agents_india.counsel import (
            _complete_gemini,
            _complete_openai,
            counsel_settings,
        )
    except ImportError:
        out["ok"] = False
        out["gap"] = "DATA_INSUFFICIENT: trading_agents_india.counsel not importable"
        return out

    cfg = counsel_settings()
    out["settings"] = {
        k: v
        for k, v in cfg.items()
        if "key" in k or k.endswith("model") or k == "provider"
    }
    if not (cfg.get("gemini_key_present") or cfg.get("openai_key_present")):
        out["ok"] = False
        out["gap"] = "DATA_INSUFFICIENT: no GEMINI/OPENAI keys for counsel"
        return out
    g = (
        _complete_gemini(prompt, cfg["gemini_model"])
        if cfg["gemini_key_present"]
        else {"ok": False, "gap": "gemini_missing"}
    )
    o = (
        _complete_openai(prompt, cfg["openai_model"])
        if cfg["openai_key_present"]
        else {"ok": False, "gap": "openai_missing"}
    )
    out["ok"] = bool(g.get("ok") or o.get("ok"))
    out["gemini"] = {k: v for k, v in g.items() if k != "raw"}
    out["openai"] = {k: v for k, v in o.items() if k != "raw"}
    return out


def write_counsel(blob: dict[str, Any], root: Path) -> Path:
    path = root / "teams" / "06_backtesting" / "docs" / "TV_EP_FACTORY_COUNSEL.md"
    lines = [
        "# TV-EP factory design — joint counsel (one shot)",
        "",
        "**Scope:** factory design only. Not each Editor Pick. **NO_PROMOTE.**",
        "",
    ]
    if blob.get("gap"):
        lines += [
            f"**Status:** `{blob['gap']}`",
            "",
            "Prompt saved below. Re-run `python -m backtest_engine tv-ep-counsel` when keys exist.",
            "",
            "```text",
            str(blob.get("prompt") or ""),
            "```",
            "",
        ]
    else:
        lines += ["**Status:** keys present — model text is REVIEW, not a promote.", ""]
        for name in ("gemini", "openai"):
            block = blob.get(name) or {}
            lines += [f"## {name}", "", "```text", str(block.get("text") or block.get("gap") or block), "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

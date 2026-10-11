"""LLM shadow judge on the dual-tape loop. Log only. Never changes a paper fill.

PICK: when a paper-slot or shadow rule fires → TAKE|SKIP.
EXIT: once a minute per open paper trade → HOLD|TRAIL|EXIT.

``trade: false`` is a hard lock. The board, engine opens, and paper-slot tickets
are never mutated here. Missing OPENAI_API_KEY skips the call.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from desk_ml.llm_analyst.context import dumps, scrub, untrusted_text
from desk_ml.persist import code_root

log = logging.getLogger("desk_ml.llm_judge")
IST = timezone(timedelta(hours=5, minutes=30))

PROMPT_VERSION = "llm-judge-v1"
SCHEMA = "llm-judge-v1"
ACTOR = "LLM judge"
CONFIG_REL = Path("config") / "llm_judge.yaml"
DI = "DATA_INSUFFICIENT"

PICK_DECISIONS = ("TAKE", "SKIP")
EXIT_ACTIONS = ("HOLD", "TRAIL", "EXIT")
EXPLAIN_MARKET_TYPES = (
    "trend up",
    "trend down",
    "chop",
    "tight range",
    "expiry pin",
    "high-VIX",
)
MARKET_TYPE_ALIASES = {
    "trend_up": "trend up",
    "trend-up": "trend up",
    "uptrend": "trend up",
    "trend_down": "trend down",
    "trend-down": "trend down",
    "downtrend": "trend down",
    "choppy": "chop",
    "sideways": "chop",
    "tight_range": "tight range",
    "tight-range": "tight range",
    "range": "tight range",
    "expiry": "expiry pin",
    "expiry_pin": "expiry pin",
    "pin": "expiry pin",
    "high_vix": "high-VIX",
    "high-vix": "high-VIX",
    "highvix": "high-VIX",
}
ACCOUNTS_REL = Path("config") / "v2" / "accounts.yaml"
SHADOW_MARKERS = ("shadow", "research_rule", "exit_variants")
R3_REL = Path("research") / "lab" / "2026-10-11_llm_judge" / "R3_PREREG"
R4_REL = Path("research") / "lab" / "2026-10-11_llm_judge" / "R4_SLOT"
R4_PROMPT_DEFAULT = Path("research") / "lab" / "2026-10-11_llm_debrief" / "R4" / "prompt.txt"
R4_SHA_PREFIX_DEFAULT = "d31a9c85"

DEFAULTS: dict[str, Any] = {
    "shadow": True,
    "trade": False,
    "timeout_s": 3.0,
    "model": "gpt-4o-mini",
    "cache_size": 256,
    "max_output_tokens": 200,
    "price_usd_per_1m_tokens": {"input": 0.15, "output": 0.60},
    "r4_prompt_path": str(R4_PROMPT_DEFAULT),
    "r4_sha256_prefix": R4_SHA_PREFIX_DEFAULT,
}

PICK_SYSTEM = (
    "You are a PAPER-ONLY shadow judge for an Indian index-options desk (NIFTY / "
    "BANKNIFTY / SENSEX, buy CE or buy PE). You have no order authority. A paper-slot "
    "or shadow rule already fired; you only say whether that setup looks TAKE or SKIP. "
    "Your verdict is logged for later scoring. It must not place, size, veto, or cancel "
    "any ticket. DATA_INSUFFICIENT means unknown — do not invent prints, OI, VIX, or news. "
    f"Reply with exactly one JSON object: {{\"decision\":\"TAKE|SKIP\",\"confidence\":0-1,"
    f"\"reason\":\"short string\"}}. Prompt {PROMPT_VERSION}. No prose outside the JSON."
)
EXIT_SYSTEM = (
    "You are a PAPER-ONLY shadow judge watching an open long-premium index-option ticket. "
    "You have no order authority. Once a minute you see the premium path, P&L, time in "
    "trade, and the same market snapshot as the pick call. Choose HOLD, TRAIL, or EXIT. "
    "The live paper book ignores you. DATA_INSUFFICIENT means unknown — do not invent. "
    f"Reply with exactly one JSON object: {{\"action\":\"HOLD|TRAIL|EXIT\",\"reason\":"
    f"\"short string\"}}. Prompt {PROMPT_VERSION}. No prose outside the JSON."
)
EXPLAIN_SYSTEM = (
    "You are a PAPER-ONLY explainer for an Indian index-options desk. A paper-slot "
    "trade already filled. Write 1-3 plain English sentences a founder can read, and "
    "one market-type label. You have no order authority. Do not say TAKE, SKIP, HOLD, "
    "TRAIL, EXIT, BUY, or SELL. Do not veto, size, or cancel. Do not invent prints, "
    "OI, VIX, or news. DATA_INSUFFICIENT means unknown. "
    f"Allowed market_type values exactly: {' | '.join(EXPLAIN_MARKET_TYPES)}. "
    'Reply with exactly one JSON object: {"explanation":"1-3 sentences",'
    '"market_type":"trend up|trend down|chop|tight range|expiry pin|high-VIX"}. '
    "No prose outside the JSON. No internal codes."
)

CompleteFn = Callable[..., Any]


def _num(raw: Any) -> Optional[float]:
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val == val else None


def _truthy(raw: Any, default: bool) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def load_config(
    root: Optional[Path] = None,
    environ: Optional[Mapping[str, str]] = None,
    path: Optional[Path] = None,
) -> dict[str, Any]:
    """Yaml over DEFAULTS. ``trade`` is forced False — the judge never owns a fill."""
    env = environ if environ is not None else os.environ
    cfg = dict(DEFAULTS)
    cfg["price_usd_per_1m_tokens"] = dict(DEFAULTS["price_usd_per_1m_tokens"])
    base = Path(root) if root is not None else code_root()
    cfg_path = Path(path) if path is not None else base / CONFIG_REL
    if cfg_path.is_file():
        try:
            import yaml  # type: ignore[import-untyped]

            loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                if "shadow" in loaded:
                    cfg["shadow"] = bool(loaded["shadow"])
                if loaded.get("timeout_s") is not None:
                    cfg["timeout_s"] = float(loaded["timeout_s"])
                if loaded.get("model"):
                    cfg["model"] = str(loaded["model"])
                if loaded.get("cache_size") is not None:
                    cfg["cache_size"] = int(loaded["cache_size"])
                if loaded.get("max_output_tokens") is not None:
                    cfg["max_output_tokens"] = int(loaded["max_output_tokens"])
                price = loaded.get("price_usd_per_1m_tokens")
                if isinstance(price, dict):
                    cfg["price_usd_per_1m_tokens"].update(price)
                if loaded.get("r4_prompt_path"):
                    cfg["r4_prompt_path"] = str(loaded["r4_prompt_path"]).strip()
                if loaded.get("r4_sha256_prefix"):
                    cfg["r4_sha256_prefix"] = str(loaded["r4_sha256_prefix"]).strip().lower()
        except Exception:  # noqa: BLE001 — missing yaml must not stop paper
            pass
    if "LLM_JUDGE_SHADOW" in env:
        cfg["shadow"] = _truthy(env.get("LLM_JUDGE_SHADOW"), True)
    if env.get("LLM_R4_PROMPT_PATH"):
        cfg["r4_prompt_path"] = str(env["LLM_R4_PROMPT_PATH"]).strip()
    if env.get("LLM_R4_SHA256_PREFIX"):
        cfg["r4_sha256_prefix"] = str(env["LLM_R4_SHA256_PREFIX"]).strip().lower()
    cfg["trade"] = False
    cfg["timeout_s"] = min(10.0, max(0.2, float(cfg["timeout_s"])))
    return cfg


def paper_slot_ids(root: Optional[Path] = None, *, allow_code_root: bool = True) -> frozenset[str]:
    """Active ``strategy_id`` values from accounts.yaml. No fallback roster."""
    seen: set[str] = set()
    candidates: list[Path] = []
    if root is not None:
        candidates.append(Path(root) / ACCOUNTS_REL)
    if allow_code_root or root is None:
        candidates.append(code_root() / ACCOUNTS_REL)
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return frozenset()
    try:
        import yaml  # type: ignore[import-untyped]

        blob = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — missing yaml must not stop paper
        return frozenset()
    rows = blob.get("accounts") if isinstance(blob, Mapping) else None
    if not isinstance(rows, list):
        return frozenset()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("status") or "").strip().lower() != "active":
            continue
        sid = str(row.get("strategy_id") or "").strip()
        if sid:
            seen.add(sid)
    return frozenset(seen)


def openai_key(environ: Optional[Mapping[str, str]] = None) -> str:
    env = environ if environ is not None else os.environ
    return str(env.get("OPENAI_API_KEY") or env.get("OPENAI_KEY") or "").strip()


def context_hash(ctx: Mapping[str, Any]) -> str:
    return hashlib.sha256(dumps(ctx).encode("utf-8")).hexdigest()[:20]


def parse_pick(text: Any) -> dict[str, Any]:
    obj = _parse_object(text)
    extra = set(obj) - {"decision", "confidence", "reason"}
    missing = {"decision", "confidence", "reason"} - set(obj)
    if extra or missing:
        raise ValueError(f"pick keys {sorted(obj)} != schema")
    decision = str(obj["decision"]).strip().upper()
    if decision not in PICK_DECISIONS:
        raise ValueError(f"decision {decision!r}")
    conf = obj["confidence"]
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0.0 <= float(conf) <= 1.0:
        raise ValueError(f"confidence {conf!r}")
    reason = str(obj["reason"] or "").strip()[:400]
    if not reason:
        raise ValueError("empty reason")
    return {"decision": decision, "confidence": float(conf), "reason": reason}


def parse_exit(text: Any) -> dict[str, Any]:
    obj = _parse_object(text)
    extra = set(obj) - {"action", "reason"}
    missing = {"action", "reason"} - set(obj)
    if extra or missing:
        raise ValueError(f"exit keys {sorted(obj)} != schema")
    action = str(obj["action"]).strip().upper()
    if action not in EXIT_ACTIONS:
        raise ValueError(f"action {action!r}")
    reason = str(obj["reason"] or "").strip()[:400]
    if not reason:
        raise ValueError("empty reason")
    return {"action": action, "reason": reason}


def plain_market_type(raw: Any) -> Optional[str]:
    """Map a label to the founder-facing words. Unknown → None (never invent)."""
    if raw is None or raw == "":
        return None
    s = str(raw).strip()
    if s in EXPLAIN_MARKET_TYPES:
        return s
    low = s.lower()
    for label in EXPLAIN_MARKET_TYPES:
        if low == label.lower():
            return label
    key = low.replace(" ", "_")
    if key in MARKET_TYPE_ALIASES:
        return MARKET_TYPE_ALIASES[key]
    compact = low.replace(" ", "").replace("_", "").replace("-", "")
    for alias, label in MARKET_TYPE_ALIASES.items():
        if alias.replace("_", "").replace("-", "") == compact:
            return label
    return None


def _sentence_count(text: str) -> int:
    parts = [p.strip() for p in re.split(r"[.!?]+", text) if p.strip()]
    return len(parts)


def parse_explain(text: Any) -> dict[str, Any]:
    obj = _parse_object(text)
    extra = set(obj) - {"explanation", "market_type"}
    missing = {"explanation", "market_type"} - set(obj)
    if extra or missing:
        raise ValueError(f"explain keys {sorted(obj)} != schema")
    if "decision" in obj or "action" in obj:
        raise ValueError("explain must not carry a veto")
    explanation = str(obj["explanation"] or "").strip()
    explanation = " ".join(explanation.split())
    if not explanation:
        raise ValueError("empty explanation")
    if len(explanation) > 600:
        explanation = explanation[:600].rsplit(" ", 1)[0].strip()
    n = _sentence_count(explanation)
    if n < 1 or n > 3:
        raise ValueError(f"explanation sentences {n} not in 1-3")
    market = plain_market_type(obj["market_type"])
    if market is None:
        raise ValueError(f"market_type {obj['market_type']!r}")
    return {"explanation": explanation, "market_type": market, "reason": explanation}


def _parse_object(text: Any) -> dict[str, Any]:
    if not isinstance(text, str):
        raise ValueError("reply is not text")
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"not JSON: {exc}") from None
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    return obj


def _phase(hhmm: str) -> str:
    if hhmm < "10:30":
        return "open"
    if hhmm >= "14:30":
        return "close"
    return "mid"


def _ist_parts(ts: Any, fallback: Optional[datetime] = None) -> tuple[str, str, int]:
    if isinstance(ts, datetime):
        stamp = ts if ts.tzinfo is not None else ts.replace(tzinfo=IST)
        stamp = stamp.astimezone(IST)
    else:
        try:
            stamp = datetime.fromtimestamp(int(ts), IST)
        except (TypeError, ValueError, OSError):
            stamp = fallback or datetime.now(IST)
    return stamp.date().isoformat(), stamp.strftime("%H:%M"), int(stamp.timestamp())


def summarize_candles(bars: Mapping[str, Mapping[str, Any]], last_n: int = 15) -> dict[str, Any]:
    minutes = list(bars)[-last_n:]
    closes: list[float] = []
    for hhmm in minutes:
        px = _num((bars.get(hhmm) or {}).get("idx"))
        if px is not None:
            closes.append(px)
    if not closes:
        return {"n": 0, "note": DI}
    up = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i - 1])
    down = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i - 1])
    return {
        "n": len(closes),
        "up": up,
        "down": down,
        "first": round(closes[0], 2),
        "last": round(closes[-1], 2),
        "net": round(closes[-1] - closes[0], 2),
        "range": round(max(closes) - min(closes), 2),
    }


def session_vwap(bars: Mapping[str, Mapping[str, Any]]) -> Optional[float]:
    vals = [_num((bar or {}).get("idx")) for bar in bars.values()]
    nums = [v for v in vals if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def opening_range(bars: Mapping[str, Mapping[str, Any]]) -> Any:
    rows = [_num((bars[m] or {}).get("idx")) for m in bars if "09:15" <= m < "09:30"]
    nums = [v for v in rows if v is not None]
    if len(nums) < 5:
        return DI
    return {"high": round(max(nums), 2), "low": round(min(nums), 2), "n": len(nums)}


def _atm_change(bars: Mapping[str, Mapping[str, Any]], side: str) -> Optional[float]:
    minutes = list(bars)
    if len(minutes) < 2:
        return None
    key = "ce" if side == "CE" else "pe"
    now = _num((bars[minutes[-1]] or {}).get(key))
    prev = _num((bars[minutes[-2]] or {}).get(key))
    if now is None or prev is None:
        return None
    return round(now - prev, 2)


def _oi_pair(cell: Mapping[str, Any], side: str) -> Optional[float]:
    if side == "CE":
        return _num(cell.get("ce_oi") or cell.get("oi_ce"))
    return _num(cell.get("pe_oi") or cell.get("oi_pe"))


def _oi_change(snap: Optional[Mapping[str, Any]], prev: Optional[Mapping[str, Any]], side: str) -> Any:
    if not isinstance(snap, Mapping):
        return DI
    strike = _num(snap.get("atm_strike"))
    wings = snap.get("wing_quotes") if isinstance(snap.get("wing_quotes"), Mapping) else {}
    cell = {}
    if strike is not None and isinstance(wings, Mapping):
        for key in (str(int(strike)) if float(strike) == int(strike) else str(strike), str(strike)):
            packed = wings.get(key)
            if isinstance(packed, Mapping):
                cell = packed
                break
    now = _oi_pair(cell, side) if cell else None
    prev_wings = prev.get("wing_quotes") if isinstance(prev, Mapping) else None
    prev_cell: Mapping[str, Any] = {}
    if strike is not None and isinstance(prev_wings, Mapping):
        for key in (str(int(strike)) if float(strike) == int(strike) else str(strike), str(strike)):
            packed = prev_wings.get(key)
            if isinstance(packed, Mapping):
                prev_cell = packed
                break
    before = _oi_pair(prev_cell, side) if prev_cell else None
    if now is None:
        return DI
    if before is None:
        return {"oi": now, "change": DI}
    return {"oi": now, "change": round(now - before, 2)}


def load_morning_context(root: Path, day: str) -> Any:
    candidates = (
        root / "data" / "recon" / f"{day}.pre_market.json",
        root / "data" / "recon" / f"pre_market_{day}.json",
        root / "data" / "recon" / "pre_market.json",
        root / "data" / "desk_intel" / "pre_market.json",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(blob, Mapping):
            continue
        src = blob.get("premarket") if isinstance(blob.get("premarket"), Mapping) else blob
        out: dict[str, Any] = {}
        for key in ("regime_note", "session_kind", "bias", "gift_nifty", "sgx", "vix", "india_vix"):
            val = src.get(key) if isinstance(src, Mapping) else None
            if val is None and isinstance(blob, Mapping):
                val = blob.get(key)
            if val is not None and not isinstance(val, (dict, list)):
                out[key] = untrusted_text(val, limit=80) if isinstance(val, str) else val
        news = src.get("news") if isinstance(src, Mapping) else None
        if isinstance(news, list):
            titles = []
            for item in news[:4]:
                text = item.get("title") if isinstance(item, Mapping) else item
                clean = untrusted_text(text, limit=80)
                if clean:
                    titles.append(clean)
            if titles:
                out["news_untrusted"] = titles
        return out or DI
    return DI


def _pick_num(src: Any, keys: Iterable[str]) -> Optional[float]:
    if not isinstance(src, Mapping):
        return None
    for key in keys:
        val = _num(src.get(key))
        if val is not None:
            return val
    return None


def build_market_snapshot(
    *,
    underlying: str,
    bars: Mapping[str, Mapping[str, Any]],
    snap: Optional[Mapping[str, Any]] = None,
    prev_snap: Optional[Mapping[str, Any]] = None,
    board: Optional[Mapping[str, Any]] = None,
    morning: Any = None,
    hhmm: str = "",
    side: str = "",
) -> dict[str, Any]:
    """Compact market facts. Missing fields stay DATA_INSUFFICIENT — never invented."""
    und = str(underlying or "").upper()
    last = bars[list(bars)[-1]] if bars else {}
    idx = _num((snap or {}).get("index_ltp")) or _num(last.get("idx"))
    vwap = session_vwap(bars)
    vs_vwap = round(idx - vwap, 2) if idx is not None and vwap is not None else DI
    classified = {}
    if isinstance(board, Mapping):
        classified = (board.get("last_index_regime") or {}).get(und) or {}
        if not classified:
            classified = ((board.get("steps") or {}).get(und) or {}).get("index_regime") or {}
    if not isinstance(classified, Mapping):
        classified = {}
    pdh = _pick_num(classified, ("pdh",)) or _pick_num(morning if isinstance(morning, Mapping) else {}, ("pdh",))
    pdl = _pick_num(classified, ("pdl",)) or _pick_num(morning if isinstance(morning, Mapping) else {}, ("pdl",))
    vix = (
        _pick_num(classified, ("vix", "india_vix", "iv"))
        or _pick_num(board or {}, ("vix", "india_vix"))
        or _pick_num(morning if isinstance(morning, Mapping) else {}, ("vix", "india_vix"))
    )
    basis = _pick_num(morning if isinstance(morning, Mapping) else {}, ("futures_basis", "basis", "gift_basis"))
    hw = DI
    if isinstance(morning, Mapping):
        raw_hw = morning.get("heavyweights") or morning.get("heavyweight")
        if isinstance(raw_hw, Mapping) and ("up" in raw_hw or "down" in raw_hw):
            hw = {"up": int(raw_hw.get("up") or 0), "down": int(raw_hw.get("down") or 0)}
        elif _num(morning.get("heavyweights_up")) is not None:
            hw = {
                "up": int(morning.get("heavyweights_up") or 0),
                "down": int(morning.get("heavyweights_down") or 0),
            }
    ce = _num((snap or {}).get("atm_ce_ltp")) or _num(last.get("ce"))
    pe = _num((snap or {}).get("atm_pe_ltp")) or _num(last.get("pe"))
    strike = _num((snap or {}).get("atm_strike")) or _num(last.get("atm"))
    market_type = classified.get("regime") or classified.get("session_kind") or (board or {}).get("day_kind") or DI
    return scrub(
        {
            "underlying": und,
            "index": idx if idx is not None else DI,
            "vwap": vwap if vwap is not None else DI,
            "index_vs_vwap": vs_vwap,
            "pdh": pdh if pdh is not None else DI,
            "pdl": pdl if pdl is not None else DI,
            "opening_range": opening_range(bars),
            "candles_1m_15": summarize_candles(bars, 15),
            "atm_ce": {"premium": ce if ce is not None else DI, "change": _atm_change(bars, "CE") or DI},
            "atm_pe": {"premium": pe if pe is not None else DI, "change": _atm_change(bars, "PE") or DI},
            "oi_change": _oi_change(snap, prev_snap, side or "CE"),
            "vix": vix if vix is not None else DI,
            "futures_basis": basis if basis is not None else DI,
            "heavyweights": hw,
            "market_type": market_type or DI,
            "phase": _phase(hhmm) if hhmm else DI,
            "morning_context": morning if morning not in (None, {}) else DI,
            "atm_strike": strike if strike is not None else DI,
        }
    )


def build_pick_snapshot(
    *,
    setup: str,
    side: str,
    strike: Any,
    underlying: str,
    market: Mapping[str, Any],
    source: str,
    hhmm: str,
    day: str,
) -> dict[str, Any]:
    return scrub(
        {
            "v": PROMPT_VERSION,
            "job": "PICK",
            "day": day,
            "hhmm": hhmm,
            "setup": str(setup),
            "side": side,
            "strike": _num(strike) if _num(strike) is not None else DI,
            "source": source,
            "market": dict(market),
            "orders": "REFUSED",
            "promote": False,
        }
    )


def build_exit_snapshot(
    *,
    trade: Mapping[str, Any],
    market: Mapping[str, Any],
    hhmm: str,
    day: str,
) -> dict[str, Any]:
    entry = _num(trade.get("entry"))
    mark = _num(trade.get("last_ltp") or trade.get("mark") or trade.get("exit"))
    opened = trade.get("opened_ts") or trade.get("opened_ist")
    held_min = None
    try:
        if opened is not None:
            if isinstance(opened, str) and "T" in opened:
                opened_ts = datetime.fromisoformat(opened.replace("Z", "+00:00")).timestamp()
            else:
                opened_ts = float(opened)
            now_ts = datetime.fromisoformat(f"{day}T{hhmm}:00+05:30").timestamp()
            held_min = max(0, int((now_ts - opened_ts) / 60))
    except (TypeError, ValueError, OSError):
        held_min = None
    pnl = _num(trade.get("unrealized_pnl_inr") or trade.get("realized_pnl_inr") or trade.get("gross_pnl_inr"))
    if pnl is None and entry is not None and mark is not None:
        pnl = round(mark - entry, 2)
    path = trade.get("premium_path") or trade.get("path")
    if not isinstance(path, list):
        path = []
    compact_path = []
    for item in path[-12:]:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            compact_path.append({"t": item[0], "px": _num(item[1])})
        elif isinstance(item, Mapping):
            compact_path.append({"t": item.get("t") or item.get("hhmm"), "px": _num(item.get("px") or item.get("ltp"))})
    return scrub(
        {
            "v": PROMPT_VERSION,
            "job": "EXIT",
            "day": day,
            "hhmm": hhmm,
            "setup": trade.get("book_id") or trade.get("rule_id") or trade.get("setup"),
            "side": trade.get("side"),
            "strike": _num(trade.get("atm_strike") or trade.get("strike")),
            "trade_id": trade.get("trade_id"),
            "entry": entry if entry is not None else DI,
            "premium": mark if mark is not None else DI,
            "pnl": pnl if pnl is not None else DI,
            "time_in_trade_min": held_min if held_min is not None else DI,
            "premium_path": compact_path or DI,
            "market": dict(market),
            "orders": "REFUSED",
            "promote": False,
        }
    )


def _journal_decision(job: str, verdict: Mapping[str, Any]) -> tuple[str, str]:
    if job == "EXPLAIN":
        return "pass", "llm_explain"
    if job == "PICK":
        return ("pass" if verdict.get("decision") == "TAKE" else "skip", "llm_pick")
    action = str(verdict.get("action") or "")
    if action == "EXIT":
        return "exit", "llm_exit"
    return "pass", "llm_exit"


def _cost_usd(cfg: Mapping[str, Any], tokens_in: int, tokens_out: int) -> float:
    price = cfg.get("price_usd_per_1m_tokens") or {}
    return (tokens_in * float(price.get("input", 0.15)) + tokens_out * float(price.get("output", 0.60))) / 1_000_000


def _response_schema(system: str) -> dict[str, Any]:
    if "explanation" in system and "market_type" in system:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["explanation", "market_type"],
            "properties": {
                "explanation": {"type": "string"},
                "market_type": {"type": "string", "enum": list(EXPLAIN_MARKET_TYPES)},
            },
        }
    if "TAKE|SKIP" in system:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["decision", "confidence", "reason"],
            "properties": {
                "decision": {"type": "string", "enum": list(PICK_DECISIONS)},
                "confidence": {"type": "number"},
                "reason": {"type": "string"},
            },
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "reason"],
        "properties": {
            "action": {"type": "string", "enum": list(EXIT_ACTIONS)},
            "reason": {"type": "string"},
        },
    }


def system_for_job(job: str, *, pick_system: Optional[str] = None) -> str:
    if job == "EXPLAIN":
        return EXPLAIN_SYSTEM
    if job == "PICK":
        return pick_system or PICK_SYSTEM
    return EXIT_SYSTEM


def parse_job(job: str, text: Any) -> dict[str, Any]:
    if job == "EXPLAIN":
        return parse_explain(text)
    if job == "PICK":
        return parse_pick(text)
    return parse_exit(text)


def call_openai(
    *,
    system: str,
    user: str,
    cfg: Mapping[str, Any],
    timeout_s: float,
    environ: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    key = openai_key(environ)
    if not key:
        raise RuntimeError("NO_OPENAI_API_KEY")
    schema = _response_schema(system)
    body = {
        "model": str(cfg.get("model") or "gpt-4o-mini"),
        "temperature": 0,
        "max_tokens": int(cfg.get("max_output_tokens") or 200),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "llm_judge", "strict": True, "schema": schema},
        },
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP_{exc.code}") from None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        raise RuntimeError(f"TRANSPORT:{type(exc).__name__}") from None
    usage = data.get("usage") or {}
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("NO_CONTENT") from exc
    return {
        "text": text,
        "tokens_in": int(usage.get("prompt_tokens") or 0),
        "tokens_out": int(usage.get("completion_tokens") or 0),
    }


class LlmJudge:
    """In-process cache, one-call-per-signal, one-call-per-trade-minute, cost counter."""

    def __init__(
        self,
        cfg: Mapping[str, Any],
        *,
        root: Path,
        complete_fn: Optional[CompleteFn] = None,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.cfg = dict(cfg)
        self.root = Path(root)
        self.complete_fn = complete_fn
        self.environ = dict(environ) if environ is not None else None
        self.timeout_s = float(self.cfg.get("timeout_s") or 3.0)
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._seen_signals: set[str] = set()
        self._seen_exits: set[str] = set()
        self._seen_explains: set[str] = set()
        self.calls = 0
        self.cache_hits = 0
        self.skipped = 0
        self.cost_usd = 0.0
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-judge")
        self._seed_seen()

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def stats(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "prompt_version": PROMPT_VERSION,
            "shadow": True,
            "trade": False,
            "calls": self.calls,
            "cache_hits": self.cache_hits,
            "skipped": self.skipped,
            "cost_usd": round(self.cost_usd, 6),
            "orders": "REFUSED",
            "promote": False,
        }

    def _seed_seen(self) -> None:
        folder = self.root / "data" / "shadow"
        if not folder.is_dir():
            return
        for path in folder.glob("*.jsonl"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict) or row.get("schema") != SCHEMA:
                    continue
                key = row.get("dedupe_key")
                if not key:
                    continue
                if row.get("job") == "PICK":
                    self._seen_signals.add(str(key))
                elif row.get("job") == "EXIT":
                    self._seen_exits.add(str(key))
                elif row.get("job") == "EXPLAIN":
                    self._seen_explains.add(str(key))

    def _remember(self, key: str, verdict: Mapping[str, Any]) -> None:
        self._cache[key] = dict(verdict)
        self._cache.move_to_end(key)
        while len(self._cache) > int(self.cfg.get("cache_size") or 256):
            self._cache.popitem(last=False)

    def review(
        self,
        job: str,
        snapshot: Mapping[str, Any],
        *,
        dedupe_key: str,
    ) -> dict[str, Any]:
        """Never raises. Missing key / timeout / bad JSON → skipped status."""
        h = context_hash(snapshot)
        with self._lock:
            if job == "PICK" and dedupe_key in self._seen_signals:
                self.skipped += 1
                return {"status": "skipped_dup_signal", "cached": False, "context_hash": h, "job": job}
            if job == "EXIT" and dedupe_key in self._seen_exits:
                self.skipped += 1
                return {"status": "skipped_dup_minute", "cached": False, "context_hash": h, "job": job}
            if job == "EXPLAIN" and dedupe_key in self._seen_explains:
                self.skipped += 1
                return {"status": "skipped_dup_trade", "cached": False, "context_hash": h, "job": job}
            hit = self._cache.get(h)
            if hit is not None:
                self.cache_hits += 1
                if job == "PICK":
                    self._seen_signals.add(dedupe_key)
                elif job == "EXPLAIN":
                    self._seen_explains.add(dedupe_key)
                else:
                    self._seen_exits.add(dedupe_key)
                return {**hit, "status": "ok", "cached": True, "context_hash": h, "job": job, "cost_usd": 0.0}
        if self.complete_fn is None and not openai_key(self.environ):
            self.skipped += 1
            return {
                "status": "skipped_no_key",
                "cached": False,
                "context_hash": h,
                "job": job,
                "reason": "OPENAI_API_KEY missing",
            }
        system = system_for_job(job, pick_system=self.cfg.get("pick_system"))
        user = "SNAPSHOT_JSON:\n" + dumps(snapshot)
        t0 = time.perf_counter()
        try:
            reply = self._invoke(system, user)
            verdict = parse_job(job, reply["text"])
            status = "ok"
            error = None
        except Exception as exc:  # noqa: BLE001 — fail-soft; paper loop keeps the ticket
            verdict = {}
            status = "timeout" if "TIMEOUT" in str(exc).upper() or isinstance(exc, FutureTimeout) else "error"
            error = f"{type(exc).__name__}:{str(exc)[:160]}"
            reply = {"tokens_in": 0, "tokens_out": 0}
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        cost = _cost_usd(self.cfg, int(reply.get("tokens_in") or 0), int(reply.get("tokens_out") or 0))
        with self._lock:
            self.calls += 1
            self.cost_usd += cost
            if status == "ok":
                self._remember(h, verdict)
                if job == "PICK":
                    self._seen_signals.add(dedupe_key)
                elif job == "EXPLAIN":
                    self._seen_explains.add(dedupe_key)
                else:
                    self._seen_exits.add(dedupe_key)
            else:
                self.skipped += 1
        out = {
            **verdict,
            "status": status,
            "cached": False,
            "context_hash": h,
            "job": job,
            "error": error,
            "latency_ms": latency_ms,
            "cost_usd": round(cost, 6),
            "tokens_in": int(reply.get("tokens_in") or 0),
            "tokens_out": int(reply.get("tokens_out") or 0),
        }
        log.info(
            "llm_judge job=%s status=%s cost_usd=%.6f calls=%d cache_hits=%d skipped=%d",
            job,
            status,
            self.cost_usd,
            self.calls,
            self.cache_hits,
            self.skipped,
        )
        return out

    def _invoke(self, system: str, user: str) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            if self.complete_fn is not None:
                raw = self.complete_fn(system=system, user=user)
                if isinstance(raw, dict) and "text" in raw:
                    return {
                        "text": raw["text"],
                        "tokens_in": int(raw.get("tokens_in") or 0),
                        "tokens_out": int(raw.get("tokens_out") or 0),
                    }
                if isinstance(raw, dict):
                    return {"text": json.dumps(raw), "tokens_in": 0, "tokens_out": 0}
                return {"text": str(raw), "tokens_in": 0, "tokens_out": 0}
            return call_openai(
                system=system,
                user=user,
                cfg=self.cfg,
                timeout_s=self.timeout_s,
                environ=self.environ,
            )

        fut = self._pool.submit(_run)
        try:
            return fut.result(timeout=self.timeout_s)
        except FutureTimeout:
            fut.cancel()
            raise RuntimeError(f"TIMEOUT_{int(self.timeout_s * 1000)}MS") from None


def shadow_path(root: Path, day: str) -> Path:
    return Path(root) / "data" / "shadow" / f"{day}.jsonl"


def append_judge_row(root: Path, row: Mapping[str, Any]) -> Optional[Path]:
    day = str(row.get("day") or "")
    if not day:
        return None
    path = shadow_path(root, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(row), default=str) + "\n")
    return path


def _journal_row(
    *,
    ts: int,
    underlying: str,
    candidate_id: str,
    job: str,
    verdict: Mapping[str, Any],
    trade_id: Any = None,
    inputs: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from desk_ml.decision_journal import make_row

    decision, stage = _journal_decision(job, verdict)
    reason = str(verdict.get("reason") or verdict.get("status") or "LLM judge")
    return make_row(
        ts=ts,
        underlying=underlying,
        candidate_id=candidate_id,
        stage=stage,
        actor=ACTOR,
        decision=decision,
        reason=reason,
        inputs=inputs,
        trade_id=trade_id,
    )


def _is_open_trade(row: Mapping[str, Any]) -> bool:
    status = str(row.get("status") or "").upper()
    phase = str(row.get("phase") or "").upper()
    if status in {"CLOSED", "FLAT", "SKIPPED"} or phase == "FLAT":
        return False
    return status in {"OPEN", "OPEN_PAPER", "WORKING"} or phase in {"IN_TRADE", "OPEN"} or (
        row.get("filled") and not row.get("closed_ts") and row.get("exit") is None
    )


def _fired_this_minute(row: Mapping[str, Any], hhmm: str) -> bool:
    for key in ("sig_min", "entry_min"):
        if str(row.get(key) or "") == hhmm:
            return True
    opened = row.get("opened_ist") or row.get("last_updated_ist")
    if isinstance(opened, str) and len(opened) >= 16 and opened[11:16] == hhmm:
        return True
    return bool(row.get("opened_this_tick"))


def _source_for(row: Mapping[str, Any], setup: str, slots: frozenset[str]) -> str:
    if setup in slots:
        return "paper_slot"
    if row.get("research_rule") or row.get("shadow") or any(row.get(k) for k in SHADOW_MARKERS):
        return "shadow_rule"
    return "shadow_rule"


def collect_pick_events(
    board: Mapping[str, Any],
    *,
    root: Path,
    day: str,
    hhmm: str,
) -> list[dict[str, Any]]:
    """Paper-slot or shadow-rule fires this minute. Does not open a ticket."""
    events: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    def add(event: Mapping[str, Any]) -> None:
        key = (
            str(event.get("setup")),
            str(event.get("underlying")),
            str(event.get("side")),
            event.get("strike"),
            hhmm,
        )
        if key in seen:
            return
        seen.add(key)
        events.append(dict(event))

    slots = paper_slot_ids(root)
    try:
        from desk_ml.research_rules import FROZEN_RULES, load_atm_minutes, signal

        for und in ("NIFTY", "SENSEX", "BANKNIFTY"):
            bars = load_atm_minutes(root, und, day)
            if not bars:
                continue
            minute = hhmm if hhmm in bars else list(bars)[-1]
            for rule in FROZEN_RULES:
                side = signal(rule, bars, minute, underlying=und)
                if not side:
                    continue
                rule_id = str(rule["rule_id"])
                atm = _num((bars[minute] or {}).get("atm"))
                add(
                    {
                        "setup": rule_id,
                        "underlying": und,
                        "side": side,
                        "strike": atm,
                        "source": "paper_slot" if rule_id in slots else "shadow_rule",
                        "hhmm": minute,
                    }
                )
    except Exception:  # noqa: BLE001 — tape miss must not stop EXIT reviews
        pass

    for row in list(board.get("open_trades") or []) + list(board.get("closed_trades") or []):
        if not isinstance(row, Mapping):
            continue
        if not _fired_this_minute(row, hhmm):
            continue
        setup = str(row.get("book_id") or row.get("rule_id") or row.get("setup") or "paper")
        add(
            {
                "setup": setup,
                "underlying": str(row.get("underlying") or "").upper(),
                "side": row.get("side"),
                "strike": row.get("atm_strike") or row.get("strike"),
                "source": _source_for(row, setup, slots),
                "hhmm": hhmm,
                "trade_id": row.get("trade_id"),
            }
        )

    steps = board.get("last_step_by_und") if isinstance(board.get("last_step_by_und"), Mapping) else {}
    if not steps and isinstance(board.get("last_step"), Mapping):
        last = board["last_step"]
        steps = {str(last.get("underlying") or ""): last}
    for und, step in steps.items():
        if not isinstance(step, Mapping):
            continue
        desk = step.get("desk") if isinstance(step.get("desk"), Mapping) else {}
        picker = step.get("picker") if isinstance(step.get("picker"), Mapping) else {}
        shadow = step.get("shadow") if isinstance(step.get("shadow"), Mapping) else {}
        fired = bool(desk.get("opened_this_tick")) or picker.get("action") in {"TICKET", "ENTER"}
        shadow_fired = shadow.get("action") in {"TICKET", "ENTER"}
        if not fired and not shadow_fired:
            continue
        setup = str(desk.get("product_book") or picker.get("book_id") or shadow.get("strategy_id") or "")
        if setup not in slots and not shadow_fired:
            continue
        side = picker.get("side") or shadow.get("side") or desk.get("side")
        add(
            {
                "setup": setup or "shadow",
                "underlying": str(und).upper(),
                "side": side,
                "strike": step.get("strike") or (step.get("itm_bin") or {}).get("strike"),
                "source": "paper_slot" if setup in slots else "shadow_rule",
                "hhmm": hhmm,
            }
        )
    return events


def _snap_map(snaps: Optional[Sequence[Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for snap in snaps or ():
        if hasattr(snap, "to_dict"):
            row = snap.to_dict()
        elif isinstance(snap, Mapping):
            row = dict(snap)
        else:
            continue
        und = str(row.get("underlying") or "").upper()
        if und:
            out[und] = row
    return out


def _board_fingerprint(board: Mapping[str, Any]) -> str:
    """Identity of paper tickets. Used to prove attach_and_log does not mutate fills."""
    rows = []
    for key in ("open_trades", "closed_trades"):
        for row in board.get(key) or []:
            if not isinstance(row, Mapping):
                continue
            rows.append(
                (
                    row.get("trade_id"),
                    row.get("book_id"),
                    row.get("side"),
                    row.get("entry"),
                    row.get("status"),
                    row.get("exit_reason"),
                )
            )
    return dumps({"n_open": board.get("n_open"), "rows": rows})


def attach_and_log(
    board: Mapping[str, Any],
    *,
    root: Path,
    snaps: Optional[Sequence[Any]] = None,
    prev_snaps: Optional[Sequence[Any]] = None,
    now: Optional[datetime] = None,
    complete_fn: Optional[CompleteFn] = None,
    environ: Optional[Mapping[str, str]] = None,
    judge: Optional[LlmJudge] = None,
    write: bool = True,
) -> dict[str, Any]:
    """Review fires + open trades. Returns stats. Never mutates ``board`` fills."""
    before = _board_fingerprint(board)
    cfg = load_config(root, environ)
    empty = {
        "schema": SCHEMA,
        "shadow": bool(cfg["shadow"]),
        "trade": False,
        "calls": 0,
        "cache_hits": 0,
        "skipped": 0,
        "cost_usd": 0.0,
        "wrote": 0,
        "orders": "REFUSED",
        "promote": False,
    }
    if not cfg["shadow"] or not write:
        return empty
    stamp = now if now is not None else datetime.now(IST)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=IST)
    stamp = stamp.astimezone(IST)
    day = str(board.get("session_ist_date") or stamp.date().isoformat())
    hhmm = stamp.strftime("%H:%M")
    owned = judge is None
    worker = judge or LlmJudge(cfg, root=root, complete_fn=complete_fn, environ=environ)
    morning = load_morning_context(root, day)
    snap_by = _snap_map(snaps)
    prev_by = _snap_map(prev_snaps)
    wrote = 0
    try:
        from desk_ml.research_rules import load_atm_minutes
    except Exception:  # noqa: BLE001
        load_atm_minutes = None  # type: ignore[assignment]

    bars_cache: dict[str, dict[str, Any]] = {}

    def bars_for(und: str) -> dict[str, Any]:
        if und in bars_cache:
            return bars_cache[und]
        rows: dict[str, Any] = {}
        if load_atm_minutes is not None:
            try:
                rows = load_atm_minutes(root, und, day)
            except Exception:  # noqa: BLE001
                rows = {}
        bars_cache[und] = rows
        return rows

    def market_for(und: str, side: str) -> dict[str, Any]:
        return build_market_snapshot(
            underlying=und,
            bars=bars_for(und),
            snap=snap_by.get(und),
            prev_snap=prev_by.get(und),
            board=board,
            morning=morning,
            hhmm=hhmm,
            side=side,
        )

    from desk_ml.decision_journal import DecisionJournal

    journal = DecisionJournal(root)
    ts = int(stamp.timestamp())

    for event in collect_pick_events(board, root=root, day=day, hhmm=hhmm):
        und = str(event.get("underlying") or "").upper()
        side = str(event.get("side") or "")
        setup = str(event.get("setup") or "paper")
        strike = event.get("strike")
        sig_hhmm = str(event.get("hhmm") or hhmm)
        snapshot = build_pick_snapshot(
            setup=setup,
            side=side,
            strike=strike,
            underlying=und,
            market=market_for(und, side),
            source=str(event.get("source") or "paper_slot"),
            hhmm=sig_hhmm,
            day=day,
        )
        dedupe = f"pick:{day}:{setup}:{und}:{side}:{strike}:{sig_hhmm}"
        verdict = worker.review("PICK", snapshot, dedupe_key=dedupe)
        if verdict.get("status") != "ok":
            append_judge_row(
                root,
                {
                    "schema": SCHEMA,
                    "job": "PICK",
                    "day": day,
                    "ts": ts,
                    "hhmm": sig_hhmm,
                    "underlying": und,
                    "setup": setup,
                    "side": side,
                    "strike": strike,
                    "source": event.get("source"),
                    "status": verdict.get("status"),
                    "reason": verdict.get("reason") or verdict.get("error"),
                    "dedupe_key": dedupe,
                    "context_hash": verdict.get("context_hash"),
                    "cost_usd": verdict.get("cost_usd") or 0.0,
                    "cached": bool(verdict.get("cached")),
                    "prompt_version": PROMPT_VERSION,
                    "orders": "REFUSED",
                    "promote": False,
                    "shadow": True,
                    "trade": False,
                },
            )
            continue
        row = {
            "schema": SCHEMA,
            "job": "PICK",
            "day": day,
            "ts": ts,
            "hhmm": sig_hhmm,
            "underlying": und,
            "setup": setup,
            "side": side,
            "strike": strike,
            "source": event.get("source"),
            "decision": verdict.get("decision"),
            "confidence": verdict.get("confidence"),
            "reason": verdict.get("reason"),
            "status": "ok",
            "dedupe_key": dedupe,
            "context_hash": verdict.get("context_hash"),
            "cost_usd": verdict.get("cost_usd") or 0.0,
            "cached": bool(verdict.get("cached")),
            "latency_ms": verdict.get("latency_ms"),
            "prompt_version": PROMPT_VERSION,
            "snapshot": snapshot,
            "orders": "REFUSED",
            "promote": False,
            "shadow": True,
            "trade": False,
        }
        append_judge_row(root, row)
        journal.append(
            _journal_row(
                ts=ts,
                underlying=und,
                candidate_id=dedupe,
                job="PICK",
                verdict=verdict,
                trade_id=event.get("trade_id"),
                inputs={"side": side, "day_type": (snapshot.get("market") or {}).get("market_type"), "phase": _phase(sig_hhmm)},
            )
        )
        wrote += 1

    for trade in board.get("open_trades") or []:
        if not isinstance(trade, Mapping) or not _is_open_trade(trade):
            continue
        und = str(trade.get("underlying") or "").upper()
        side = str(trade.get("side") or "")
        tid = str(trade.get("trade_id") or f"{und}:{side}:{hhmm}")
        snapshot = build_exit_snapshot(trade=trade, market=market_for(und, side), hhmm=hhmm, day=day)
        dedupe = f"exit:{tid}:{day}:{hhmm}"
        verdict = worker.review("EXIT", snapshot, dedupe_key=dedupe)
        if verdict.get("status") != "ok":
            append_judge_row(
                root,
                {
                    "schema": SCHEMA,
                    "job": "EXIT",
                    "day": day,
                    "ts": ts,
                    "hhmm": hhmm,
                    "underlying": und,
                    "trade_id": tid,
                    "setup": trade.get("book_id") or trade.get("rule_id"),
                    "side": side,
                    "status": verdict.get("status"),
                    "reason": verdict.get("reason") or verdict.get("error"),
                    "dedupe_key": dedupe,
                    "context_hash": verdict.get("context_hash"),
                    "cost_usd": verdict.get("cost_usd") or 0.0,
                    "cached": bool(verdict.get("cached")),
                    "prompt_version": PROMPT_VERSION,
                    "orders": "REFUSED",
                    "promote": False,
                    "shadow": True,
                    "trade": False,
                },
            )
            continue
        row = {
            "schema": SCHEMA,
            "job": "EXIT",
            "day": day,
            "ts": ts,
            "hhmm": hhmm,
            "underlying": und,
            "trade_id": tid,
            "setup": trade.get("book_id") or trade.get("rule_id"),
            "side": side,
            "strike": trade.get("atm_strike") or trade.get("strike"),
            "action": verdict.get("action"),
            "reason": verdict.get("reason"),
            "status": "ok",
            "dedupe_key": dedupe,
            "context_hash": verdict.get("context_hash"),
            "cost_usd": verdict.get("cost_usd") or 0.0,
            "cached": bool(verdict.get("cached")),
            "latency_ms": verdict.get("latency_ms"),
            "prompt_version": PROMPT_VERSION,
            "snapshot": snapshot,
            "orders": "REFUSED",
            "promote": False,
            "shadow": True,
            "trade": False,
        }
        append_judge_row(root, row)
        journal.append(
            _journal_row(
                ts=ts,
                underlying=und,
                candidate_id=dedupe,
                job="EXIT",
                verdict=verdict,
                trade_id=tid,
                inputs={"side": side, "premium": trade.get("last_ltp") or trade.get("entry"), "phase": _phase(hhmm)},
            )
        )
        wrote += 1

    if _board_fingerprint(board) != before:
        raise RuntimeError("llm_judge mutated paper-slot decisions")
    explain_stats: dict[str, Any] = {"scheduled": 0, "trade": False, "veto": False}
    try:
        from desk_ml.llm_explain import schedule_explains

        explain_stats = schedule_explains(
            board,
            root=root,
            snaps=snaps,
            prev_snaps=prev_snaps,
            now=stamp,
            complete_fn=complete_fn,
            environ=environ,
            write=write,
        )
    except Exception:  # noqa: BLE001 — explainer never owns the fill
        log.info("llm_explain schedule failed", exc_info=True)
    if _board_fingerprint(board) != before:
        raise RuntimeError("llm_judge mutated paper-slot decisions")
    out = {**worker.stats(), "wrote": wrote, "explains_scheduled": int(explain_stats.get("scheduled") or 0), "veto": False}
    if owned:
        worker.close()
    return out


def score(
    rows: Sequence[Mapping[str, Any]],
    trades: Sequence[Mapping[str, Any]],
    *,
    seed: int = 1,
) -> dict[str, Any]:
    """LLM-filtered P&L vs plain vs random skip. Paper files only. Not a promote."""
    import random

    picks = [
        r
        for r in rows
        if r.get("schema") == SCHEMA and r.get("job") == "PICK" and r.get("status") == "ok" and r.get("decision") in PICK_DECISIONS
    ]
    by_trade: dict[str, Mapping[str, Any]] = {}
    by_key: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in picks:
        tid = str(row.get("trade_id") or "")
        if tid:
            by_trade[tid] = row
        key = (str(row.get("underlying") or "").upper(), str(row.get("side") or ""), str(row.get("setup") or ""))
        by_key[key] = row

    def _pnl(trade: Mapping[str, Any]) -> Optional[float]:
        for key in ("realized_pnl_inr", "net_pnl_inr", "gross_pnl_inr", "realized_pnl"):
            val = _num(trade.get(key))
            if val is not None:
                return val
        return None

    closed = []
    for trade in trades:
        if str(trade.get("status") or "").upper() not in {"CLOSED", "FLAT"} and trade.get("closed_ts") is None:
            if trade.get("exit") is None and not trade.get("realized_pnl_inr"):
                continue
        pnl = _pnl(trade)
        if pnl is None:
            continue
        closed.append((trade, pnl))

    plain = [pnl for _t, pnl in closed]
    kept: list[float] = []
    skipped: list[float] = []
    unmatched = 0
    for trade, pnl in closed:
        pick = by_trade.get(str(trade.get("trade_id") or ""))
        if pick is None:
            pick = by_key.get(
                (
                    str(trade.get("underlying") or "").upper(),
                    str(trade.get("side") or ""),
                    str(trade.get("book_id") or trade.get("rule_id") or trade.get("setup") or ""),
                )
            )
        if pick is None:
            unmatched += 1
            kept.append(pnl)
            continue
        if pick.get("decision") == "TAKE":
            kept.append(pnl)
        else:
            skipped.append(pnl)

    skip_n = len(skipped)
    rng = random.Random(seed)
    random_kept = list(plain)
    if skip_n and len(plain) >= skip_n:
        drop = set(rng.sample(range(len(plain)), skip_n))
        random_kept = [p for i, p in enumerate(plain) if i not in drop]

    def _sum(vals: Sequence[float]) -> float:
        return round(float(sum(vals)), 4)

    return {
        "schema": f"{SCHEMA}-score",
        "plain_n": len(plain),
        "plain_pnl": _sum(plain),
        "llm_filtered_n": len(kept),
        "llm_filtered_pnl": _sum(kept),
        "llm_skipped_n": len(skipped),
        "llm_skipped_pnl": _sum(skipped),
        "random_skip_n": skip_n,
        "random_skip_pnl": _sum(random_kept),
        "unmatched_trades": unmatched,
        "picks": len(picks),
        "seed": seed,
        "orders": "REFUSED",
        "promote": False,
        "note": "Paper scoring only. LLM-filtered = TAKE picks. Random skip uses the same skip count. NO_PROMOTE.",
    }


_JUDGE: Optional[LlmJudge] = None
_JUDGE_LOCK = threading.Lock()


def get_judge(root: Path, *, complete_fn: Optional[CompleteFn] = None, environ: Optional[Mapping[str, str]] = None) -> LlmJudge:
    global _JUDGE
    with _JUDGE_LOCK:
        if _JUDGE is None:
            _JUDGE = LlmJudge(load_config(root, environ), root=root, complete_fn=complete_fn, environ=environ)
        return _JUDGE


def reset_judge() -> None:
    global _JUDGE
    with _JUDGE_LOCK:
        if _JUDGE is not None:
            _JUDGE.close()
        _JUDGE = None

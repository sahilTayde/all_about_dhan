"""LLM-ANALYST: an advisory LLM second opinion on the room's provisional CE/PE side (PR-016).

Enabled in config/analysts.yaml as `{key: LLM-ANALYST, shadow: true, timeout_ms: 2500}`; tuned in
config/llm_analyst.yaml. `weight: 0` (default) = shadow: the vote carries `metadata.shadow`, so the
boss never counts it, and with an online provider the call runs in the background so the tick never
waits. `weight: 1` (and no `shadow: true` on the analysts.yaml row) = agree becomes one CONFIRM vote for the side; disagree is HOLD (silent), so the
LLM can add a vote but can never veto, size, or place anything.

Replay/parity rooms (`deterministic=True`) always use the offline `replay_provider`.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Mapping, Optional

from analysts.base import ABSTAIN, BUY_CE, BUY_PE, HOLD, Analyst, MarketContext, Vote
from analysts.registry import register

log = logging.getLogger("analysts.llm")
LLM_KEY = "LLM-ANALYST"
RECENT_TRADES = 3
NEAR_LEVEL_FRAC = 0.0075


def _num(raw: Any) -> Optional[float]:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def llm_snapshot(engine: Any, step: Any) -> dict[str, Any]:
    """Engine state the LLM context needs, as of this tick only. Never raises."""
    try:
        return _llm_snapshot(engine, step)
    except Exception as exc:
        log.warning("llm snapshot failed (%s); LLM context is partial", type(exc).__name__)
        return {}


def _llm_snapshot(engine: Any, step: Any) -> dict[str, Any]:
    from analysts.shadow import _bar_hl, bars_upto, ist_date, ist_dt

    und = str(getattr(step, "und", "") or "").upper()
    now = int(step.tick.ts)
    day = ist_date(now)
    spot = _num(getattr(step.tick, "idx_close", None))
    bars = [b for b in bars_upto(list(getattr(step, "bars_1m", None) or []), now) if ist_date(int(b["ts"])) == day]
    highs = [h for h, _l in map(_bar_hl, bars) if h is not None]
    lows = [lo for _h, lo in map(_bar_hl, bars) if lo is not None]
    sr = (getattr(engine, "sr_levels", None) or {}).get(und) or {}
    swings = []
    if spot:
        near = [s for s in sr.get("swings") or [] if _num(s.get("px")) and abs(float(s["px"]) - spot) <= spot * NEAR_LEVEL_FRAC]
        swings = [{"px": s["px"], "kind": s.get("kind"), "tf": s.get("tf")}
                  for s in sorted(near, key=lambda s: abs(float(s["px"]) - spot))[:4]]
    levels = {
        "spot": spot,
        "session_high": max(highs) if highs else None,
        "session_low": min(lows) if lows else None,
        "pdh": _num(sr.get("pdh")), "pdl": _num(sr.get("pdl")), "pdc": _num(sr.get("pdc")),
        "near_swings": swings or None,
    }
    closed = [r for r in getattr(engine, "closed", None) or []
              if str(r.get("underlying") or "").upper() == und and r.get("filled", True)
              and _num(r.get("closed_ts")) is not None and int(r["closed_ts"]) <= now]
    today = [r for r in closed if ist_date(int(r["closed_ts"])) == day]
    recent = sorted(today, key=lambda r: int(r["closed_ts"]))[-RECENT_TRADES:]
    opens = getattr(engine, "opens", None) or {}
    book = {
        "today_pnl_inr": round(sum(_num(r.get("realized_pnl_inr")) or 0.0 for r in today), 2),
        "n_trades_today": len(today),
        "open_positions": sum(1 for k in opens if isinstance(k, tuple) and len(k) > 1 and str(k[1]).upper() == und),
        "recent": [{"side": r.get("side"), "result": r.get("result"), "pnl_inr": _num(r.get("realized_pnl_inr")),
                    "mins_ago": round((now - int(r["closed_ts"])) / 60.0, 1)} for r in recent],
    }
    return {
        "strike": _num(getattr(step, "strike", None)),
        "ist_time": ist_dt(now).strftime("%H:%M"),
        "regime": dict(getattr(step, "classified", None) or {}),
        "levels": levels,
        "book": book,
    }


_BRIEF: dict[str, tuple[float, Any]] = {}
_BRIEF_LOCK = threading.Lock()


def load_brief(path: Optional[str]) -> Any:
    """Pre-market brief JSON (desk_intel PRE_MARKET payload), re-read only when its mtime changes."""
    if not path:
        return None
    p = Path(path)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return None
    with _BRIEF_LOCK:
        hit = _BRIEF.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        _BRIEF[path] = (mtime, data)
        return data


def provisional_signal(ctx: MarketContext) -> dict[str, Any]:
    """The room's picker majority on the other analysts' votes: the side the boss is leaning to."""
    from desk_ml.picker import picker_majority

    votes = ctx.legacy_votes()
    pick = picker_majority(votes, classified=ctx.inputs.get("classified"))
    n_ce, n_pe, n_sp = int(pick["n_ce"]), int(pick["n_pe"]), int(pick["n_spoken"])
    return {
        "side": pick.get("side"),
        "confidence": round(max(n_ce, n_pe) / n_sp, 4) if n_sp else 0.0,
        "votes": {"CE": n_ce, "PE": n_pe, "silent": len(votes) - n_sp},
        "voters": {str(v.source): v.side for v in votes if v.spoken()},
        "picker_detail": pick.get("detail"),
    }


def _shadow_bits(features: Mapping[str, Any]) -> tuple[Any, Any, dict[str, Any], Optional[float]]:
    snap = features.get("shadow") if isinstance(features.get("shadow"), Mapping) else {}

    def cell(k: str) -> Mapping[str, Any]:
        c = snap.get(k)
        return c if isinstance(c, Mapping) else {}

    gex = cell("gex")
    chain = None
    if gex.get("value") is not None:
        ex = gex.get("extra") or {}
        chain = {"gex": gex.get("value"), "regime": ex.get("regime"), "zero_gamma": ex.get("zero_gamma"),
                 "n_strikes": ex.get("n_strikes")}
    exp = cell("expiry_day")
    expiry = {"dte": exp.get("value"), "expiry_day": exp.get("flag")} if exp.get("value") is not None else None
    vol = {"rv30": cell("rv30").get("value"), "rng60_atr": cell("rng60_atr").get("value"),
           "chasing": cell("chasing").get("flag"), "high_vol": cell("high_vol").get("flag")}
    day_open = _num((cell("day_direction").get("extra") or {}).get("day_open"))
    return chain, expiry, vol, day_open


class LLMAnalyst(Analyst):
    analyst_id = LLM_KEY

    def __init__(self, config_path: Optional[Path] = None) -> None:
        from desk_ml.llm_analyst import load_config

        self.cfg = load_config(config_path)
        self.weight = float(self.cfg["weight"])
        self.replay = True  # offline until a live (non-deterministic) room says otherwise

    def set_replay(self, replay: bool) -> None:
        self.replay = bool(replay)

    def build_context(self, ctx: MarketContext, signal: Mapping[str, Any]) -> dict[str, Any]:
        from desk_ml.llm_analyst import build_context

        feats = ctx.features or {}
        snap = feats.get("llm") if isinstance(feats.get("llm"), Mapping) else {}
        chain, expiry, vol, day_open = _shadow_bits(feats)
        levels = dict(snap.get("levels") or {})
        if day_open is not None:
            levels["day_open"] = day_open
        return build_context(
            underlying=ctx.underlying, tick_ts=ctx.ts, ist_time=snap.get("ist_time"),
            signal={**signal, "strike": snap.get("strike")},
            regime=snap.get("regime") or ctx.inputs.get("classified"),
            levels={k: v for k, v in levels.items() if v is not None}, chain=chain, book=snap.get("book"),
            expiry=expiry, vol=vol, brief=load_brief(self.cfg.get("premarket_brief_path")),
        )

    def vote(self, context: MarketContext) -> Vote:
        from desk_ml.llm_analyst import get_advisor

        signal = provisional_signal(context)
        side = signal.get("side")
        if side not in ("CE", "PE"):
            return self._vote(None, {"verdict": "abstain", "confidence": 0.0, "status": "NO_SIGNAL"})
        advisor = get_advisor(self.cfg, replay=self.replay)
        background = self.weight == 0.0 and not advisor.provider.offline
        return self._vote(side, advisor.review(self.build_context(context, signal), background=background))

    def _vote(self, side: Optional[str], out: Mapping[str, Any]) -> Vote:
        verdict = str(out.get("verdict") or "abstain")
        conf = min(1.0, max(0.0, float(out.get("confidence") or 0.0)))
        shadow = self.weight == 0.0
        meta = {
            "shadow": shadow, "value": verdict, "flag": side, "reason_class": "SHADOW" if shadow else "CONFIRM",
            "llm_status": out.get("status"), "context_hash": out.get("context_hash"), "cached": bool(out.get("cached")),
            "risk_flags": list(out.get("risk_flags") or []), "weight": self.weight,
        }
        reasoning = "; ".join(out.get("reasons") or []) or str(out.get("status") or verdict)
        if shadow or verdict == "abstain" or side is None:
            signal = ABSTAIN
        elif verdict == "agree":
            signal = BUY_CE if side == "CE" else BUY_PE
        else:
            signal = HOLD
        return Vote(self.analyst_id, signal, conf if signal != ABSTAIN or shadow else 0.0, reasoning[:300], meta)


register(LLM_KEY, LLMAnalyst)

"""Bounded PAPER session tuner for MIX-TV-EP / MIX-DEFAULT-BUY.

Hyperparameter *search on one session tape* only. Never writes production
params. Never places Dhan orders. Zero LLM. NO_PROMOTE.

RETUNE_GATE: emit BACKTEST_REQUIRED proposals + local paper param files under
data/recon/. Do not silently retune MIX-DEFAULT-BUY.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from backtest_engine.clocks import session_date_ist
from backtest_engine.fetch import load_cached_series
from backtest_engine.indicators import Bar
from backtest_engine.tv_ep.adapters import Adapter, get_adapter
from backtest_engine.tv_ep.catalog import CatalogEntry, ParamSpec, load_catalog
from backtest_engine.tv_ep.grid import INDEX_IDS, _load_index_bars, _trim_years
from backtest_engine.tv_ep.mapping import map_tv_signal

IST = timezone(timedelta(hours=5, minutes=30))

SHORTLIST = (
    "MIX-TV-EP-005",
    "MIX-TV-EP-010",
    "MIX-TV-EP-016",
    "MIX-DEFAULT-BUY",
)
MAX_TWEAKS_PER_MIX_PER_DAY = 3
MAX_TICKS_DEFAULT = 90
RT_COST = 0.01  # HYPOTHESIS 1% each way on premium — matches costs.DEFAULT_COST
Z_HOLD = 2.0
Z_WINDOW = 30
MIN_BETA_BARS = 8
FORBIDDEN_PRODUCTION = (
    "config/workspace.yaml",
    "teams/04_quant/docs/candidates/",
    "packages/indicators/",
)

DEFAULT_BUY_SCHEMA = {
    "lookback": ParamSpec("int", 1, (1, 2, 3)),
}


def _tod(ts: int) -> tuple[int, int]:
    dt = datetime.fromtimestamp(int(ts), tz=IST)
    return dt.hour, dt.minute


def _bars_from_rows(rows: list[dict[str, Any]]) -> list[Bar]:
    out: list[Bar] = []
    for row in rows:
        try:
            ts = int(row.get("ts") or 0)
            if not ts:
                continue
            out.append(
                Bar(
                    ts=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0),
                )
            )
        except (TypeError, ValueError, KeyError):
            continue
    out.sort(key=lambda b: b.ts)
    return out


def _load_premium_sides(underlying: str, root: Path) -> tuple[list[Bar], list[Bar], str, str]:
    """Last ATM CE+PE day on disk. Empty ⇒ no tape."""
    folder = root / "data" / "recon" / "premium_tape"
    if not folder.is_dir():
        return [], [], "", ""
    paths = sorted(folder.glob(f"{underlying.upper()}_ATM_1m_*.json"))
    if not paths:
        return [], [], "", ""
    path = paths[-1]
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], [], "", ""
    ce = _bars_from_rows(list(blob.get("ce") or []))
    pe = _bars_from_rows(list(blob.get("pe") or []))
    day = str((blob.get("meta") or {}).get("day") or path.stem.split("_")[-1])
    return ce, pe, day, str(path)


def _fallback_divergence(
    *,
    intended: str,
    ce_prev: Optional[float],
    ce_now: Optional[float],
    pe_prev: Optional[float],
    pe_now: Optional[float],
) -> tuple[bool, str]:
    if intended not in ("CE", "PE", "BUY_CE", "BUY_PE"):
        return False, ""
    side = "CE" if intended in ("CE", "BUY_CE") else "PE"
    if None in (ce_prev, ce_now, pe_prev, pe_now):
        return True, "PREMIUM_DIVERGENCE: DATA_INSUFFICIENT CE/PE — no new paper ticket"
    ce_ret = float(ce_now) - float(ce_prev)  # type: ignore[arg-type]
    pe_ret = float(pe_now) - float(pe_prev)  # type: ignore[arg-type]
    if ce_ret > 0 and pe_ret > 0:
        return True, "PREMIUM_DIVERGENCE: both CE and PE premiums rose"
    if side == "CE" and ce_ret <= 0 and pe_ret > 0:
        return True, "PREMIUM_DIVERGENCE: BUY_CE but PE premium led"
    if side == "PE" and pe_ret <= 0 and ce_ret > 0:
        return True, "PREMIUM_DIVERGENCE: BUY_PE but CE premium led"
    return False, ""


def premium_divergence(
    *,
    intended: str,
    index_prev: Optional[float] = None,
    index_now: Optional[float] = None,
    ce_prev: Optional[float] = None,
    ce_now: Optional[float] = None,
    pe_prev: Optional[float] = None,
    pe_now: Optional[float] = None,
) -> tuple[bool, str]:
    """Dual-use sibling `desk_divergence.judge_tick` when importable.

    PREMIUM_DIVERGENCE (or any allow_new_paper_ce_pe=False) → no new paper ticket.
    MIX lean that disagrees with dual-tape confirm is also blocked.
    """
    if intended not in ("CE", "PE", "BUY_CE", "BUY_PE"):
        return False, ""
    side = "CE" if intended in ("CE", "BUY_CE") else "PE"
    try:
        from trading_agents_india.desk_divergence import judge_tick
    except ImportError:
        return _fallback_divergence(
            intended=intended,
            ce_prev=ce_prev,
            ce_now=ce_now,
            pe_prev=pe_prev,
            pe_now=pe_now,
        )
    idx_d = None if None in (index_prev, index_now) else float(index_now) - float(index_prev)  # type: ignore[arg-type]
    ce_d = None if None in (ce_prev, ce_now) else float(ce_now) - float(ce_prev)  # type: ignore[arg-type]
    pe_d = None if None in (pe_prev, pe_now) else float(pe_now) - float(pe_prev)  # type: ignore[arg-type]
    note = judge_tick(
        underlying="NIFTY",
        index_delta=idx_d,
        ce_delta=ce_d,
        pe_delta=pe_d,
    )
    if not note.allow_new_paper_ce_pe:
        return True, note.dealer_note
    if side == "CE" and note.verdict == "BUY_PE_CONFIRM":
        return True, "PREMIUM_DIVERGENCE: dual-tape confirms PE; MIX wanted BUY_CE"
    if side == "PE" and note.verdict == "BUY_CE_CONFIRM":
        return True, "PREMIUM_DIVERGENCE: dual-tape confirms CE; MIX wanted BUY_PE"
    return False, ""


def _return_triples(
    index: list[Bar], ce: list[Bar], pe: list[Bar], end_i: int
) -> list[tuple[float, float, float]]:
    """Simple returns on bars[1..end_i] inclusive. Causal: no bar after end_i."""
    from trading_agents_india.index_ce_pe_formulas import simple_return

    out: list[tuple[float, float, float]] = []
    for j in range(1, end_i + 1):
        ir = simple_return(index[j - 1].close, index[j].close)
        cr = simple_return(ce[j - 1].close, ce[j].close)
        pr = simple_return(pe[j - 1].close, pe[j].close)
        if ir is None or cr is None or pr is None:
            continue
        out.append((ir, cr, pr))
    return out


def causal_overlay_block(
    index: list[Bar],
    ce: list[Bar],
    pe: list[Bar],
    i: int,
    *,
    z_hold: float = Z_HOLD,
    z_window: int = Z_WINDOW,
) -> tuple[bool, str]:
    """HOLD new paper CE/PE on FOLLOW-GAP or ML-002 |z| (expanding k, causal z).

    Beta uses returns strictly before the decision bar. Residual z uses history
    only (02 / AFML). Does not write MIX params. Not a promote.
    """
    from trading_agents_india.index_ce_pe_formulas import (
        mix_form_diverge_z,
        mix_form_follow_gap,
        ols_beta,
    )

    if i < 1 or i >= min(len(index), len(ce), len(pe)):
        return True, "DATA_INSUFFICIENT: no prior bar for FOLLOW-GAP / residual z"
    rets = _return_triples(index, ce, pe, i)
    if not rets:
        return True, "DATA_INSUFFICIENT: no aligned returns — no new paper ticket"
    ir, cr, pr = rets[-1]
    gap = mix_form_follow_gap(index_ret=ir, ce_ret=cr, pe_ret=pr)
    if gap.get("any_divergence"):
        return True, "FOLLOW-GAP: index lean not confirmed by ATM premium"
    prior = rets[:-1]
    if len(prior) < MIN_BETA_BARS:
        return False, ""
    idx = [r[0] for r in prior]
    k_ce = ols_beta(idx, [r[1] for r in prior])
    k_pe = ols_beta(idx, [r[2] for r in prior])
    if k_ce is None or k_pe is None:
        return False, ""
    hist = [0.5 * ((r[1] - k_ce * r[0]) + (r[2] - k_pe * r[0])) for r in prior]
    cur = 0.5 * ((cr - k_ce * ir) + (pr - k_pe * ir))
    z = mix_form_diverge_z(cur, hist, window=z_window)
    if z is not None and abs(z) >= z_hold:
        return True, f"ML-002 RESIDUAL_Z |z|={abs(z):.2f} ≥ {z_hold}"
    return False, ""


def default_buy_leans(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """Paper-only MIX-DEFAULT-BUY proxy: lookback close momentum. Not production."""
    lookback = max(1, int(params.get("lookback", 1)))
    leans = ["HOLD"] * len(bars)
    for i in range(lookback, len(bars)):
        prev = bars[i - lookback].close
        cur = bars[i].close
        if cur > prev:
            leans[i] = "CE"
        elif cur < prev:
            leans[i] = "PE"
    return leans


def _default_entry() -> CatalogEntry:
    return CatalogEntry(
        ep_id="EP-000",
        mix_id="MIX-DEFAULT-BUY",
        adapter="default_buy",
        title="Customer default (paper proxy only — production untouched)",
        origin="PROJECT_MIX",
        input_schema=DEFAULT_BUY_SCHEMA,
    )


def _adapter_for(mix_id: str, catalog: list[CatalogEntry]) -> tuple[CatalogEntry, Adapter, Any]:
    if mix_id == "MIX-DEFAULT-BUY":
        entry = _default_entry()

        class _A:
            id = "default_buy"
            ported = True
            partial = True
            gap = "paper proxy; MIX-DEFAULT-BUY production params never written"
            default_schema = DEFAULT_BUY_SCHEMA

            def schema_for(self, _e: CatalogEntry) -> dict[str, ParamSpec]:
                return DEFAULT_BUY_SCHEMA

            def param_grid(self, _e: CatalogEntry) -> list[dict[str, float]]:
                return [{"lookback": float(v)} for v in (1, 2, 3)]

        return entry, _A(), default_buy_leans  # type: ignore[return-value]
    found = next((e for e in catalog if e.mix_id == mix_id), None)
    if found is None:
        found = CatalogEntry(
            ep_id="EP-000",
            mix_id=mix_id,
            adapter="stub",
            title="missing catalog row",
            origin="TV-EP-STUB",
        )
    adapter = get_adapter(found.adapter)
    return found, adapter, adapter.leans


def bounded_param_grid(adapter: Any, entry: CatalogEntry, *, max_tweaks: int) -> list[dict[str, float]]:
    cap = max(1, min(int(max_tweaks), MAX_TWEAKS_PER_MIX_PER_DAY))
    schema = adapter.schema_for(entry) if hasattr(adapter, "schema_for") else {}
    default = {k: float(spec.default) for k, spec in schema.items()} if schema else {}
    combos: list[dict[str, float]] = []
    raw = adapter.param_grid(entry) if hasattr(adapter, "param_grid") else [default]
    if default:
        combos.append(default)
    for combo in raw:
        if combo not in combos:
            combos.append(combo)
        if len(combos) >= cap:
            break
    return combos[:cap] or [{}]


def _align_triple(
    index: list[Bar],
    ce: list[Bar],
    pe: list[Bar],
) -> tuple[list[Bar], list[Bar], list[Bar], dict[str, Any]]:
    """Prefer same-epoch intersection; else IST clock-of-day (honest mismatch)."""
    ce_ts = {b.ts: b for b in ce}
    pe_ts = {b.ts: b for b in pe}
    idx_ts = {b.ts: b for b in index}
    common = sorted(set(ce_ts) & set(pe_ts) & set(idx_ts))
    meta: dict[str, Any] = {}
    if len(common) >= 20:
        meta["alignment"] = "SAME_EPOCH"
        meta["bars"] = len(common)
        return (
            [idx_ts[t] for t in common],
            [ce_ts[t] for t in common],
            [pe_ts[t] for t in common],
            meta,
        )
    ce_tod = {_tod(b.ts): b for b in ce}
    pe_tod = {_tod(b.ts): b for b in pe}
    idx_tod = {_tod(b.ts): b for b in index}
    keys = sorted(set(ce_tod) & set(pe_tod) & set(idx_tod))
    meta["alignment"] = "SESSION_CLOCK"
    meta["bars"] = len(keys)
    meta["note"] = (
        "INDEX cache and ATM CE/PE are different calendar days; bars matched by IST HH:MM. "
        "Not the same trading day. Paper only."
    )
    if index:
        meta["index_last_ist"] = datetime.fromtimestamp(index[-1].ts, IST).isoformat(timespec="minutes")
    if ce:
        meta["premium_last_ist"] = datetime.fromtimestamp(ce[-1].ts, IST).isoformat(timespec="minutes")
    return (
        [idx_tod[k] for k in keys],
        [ce_tod[k] for k in keys],
        [pe_tod[k] for k in keys],
        meta,
    )


def load_session_tapes(
    underlying: str,
    *,
    root: Path,
    years: float = 0.12,
) -> dict[str, Any]:
    idx, idx_gap = _load_index_bars(underlying, client=None, fetch_live=False, years=years)
    if not idx:
        # Fall back to untrimmed cache if years trim emptied the last session.
        meta = INDEX_IDS.get(underlying)
        if meta:
            sid, seg, inst = meta
            idx = load_cached_series(
                security_id=str(sid),
                exchange_segment=seg,
                instrument=inst,
                interval=1,
            )
            idx = _trim_years(idx, years) if idx else []
            if not idx_gap and not idx:
                idx_gap = f"DATA_INSUFFICIENT: no INDEX 1m cache for {underlying}"
    ce, pe, prem_day, prem_path = _load_premium_sides(underlying, root)
    if not ce or not pe:
        return {
            "ok": False,
            "gap": "DATA_INSUFFICIENT: no ATM CE+PE 1m premium_tape — stop (no tape)",
            "index": [],
            "ce": [],
            "pe": [],
        }
    if not idx:
        return {
            "ok": False,
            "gap": idx_gap or "DATA_INSUFFICIENT: no INDEX 1m cache — stop (no tape)",
            "index": [],
            "ce": ce,
            "pe": pe,
            "premium_day": prem_day,
        }
    a_idx, a_ce, a_pe, align = _align_triple(idx, ce, pe)
    if len(a_idx) < 8:
        return {
            "ok": False,
            "gap": "DATA_INSUFFICIENT: INDEX+CE+PE alignment < 8 bars — stop (no tape)",
            "alignment": align,
            "index": a_idx,
            "ce": a_ce,
            "pe": a_pe,
        }
    return {
        "ok": True,
        "gap": "",
        "index": a_idx,
        "ce": a_ce,
        "pe": a_pe,
        "premium_day": prem_day,
        "premium_path": prem_path,
        "alignment": align,
        "index_gap": idx_gap,
    }


def _lean_to_side(raw: str) -> str:
    mapped = map_tv_signal(raw)
    if raw in ("CE", "PE", "HOLD", "EXIT"):
        if raw == "EXIT":
            return "HOLD"
        return raw
    if mapped in ("CE", "PE"):
        return mapped
    return "HOLD"


def replay_one(
    *,
    mix_id: str,
    params: dict[str, float],
    index: list[Bar],
    ce: list[Bar],
    pe: list[Bar],
    leans_fn: Any,
    max_ticks: int,
) -> dict[str, Any]:
    n = min(len(index), len(ce), len(pe), int(max_ticks) if max_ticks else 10**9)
    if n < 3:
        return {
            "mix_id": mix_id,
            "params": params,
            "ticks": n,
            "tickets": [],
            "blocked_divergence": 0,
            "blocked_overlay": 0,
            "paper_pnl": 0.0,
            "paper_pnl_after_cost": 0.0,
            "wins": 0,
            "losses": 0,
            "holds": n,
            "mistake_notes": [],
            "gap": "no tape",
        }
    slice_idx = index[:n]
    slice_ce = ce[:n]
    slice_pe = pe[:n]
    leans_raw = leans_fn(slice_idx, params) if leans_fn else ["HOLD"] * n
    if len(leans_raw) < n:
        leans_raw = list(leans_raw) + ["HOLD"] * (n - len(leans_raw))
    tickets: list[dict[str, Any]] = []
    mistakes: list[str] = []
    blocked = 0
    holds = 0
    in_pos = False
    for i in range(n - 1):
        side = _lean_to_side(leans_raw[i])
        if side == "HOLD" or in_pos:
            if side == "HOLD":
                holds += 1
            continue
        div, why = premium_divergence(
            intended=side,
            index_prev=slice_idx[i - 1].close if i else None,
            index_now=slice_idx[i].close,
            ce_prev=slice_ce[i - 1].close if i else None,
            ce_now=slice_ce[i].close,
            pe_prev=slice_pe[i - 1].close if i else None,
            pe_now=slice_pe[i].close,
        )
        overlay, overlay_why = causal_overlay_block(slice_idx, slice_ce, slice_pe, i)
        if div or overlay:
            blocked += 1
            tickets.append(
                {
                    "i": i,
                    "ts": slice_idx[i].ts,
                    "signal": "HOLD",
                    "wanted": f"BUY_{side}",
                    "blocked": why or overlay_why,
                    "pnl": 0.0,
                }
            )
            continue
        prem = slice_ce if side == "CE" else slice_pe
        fill = prem[i + 1]
        entry = fill.open
        nxt = fill.close
        pnl = nxt - entry
        after = pnl - RT_COST * (abs(entry) + abs(nxt))
        win = pnl > 0
        note = ""
        if not win:
            note = (
                f"{mix_id} BUY_{side} at i={i} next-bar-open fill {pnl:.4f} ≤0 "
                f"(params={params})"
            )
            mistakes.append(note)
        tickets.append(
            {
                "i": i,
                "ts": slice_idx[i].ts,
                "signal": f"BUY_{side}",
                "entry_premium": entry,
                "next_premium": nxt,
                "fill_ts": fill.ts,
                "pnl": round(pnl, 6),
                "pnl_after_cost": round(after, 6),
                "mistake_note": note or None,
            }
        )
        in_pos = False  # 1-bar next-premium score; flatten before next candidate
    pnls = [float(t["pnl"]) for t in tickets if t.get("signal", "").startswith("BUY_")]
    afters = [float(t["pnl_after_cost"]) for t in tickets if t.get("signal", "").startswith("BUY_")]
    wins = sum(1 for p in pnls if p > 0)
    return {
        "mix_id": mix_id,
        "params": params,
        "ticks": n,
        "tickets": tickets,
        "blocked_divergence": blocked,
        "paper_pnl": round(sum(pnls), 6),
        "paper_pnl_after_cost": round(sum(afters), 6),
        "wins": wins,
        "losses": len(pnls) - wins,
        "holds": holds,
        "trades": len(pnls),
        "mistake_notes": mistakes[:40],
        "cost_model": "HYPOTHESIS_OPTION_RT_1PCT",
        "fill": "signal_close → next_bar_open premium (1m); mark next_bar_close",
        "promotion": "NO_PROMOTE",
    }


def _proposal_payload(mix_row: dict[str, Any], *, tape_meta: dict[str, Any]) -> dict[str, Any]:
    best = mix_row.get("best") or {}
    return {
        "kind": "RETUNE_PROPOSAL",
        "status": "BACKTEST_REQUIRED",
        "keep_current_strategy": True,
        "production_params_written": False,
        "promotion": "NO_PROMOTE",
        "mix_id": mix_row.get("mix_id"),
        "customer_default_untouched": mix_row.get("mix_id") == "MIX-DEFAULT-BUY",
        "proposed_input_schema": best.get("params") or {},
        "paper_pnl_after_cost": best.get("paper_pnl_after_cost"),
        "baseline_pnl_after_cost": (mix_row.get("baseline") or {}).get("paper_pnl_after_cost"),
        "paper_improved_vs_baseline": mix_row.get("paper_improved"),
        "one_day_pnl_is_not_evidence": True,
        "oos_non_event_required": True,
        "backtest_results": None,
        "mistake_notes": best.get("mistake_notes") or [],
        "tweaks_tried": mix_row.get("tweaks_tried"),
        "tape": tape_meta,
        "forbidden_write_paths": list(FORBIDDEN_PRODUCTION),
        "note": (
            "Local paper param file only. Do not copy into MIX-DEFAULT-BUY / "
            "workspace.yaml. 06 must OOS+NORMAL before any promote."
        ),
    }


def _write_recon(
    *,
    root: Path,
    mix_id: str,
    day: str,
    proposal: dict[str, Any],
    paper_params: dict[str, Any],
) -> dict[str, str]:
    recon = root / "data" / "recon"
    recon.mkdir(parents=True, exist_ok=True)
    safe = mix_id.replace("/", "_")
    prop_path = recon / f"RETUNE_PROPOSAL_TV_EP_PAPER_{safe}_{day}.json"
    param_path = recon / f"tv_ep_paper_params_{safe}_{day}.json"
    prop_path.write_text(json.dumps(proposal, indent=2, default=str), encoding="utf-8")
    param_path.write_text(
        json.dumps(
            {
                **paper_params,
                "production_params_written": False,
                "promotion": "NO_PROMOTE",
                "mix_default_buy_untouched": mix_id == "MIX-DEFAULT-BUY",
                "path_is_local_paper_only": True,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return {"proposal": str(prop_path), "paper_params": str(param_path)}


def append_paper_sessions(root: Path, sessions: list[dict[str, Any]]) -> str:
    path = root / "data" / "recon" / "tv_ep_leaderboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    blob: dict[str, Any]
    if path.is_file():
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blob = {}
    else:
        blob = {
            "mode": "PAPER",
            "promotion": "NO_PROMOTE",
            "research_ready_for_programming": False,
            "cells": [],
        }
    live = list(blob.get("paper_sessions") or blob.get("paper_live") or [])
    live.extend(sessions)
    blob["paper_sessions"] = live
    blob["paper_live"] = live
    blob["promotion"] = "NO_PROMOTE"
    blob["mode"] = "PAPER"
    path.write_text(json.dumps(blob, indent=2, default=str), encoding="utf-8")
    return str(path)


def run_paper_tune(
    *,
    root: Optional[Path] = None,
    mix_ids: Optional[list[str]] = None,
    underlying: str = "NIFTY",
    max_ticks: int = MAX_TICKS_DEFAULT,
    max_tweaks: int = MAX_TWEAKS_PER_MIX_PER_DAY,
    write: bool = True,
    bars_override: Optional[dict[str, list[Bar]]] = None,
) -> dict[str, Any]:
    from dhan_client.config import repo_root as _repo

    root = root or _repo()
    ids = list(mix_ids or SHORTLIST)
    catalog = load_catalog()
    if bars_override:
        idx = bars_override.get("index") or []
        ce_b = bars_override.get("ce") or []
        pe_b = bars_override.get("pe") or []
        if min(len(idx), len(ce_b), len(pe_b)) < 8:
            tapes = {
                "ok": False,
                "gap": "DATA_INSUFFICIENT: INDEX+CE+PE alignment < 8 bars — stop (no tape)",
                "index": idx,
                "ce": ce_b,
                "pe": pe_b,
            }
        else:
            tapes = {
                "ok": True,
                "gap": "",
                "index": idx,
                "ce": ce_b,
                "pe": pe_b,
                "premium_day": "fixture",
                "alignment": {"alignment": "SAME_EPOCH", "bars": len(idx)},
            }
    else:
        tapes = load_session_tapes(underlying, root=root)
    if not tapes.get("ok"):
        return {
            "ok": False,
            "mode": "PAPER",
            "promotion": "NO_PROMOTE",
            "llm": False,
            "orders": "refused",
            "gap": tapes.get("gap"),
            "mixes_ran": [],
            "paper_pnl_improved": False,
            "proposal_paths": [],
            "stop": "no tape",
        }
    index = list(tapes["index"])
    ce = list(tapes["ce"])
    pe = list(tapes["pe"])
    day = str(tapes.get("premium_day") or session_date_ist(index[-1].ts) if index else "unknown")
    mix_rows: list[dict[str, Any]] = []
    proposal_paths: list[str] = []
    sessions: list[dict[str, Any]] = []
    any_improved = False
    for mix_id in ids:
        # One MIX at a time (bounded).
        entry, adapter, leans_fn = _adapter_for(mix_id, catalog)
        if leans_fn is None:
            mix_rows.append(
                {
                    "mix_id": mix_id,
                    "status": "DATA_INSUFFICIENT",
                    "gap": adapter.gap or "unported adapter — KEEP_ALL, no paper tickets",
                    "tweaks_tried": 0,
                    "paper_improved": False,
                    "promotion": "NO_PROMOTE",
                }
            )
            continue
        grid = bounded_param_grid(adapter, entry, max_tweaks=max_tweaks)
        runs = [
            replay_one(
                mix_id=mix_id,
                params=params,
                index=index,
                ce=ce,
                pe=pe,
                leans_fn=leans_fn,
                max_ticks=max_ticks,
            )
            for params in grid
        ]
        baseline = runs[0]
        best = max(runs, key=lambda r: (float(r.get("paper_pnl_after_cost") or 0), float(r.get("paper_pnl") or 0)))
        improved = float(best.get("paper_pnl_after_cost") or 0) > float(
            baseline.get("paper_pnl_after_cost") or 0
        )
        any_improved = any_improved or improved
        row = {
            "mix_id": mix_id,
            "adapter": getattr(adapter, "id", entry.adapter),
            "title": entry.title,
            "tweaks_tried": len(runs),
            "baseline": {
                "params": baseline.get("params"),
                "paper_pnl": baseline.get("paper_pnl"),
                "paper_pnl_after_cost": baseline.get("paper_pnl_after_cost"),
                "trades": baseline.get("trades"),
                "wins": baseline.get("wins"),
            },
            "best": {
                "params": best.get("params"),
                "paper_pnl": best.get("paper_pnl"),
                "paper_pnl_after_cost": best.get("paper_pnl_after_cost"),
                "trades": best.get("trades"),
                "wins": best.get("wins"),
                "blocked_divergence": best.get("blocked_divergence"),
                "mistake_notes": best.get("mistake_notes"),
            },
            "paper_improved": improved,
            "status": "PAPER_WATCH" if (best.get("trades") or 0) else "PARK",
            "promotion": "NO_PROMOTE",
            "keep_current_strategy": True,
        }
        mix_rows.append(row)
        tape_meta = {
            "underlying": underlying,
            "premium_day": day,
            "alignment": tapes.get("alignment"),
            "ticks": best.get("ticks"),
        }
        proposal = _proposal_payload(row, tape_meta=tape_meta)
        paper_params = {
            "mix_id": mix_id,
            "input_schema": best.get("params") or {},
            "status": "BACKTEST_REQUIRED",
            "layer": "HYPOTHESIS",
        }
        if write:
            paths = _write_recon(
                root=root,
                mix_id=mix_id,
                day=day,
                proposal=proposal,
                paper_params=paper_params,
            )
            proposal_paths.append(paths["proposal"])
            row["proposal_path"] = paths["proposal"]
            row["paper_params_path"] = paths["paper_params"]
        sessions.append(
            {
                "mix_id": mix_id,
                "day": day,
                "underlying": underlying,
                "paper_pnl_after_cost": best.get("paper_pnl_after_cost"),
                "baseline_pnl_after_cost": baseline.get("paper_pnl_after_cost"),
                "paper_improved": improved,
                "trades": best.get("trades"),
                "blocked_divergence": best.get("blocked_divergence"),
                "params": best.get("params"),
                "promotion": "NO_PROMOTE",
                "status": row["status"],
                "unvalidated": True,
            }
        )
    board_path = ""
    summary_path = ""
    if write:
        board_path = append_paper_sessions(root, sessions)
        summary = {
            "kind": "TV_EP_PAPER_TUNE",
            "mode": "PAPER",
            "promotion": "NO_PROMOTE",
            "llm": False,
            "orders": "refused",
            "underlying": underlying,
            "mixes_ran": [r["mix_id"] for r in mix_rows],
            "paper_pnl_improved": any_improved,
            "proposal_paths": proposal_paths,
            "mixes": mix_rows,
            "tape": {
                "premium_day": day,
                "alignment": tapes.get("alignment"),
                "index_bars": len(index),
                "ce_bars": len(ce),
                "pe_bars": len(pe),
            },
            "ist_0915": (
                "Next live dry: 09:15 IST `python -m backtest_engine tv-ep-paper-tune` "
                "(cache; --poll only if founder started paper hours). Still NO_PROMOTE."
            ),
        }
        summary_path = str(root / "data" / "recon" / f"tv_ep_paper_tune_{day}.json")
        Path(summary_path).write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return {
        "ok": True,
        "mode": "PAPER",
        "promotion": "NO_PROMOTE",
        "research_ready_for_programming": False,
        "llm": False,
        "orders": "refused",
        "production_params_written": False,
        "keep_current_strategy": True,
        "mixes_ran": [r["mix_id"] for r in mix_rows],
        "paper_pnl_improved": any_improved,
        "proposal_paths": proposal_paths,
        "mixes": mix_rows,
        "leaderboard": board_path,
        "summary_path": summary_path,
        "tape": tapes.get("alignment"),
        "premium_day": day,
        "underlying": underlying,
        "max_ticks": max_ticks,
        "max_tweaks": max_tweaks,
    }


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="PAPER session tuner for MIX-TV-EP / DEFAULT-BUY. No orders. NO_PROMOTE."
    )
    p.add_argument(
        "--mix",
        nargs="+",
        default=list(SHORTLIST),
        help="One MIX at a time internally; default shortlist 005 010 016 DEFAULT-BUY.",
    )
    p.add_argument("--underlying", default="NIFTY", choices=("NIFTY", "BANKNIFTY", "SENSEX"))
    p.add_argument("--max-ticks", type=int, default=MAX_TICKS_DEFAULT)
    p.add_argument("--max-tweaks", type=int, default=MAX_TWEAKS_PER_MIX_PER_DAY)
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args(argv)
    mixes = []
    for raw in args.mix:
        token = raw.strip().upper()
        if token in ("DEFAULT-BUY", "MIX-DEFAULT-BUY", "DEFAULT"):
            mixes.append("MIX-DEFAULT-BUY")
        elif token.startswith("MIX-"):
            mixes.append(token)
        elif token.isdigit():
            mixes.append(f"MIX-TV-EP-{int(token):03d}")
        else:
            mixes.append(token)
    report = run_paper_tune(
        mix_ids=mixes,
        underlying=args.underlying,
        max_ticks=int(args.max_ticks),
        max_tweaks=int(args.max_tweaks),
        write=not args.no_write,
    )
    slim = {k: v for k, v in report.items() if k != "mixes"}
    slim["mixes_head"] = [
        {
            "mix_id": m.get("mix_id"),
            "paper_improved": m.get("paper_improved"),
            "best_pnl_after_cost": (m.get("best") or {}).get("paper_pnl_after_cost"),
            "baseline_pnl_after_cost": (m.get("baseline") or {}).get("paper_pnl_after_cost"),
            "tweaks_tried": m.get("tweaks_tried"),
            "proposal_path": m.get("proposal_path"),
            "gap": m.get("gap"),
        }
        for m in (report.get("mixes") or [])
    ]
    print(json.dumps(slim, indent=2, default=str))
    return 0 if report.get("ok") or report.get("stop") == "no tape" else 1

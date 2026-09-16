"""Parallel PAPER scalper books on INDEX+ATM tape. No live Dhan. No MIX-DEFAULT-BUY write.

Each book_id × underlying has at most one OPEN. Books never veto each other.
Dealer / mix proposes CE/PE + ATM + feasible stop/target; ML-001/002 may SKIP that book.
MIX-ML-LOGIT is an INDEX scan book, not the customer default.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from desk_ml.features import Triple, build_feature_rows
from desk_ml.fit import fit_from_rows, score_features_dict
from desk_ml.inventory import inventory_recon
from desk_ml.model import OVERLAY_HOLD, premium_divergence_pattern
from desk_ml.mrr import Z_HOLD, ols_beta, rolling_z
from desk_ml.persist import pack_estimators, repo_root
from desk_ml.tape import load_dual_tape_triples, load_index_closes, load_triples

try:
    from warehouse.feasibility import evaluate_long_premium
except ImportError:  # pragma: no cover
    evaluate_long_premium = None  # type: ignore[assignment]

try:
    from trading_agents_india.desk_divergence import judge_tick
except ImportError:  # pragma: no cover
    judge_tick = None  # type: ignore[assignment]

IST = timezone(timedelta(hours=5, minutes=30))
FLATTEN_MINUTES_IST = 15 * 60  # 15:00 IST
SCALP_HOLD_BARS = 8  # 1m tape ≈ 8 minutes
RANGE_LOOKBACK = 20
STOP_FRAC = 0.40
TARGET_FRAC = 0.55
STRIKE_STEP = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "SENSEX": 100.0}

LIVE_BOOKS = (
    "MIX-DEFAULT-BUY",
    "ML-001",
    "ML-002",
    "ML-1",
    "MIX-ML-LOGIT",
    "MIX-ML-LOGIT-XR",
    "MIX-TV-EP-024",
)

TV_EP_KEEP_ALL = tuple(f"MIX-TV-EP-{i:03d}" for i in range(1, 26))
TV_EP_SHORTLIST = ("MIX-TV-EP-018", "MIX-TV-EP-010", "MIX-TV-EP-009")

STOP_FLAG_NAME = "ml_paper_scalp_STOPPED.flag"
DASH_JSON_NAME = "ml_paper_dashboard.json"
DASH_MD_REL = Path("teams") / "06_backtesting" / "docs" / "ML_PAPER_DASHBOARD.md"
MOCK_JSON_REL = Path("apps") / "web" / "public" / "mock" / "ml_paper_dashboard.json"


def _ist_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=IST)


def minutes_ist(ts: int) -> int:
    dt = _ist_dt(ts)
    return dt.hour * 60 + dt.minute


def round_atm_strike(underlying: str, index_ltp: float) -> float:
    step = STRIKE_STEP.get(underlying.upper(), 50.0)
    return round(float(index_ltp) / step) * step


def feasibility_long(*, entry: float, stop: float, target: float, typical_range: float) -> dict[str, Any]:
    if evaluate_long_premium is None:
        return {
            "ok": False,
            "action": "HOLD",
            "reason_code": "DATA_INSUFFICIENT",
            "note": "warehouse.feasibility not importable",
        }
    dec = evaluate_long_premium(
        entry=entry,
        stop=stop,
        target=target,
        stage="EARLY",
        typical_premium_range=typical_range,
    )
    return dec.to_dict()


def propose_levels(entry: float, premiums: Sequence[float]) -> dict[str, Any]:
    """Scalp stop/target from same-side premium path. Kills fantasy 150/96/250."""
    if entry is None or entry <= 0:
        return {"ok": False, "reason_code": "DATA_INSUFFICIENT", "data_gaps": ["entry missing"]}
    path = [float(x) for x in premiums if x is not None]
    if len(path) < 5:
        return {
            "ok": False,
            "reason_code": "DATA_INSUFFICIENT",
            "data_gaps": ["typical_premium_range: need ≥5 ATM prints"],
        }
    typical = max(path) - min(path)
    if typical <= 0:
        return {"ok": False, "reason_code": "DATA_INSUFFICIENT", "data_gaps": ["flat premium path"]}
    stop = entry - STOP_FRAC * typical
    target = entry + TARGET_FRAC * typical
    if stop <= 0:
        stop = max(0.05, entry * 0.85)
    feas = feasibility_long(entry=entry, stop=stop, target=target, typical_range=typical)
    return {
        "ok": bool(feas.get("ok")),
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "target": round(target, 4),
        "typical_premium_range": round(typical, 4),
        "feasibility": feas,
        "reason_code": feas.get("reason_code"),
        "scalp_hold_bars": SCALP_HOLD_BARS,
        "flatten_ist": "15:00",
    }


@dataclass
class OpenPaper:
    book_id: str
    underlying: str
    side: str
    trade_id: str
    entry: float
    stop: float
    target: float
    atm_strike: Optional[float]
    opened_ts: int
    opened_bar: int
    strike_source: str


@dataclass
class BookEngine:
    opens: dict[tuple[str, str], OpenPaper] = field(default_factory=dict)
    closed: list[dict[str, Any]] = field(default_factory=list)
    skips: list[dict[str, Any]] = field(default_factory=list)
    last_step: dict[str, Any] = field(default_factory=dict)

    def has_open(self, book_id: str, underlying: str) -> bool:
        return (book_id, underlying) in self.opens

    def mark_skip(self, book_id: str, underlying: str, reason: str, **extra: Any) -> None:
        self.skips.append(
            {
                "book_id": book_id,
                "underlying": underlying,
                "action": "SKIP",
                "reason": reason,
                **extra,
            }
        )


def dealer_side(
    index_delta: Optional[float],
    ce_delta: Optional[float],
    pe_delta: Optional[float],
    *,
    underlying: str = "NIFTY",
) -> dict[str, Any]:
    if judge_tick is None:
        return {"side": None, "verdict": "DATA_INSUFFICIENT", "case": "NO_DEALER"}
    note = judge_tick(
        underlying=underlying,
        index_delta=index_delta,
        ce_delta=ce_delta,
        pe_delta=pe_delta,
        paper_train=False,
    )
    side = None
    if note.verdict == "BUY_CE_CONFIRM":
        side = "CE"
    elif note.verdict == "BUY_PE_CONFIRM":
        side = "PE"
    return {
        "side": side,
        "verdict": note.verdict,
        "case": note.case,
        "allow_new_paper_ce_pe": note.allow_new_paper_ce_pe,
        "dealer_note": note.dealer_note,
    }


def _sma(vals: Sequence[float], n: int) -> Optional[float]:
    if len(vals) < n:
        return None
    chunk = vals[-n:]
    return sum(chunk) / n


def tv_ep_024_side(idx_closes: Sequence[float]) -> Optional[str]:
    sma20 = _sma(list(idx_closes), 20)
    if sma20 is None:
        return None
    last = float(idx_closes[-1])
    if last > sma20:
        return "CE"
    if last < sma20:
        return "PE"
    return None


def paper_hit_rate(pnls: Sequence[float]) -> Optional[float]:
    """Closed-paper hit rate: share of realized_pnl > 0. Not a live claim. NO_PROMOTE."""
    if not pnls:
        return None
    wins = sum(1 for p in pnls if float(p) > 0)
    return round(wins / len(pnls), 4)


def resample_closes_3m(closes: dict[int, float]) -> list[Any]:
    """3m INDEX bars from 1m closes. Does not fabricate missing days."""
    try:
        from backtest_engine.indicators import Bar
    except ImportError:
        return []
    buckets: dict[int, list[tuple[int, float]]] = {}
    for ts, close in sorted(closes.items()):
        key = int(ts) - (int(ts) % 180)
        buckets.setdefault(key, []).append((int(ts), float(close)))
    bars = []
    for key in sorted(buckets):
        grp = buckets[key]
        cs = [c for _, c in grp]
        bars.append(
            Bar(
                ts=grp[-1][0],
                open=float(cs[0]),
                high=float(max(cs)),
                low=float(min(cs)),
                close=float(cs[-1]),
                volume=0.0,
            )
        )
    return bars


def resample_index_3m(triples: Sequence[Triple]) -> list[Any]:
    """3m INDEX bars from 1m triples. Does not fabricate missing days."""
    return resample_closes_3m({int(t.ts): float(t.idx_close) for t in triples})


def logit_side_series(
    triples: Sequence[Triple],
    *,
    index_closes: Optional[dict[int, float]] = None,
    xr: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Walk-forward INDEX 3m logit. Train on INDEX history *before* the ATM session."""
    thin = {
        "side": None,
        "status": "DATA_INSUFFICIENT",
        "reason": "INDEX 3m train < 200 labeled rows before session (no fabricate)",
        "n_3m": 0,
    }
    if not triples:
        return [], {"n_3m": 0, "n_index_1m": 0}
    closes = dict(index_closes or {})
    for t in triples:
        closes.setdefault(int(t.ts), float(t.idx_close))
    bars = resample_closes_3m(closes)
    meta: dict[str, Any] = {"n_3m": len(bars), "n_index_1m": len(closes)}
    if len(bars) < 40:
        meta["status"] = "DATA_INSUFFICIENT"
        return [{**thin, "n_3m": len(bars)} for _ in triples], meta
    try:
        from backtest_engine.ml_leans import lean_ml_logit
        from backtest_engine.patterns import lean_range_exp
    except ImportError:
        meta["status"] = "DATA_INSUFFICIENT"
        reason = "backtest_engine.ml_leans not importable"
        return [{**thin, "reason": reason, "n_3m": len(bars)} for _ in triples], meta
    train_end = int(triples[0].ts)
    meta["train_end_ts"] = train_end
    leans = lean_ml_logit(bars, train_end_ts=train_end)
    xr_leans = lean_range_exp(bars) if xr else None
    labeled_before = sum(1 for bar in bars if bar.ts < train_end)
    meta["n_train_3m_bars_before_session"] = labeled_before
    out: list[dict[str, Any]] = []
    last_logit = "SKIP"
    last_xr = "SKIP"
    bi = 0
    for t in triples:
        while bi < len(bars) and bars[bi].ts <= int(t.ts):
            last_logit = leans[bi]
            if xr_leans is not None:
                last_xr = xr_leans[bi]
            bi += 1
        if xr:
            if last_logit in {"CE", "PE"} and last_logit == last_xr:
                out.append(
                    {
                        "side": last_logit,
                        "status": "OK",
                        "n_3m": len(bars),
                        "train_end_ts": train_end,
                    }
                )
            else:
                out.append(
                    {
                        "side": None,
                        "status": "SKIP",
                        "reason": f"XR filter logit={last_logit} range={last_xr}",
                        "n_3m": len(bars),
                        "train_end_ts": train_end,
                    }
                )
            continue
        if last_logit in {"CE", "PE"}:
            out.append(
                {
                    "side": last_logit,
                    "status": "OK",
                    "n_3m": len(bars),
                    "train_end_ts": train_end,
                }
            )
        else:
            out.append(
                {
                    "side": None,
                    "status": "DATA_INSUFFICIENT" if last_logit == "SKIP" else "SKIP",
                    "reason": (
                        "lean_ml_logit SKIP (needs ≥200 labeled 3m train rows before cutoff; "
                        "label is next INDEX close, not premium)"
                    ),
                    "n_3m": len(bars),
                    "train_end_ts": train_end,
                }
            )
    meta["status"] = "OK" if any(r.get("side") in {"CE", "PE"} for r in out) else "DATA_INSUFFICIENT"
    return out, meta


def logit_last_side(triples: Sequence[Triple], *, xr: bool = False) -> dict[str, Any]:
    series, meta = logit_side_series(triples, xr=xr)
    if series:
        return {**series[-1], **{k: v for k, v in meta.items() if k not in series[-1]}}
    return {
        "side": None,
        "status": "DATA_INSUFFICIENT",
        "reason": "no triples",
        "n_3m": meta.get("n_3m", 0),
    }


def ml1_meta_label(closed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """AFML-style take/skip. Needs closed paper labels; else DATA_INSUFFICIENT."""
    labeled = [c for c in closed if c.get("realized_pnl") is not None]
    if len(labeled) < 30:
        return {
            "take": None,
            "status": "DATA_INSUFFICIENT",
            "reason": f"ML-1 meta-label needs ≥30 closed paper rows; have {len(labeled)}",
        }
    pnls = [float(c["realized_pnl"]) for c in labeled]
    rate = paper_hit_rate(pnls)
    take = rate is not None and rate >= 0.5
    return {
        "take": take,
        "status": "OK",
        "n_labels": len(labeled),
        "win_rate": rate,
        "win_rate_kind": "paper_closed_premium_gt_0",
        "promote": False,
    }


def _exit_reason(pos: OpenPaper, ltp: float, ts: int, bar_i: int) -> Optional[str]:
    if ltp <= pos.stop:
        return "STOP"
    if ltp >= pos.target:
        return "TARGET"
    if bar_i - pos.opened_bar >= SCALP_HOLD_BARS:
        return "TIME"
    if minutes_ist(ts) >= FLATTEN_MINUTES_IST:
        return "FLATTEN_1500"
    return None


def _close(engine: BookEngine, pos: OpenPaper, *, ltp: float, ts: int, reason: str) -> None:
    pnl = float(ltp) - float(pos.entry)
    engine.closed.append(
        {
            "book_id": pos.book_id,
            "underlying": pos.underlying,
            "side": pos.side,
            "trade_id": pos.trade_id,
            "status": "CLOSED_PAPER",
            "entry": pos.entry,
            "exit": round(float(ltp), 4),
            "stop": pos.stop,
            "target": pos.target,
            "atm_strike": pos.atm_strike,
            "strike_source": pos.strike_source,
            "exit_reason": reason,
            "realized_pnl": round(pnl, 4),
            "opened_ts": pos.opened_ts,
            "closed_ts": ts,
            "opened_ist": _ist_dt(pos.opened_ts).isoformat(timespec="seconds"),
            "closed_ist": _ist_dt(ts).isoformat(timespec="seconds"),
            "shadow": True,
            "execution": "refused",
            "promote": False,
            "won": pnl > 0,
        }
    )
    engine.opens.pop((pos.book_id, pos.underlying), None)


def _try_open(
    engine: BookEngine,
    *,
    book_id: str,
    underlying: str,
    side: Optional[str],
    tick: Triple,
    ce_path: Sequence[float],
    pe_path: Sequence[float],
    bar_i: int,
    skip_reason: Optional[str] = None,
    strike: Optional[float] = None,
    strike_source: str = "ROUND_INDEX_HYPOTHESIS",
) -> None:
    if engine.has_open(book_id, underlying):
        return
    if skip_reason:
        engine.mark_skip(book_id, underlying, skip_reason, ts=tick.ts)
        return
    if side not in {"CE", "PE"}:
        engine.mark_skip(book_id, underlying, "NO_SIDE", ts=tick.ts)
        return
    entry = tick.ce_close if side == "CE" else tick.pe_close
    path = ce_path if side == "CE" else pe_path
    levels = propose_levels(float(entry), path)
    if not levels.get("ok"):
        engine.mark_skip(
            book_id,
            underlying,
            str(levels.get("reason_code") or "LEVELS_FAIL"),
            feasibility=levels.get("feasibility"),
            ts=tick.ts,
        )
        return
    atm = strike if strike is not None else round_atm_strike(underlying, tick.idx_close)
    pos = OpenPaper(
        book_id=book_id,
        underlying=underlying,
        side=side,
        trade_id=f"paper-{book_id}-{underlying}-{tick.ts}-{side}",
        entry=float(levels["entry"]),
        stop=float(levels["stop"]),
        target=float(levels["target"]),
        atm_strike=atm,
        opened_ts=tick.ts,
        opened_bar=bar_i,
        strike_source=strike_source,
    )
    engine.opens[(book_id, underlying)] = pos


def mark_to_market(engine: BookEngine, tick: Triple, underlying: str, bar_i: int) -> None:
    for book_id in list(LIVE_BOOKS):
        pos = engine.opens.get((book_id, underlying))
        if pos is None:
            continue
        ltp = tick.ce_close if pos.side == "CE" else tick.pe_close
        reason = _exit_reason(pos, float(ltp), tick.ts, bar_i)
        if reason:
            _close(engine, pos, ltp=float(ltp), ts=tick.ts, reason=reason)


def step_underlying(
    engine: BookEngine,
    *,
    underlying: str,
    triples: Sequence[Triple],
    i: int,
    ml001_hold: bool,
    ml002_hold: bool,
    follow_gap: bool,
    logit: dict[str, Any],
    logit_xr: dict[str, Any],
    ml1: dict[str, Any],
    tv_side: Optional[str],
) -> None:
    if i < 1:
        return
    und = underlying.upper()
    tick = triples[i]
    prev = triples[i - 1]
    mark_to_market(engine, tick, und, i)

    idx_d = tick.idx_close - prev.idx_close
    ce_d = tick.ce_close - prev.ce_close
    pe_d = tick.pe_close - prev.pe_close
    dealer = dealer_side(idx_d, ce_d, pe_d, underlying=und)
    dealer_proposal = dealer.get("side") if dealer.get("allow_new_paper_ce_pe") else None
    ce_path = [t.ce_close for t in triples[max(0, i - RANGE_LOOKBACK) : i + 1]]
    pe_path = [t.pe_close for t in triples[max(0, i - RANGE_LOOKBACK) : i + 1]]
    strike = round_atm_strike(und, tick.idx_close)

    # MIX-DEFAULT-BUY — dealer book only. Other HOLDs do not block it.
    _try_open(
        engine,
        book_id="MIX-DEFAULT-BUY",
        underlying=und,
        side=dealer_proposal,
        tick=tick,
        ce_path=ce_path,
        pe_path=pe_path,
        bar_i=i,
        skip_reason=None if dealer_proposal else f"DEALER_{dealer.get('verdict')}",
        strike=strike,
    )
    # ML-001 overlay on the dealer proposal. HOLD → skip this book only.
    ml001_skip = None
    if ml001_hold or follow_gap:
        ml001_skip = "ML-001_HOLD"
    elif not dealer_proposal:
        ml001_skip = "NO_DEALER_TICKET"
    _try_open(
        engine,
        book_id="ML-001",
        underlying=und,
        side=dealer_proposal,
        tick=tick,
        ce_path=ce_path,
        pe_path=pe_path,
        bar_i=i,
        skip_reason=ml001_skip,
        strike=strike,
    )
    ml002_skip = None
    if ml002_hold or follow_gap:
        ml002_skip = "ML-002_HOLD"
    elif not dealer_proposal:
        ml002_skip = "NO_DEALER_TICKET"
    _try_open(
        engine,
        book_id="ML-002",
        underlying=und,
        side=dealer_proposal,
        tick=tick,
        ce_path=ce_path,
        pe_path=pe_path,
        bar_i=i,
        skip_reason=ml002_skip,
        strike=strike,
    )
    ml1_skip = None
    if ml1.get("status") != "OK":
        ml1_skip = str(ml1.get("reason") or "ML-1_DATA_INSUFFICIENT")
    elif ml1.get("take") is False:
        ml1_skip = "ML-1_SKIP"
    elif not dealer_proposal:
        ml1_skip = "NO_DEALER_TICKET"
    _try_open(
        engine,
        book_id="ML-1",
        underlying=und,
        side=dealer_proposal,
        tick=tick,
        ce_path=ce_path,
        pe_path=pe_path,
        bar_i=i,
        skip_reason=ml1_skip,
        strike=strike,
    )
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying=und,
        side=logit.get("side"),
        tick=tick,
        ce_path=ce_path,
        pe_path=pe_path,
        bar_i=i,
        skip_reason=None if logit.get("side") else str(logit.get("reason") or logit.get("status")),
        strike=strike,
    )
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT-XR",
        underlying=und,
        side=logit_xr.get("side"),
        tick=tick,
        ce_path=ce_path,
        pe_path=pe_path,
        bar_i=i,
        skip_reason=None if logit_xr.get("side") else str(logit_xr.get("reason") or logit_xr.get("status")),
        strike=strike,
    )
    _try_open(
        engine,
        book_id="MIX-TV-EP-024",
        underlying=und,
        side=tv_side,
        tick=tick,
        ce_path=ce_path,
        pe_path=pe_path,
        bar_i=i,
        skip_reason=None if tv_side else "TV-EP-024 SMA20 flat or warmup",
        strike=strike,
    )
    engine.last_step = {
        "underlying": und,
        "ts": tick.ts,
        "dealer": dealer,
        "ml001_hold": ml001_hold,
        "ml002_hold": ml002_hold,
        "follow_gap": follow_gap,
        "logit": logit,
        "logit_xr": logit_xr,
        "ml1": ml1,
        "tv_ep_024": tv_side,
        "independent": True,
        "note": "HOLD on one book does not veto another",
    }


def _hold_series(triples: Sequence[Triple], *, seed: int = 14) -> tuple[list[bool], list[bool], list[bool], dict[str, Any]]:
    rows = build_feature_rows(list(triples))
    meta: dict[str, Any] = {"n_feature_rows": len(rows)}
    if len(rows) < 20:
        n = len(triples)
        return [False] * n, [False] * n, [False] * n, {**meta, "status": "DATA_INSUFFICIENT"}
    train = rows[: max(16, int(len(rows) * 0.6))]
    fitted = fit_from_rows(train, seed=seed)
    bundle = pack_estimators(
        scaler=fitted["scaler"],
        kmeans=fitted["kmeans"],
        cluster_labels=fitted["cluster_labels"],
        forest=fitted["forest"],
    )
    idx_rets = [r["idx_ret"] for r in rows]
    k_ce = ols_beta(idx_rets, [r["ce_ret"] for r in rows])
    k_pe = ols_beta(idx_rets, [r["pe_ret"] for r in rows])
    residual: list[float] = []
    if k_ce is not None and k_pe is not None:
        residual = [
            0.5 * ((r["ce_ret"] - k_ce * r["idx_ret"]) + (r["pe_ret"] - k_pe * r["idx_ret"]))
            for r in rows
        ]
    zs = rolling_z(residual, 40) if residual else []
    names = ("idx_ret", "ce_ret", "pe_ret", "spread_chg", "abs_residual")
    by_ts = {int(r["ts"]): r for r in rows}
    ml001: list[bool] = []
    ml002: list[bool] = []
    gap: list[bool] = []
    row_i = -1
    for t in triples:
        feat_row = by_ts.get(int(t.ts))
        if feat_row is None:
            ml001.append(False)
            ml002.append(False)
            gap.append(False)
            continue
        row_i += 1
        feat = {name: float(feat_row[name]) for name in names}
        scored = score_features_dict(feat, bundle)
        g = premium_divergence_pattern(feat_row["idx_ret"], feat_row["ce_ret"], feat_row["pe_ret"])
        z_hold = False
        if row_i < len(zs) and zs[row_i] is not None:
            z_hold = abs(float(zs[row_i])) >= Z_HOLD
        ml001.append(scored.get("overlay") == OVERLAY_HOLD)
        ml002.append(z_hold)
        gap.append(g)
    meta["status"] = "OK"
    return ml001, ml002, gap, meta


def replay_paper_scalp(
    *,
    root: Optional[Path] = None,
    underlyings: Sequence[str] = ("NIFTY", "BANKNIFTY", "SENSEX"),
    source: str = "cache",
    triples_by_und: Optional[dict[str, list[Triple]]] = None,
    write: bool = False,
) -> dict[str, Any]:
    base = root or repo_root()
    engine = BookEngine()
    tapes: dict[str, Any] = {}
    steps: dict[str, Any] = {}
    src = (source or "cache").strip().lower()
    now = datetime.now(IST)

    for und in underlyings:
        u = und.upper()
        if triples_by_und is not None:
            triples, tape = triples_by_und.get(u, []), {"source": "caller", "aligned_triples": len(triples_by_und.get(u, []))}
        elif src in {"dual-tape", "dual_tape"}:
            triples, tape = load_dual_tape_triples(u, root=base)
        else:
            triples, tape = load_triples(u, root=base)
        tapes[u] = tape
        if len(triples) < 8:
            steps[u] = {
                "status": "DATA_INSUFFICIENT",
                "reason": "need ≥8 aligned INDEX+ATM 1m triples; do not fabricate bars",
                "tape": tape,
            }
            continue
        ml001, ml002, gap, hold_meta = _hold_series(triples)
        idx_closes = load_index_closes(u, root=base)
        if triples_by_und is not None:
            idx_closes = {int(t.ts): float(t.idx_close) for t in triples}
        logit_series, logit_meta = logit_side_series(triples, index_closes=idx_closes, xr=False)
        logit_xr_series, logit_xr_meta = logit_side_series(triples, index_closes=idx_closes, xr=True)
        thin_logit = {
            "side": None,
            "status": "DATA_INSUFFICIENT",
            "reason": "no logit series",
        }
        idx_path: list[float] = []
        for i, tick in enumerate(triples):
            idx_path.append(tick.idx_close)
            h1 = ml001[i] if i < len(ml001) else False
            h2 = ml002[i] if i < len(ml002) else False
            g = gap[i] if i < len(gap) else False
            tv = tv_ep_024_side(idx_path)
            logit = logit_series[i] if i < len(logit_series) else thin_logit
            logit_xr = logit_xr_series[i] if i < len(logit_xr_series) else thin_logit
            # Recompute ML-1 as closes accumulate (still DI until 30).
            ml1 = ml1_meta_label(engine.closed)
            step_underlying(
                engine,
                underlying=u,
                triples=triples,
                i=i,
                ml001_hold=h1,
                ml002_hold=h2,
                follow_gap=g,
                logit=logit,
                logit_xr=logit_xr,
                ml1=ml1,
                tv_side=tv,
            )
        # Flatten leftovers at last tick.
        last = triples[-1]
        for book_id in LIVE_BOOKS:
            pos = engine.opens.get((book_id, u))
            if pos is None:
                continue
            ltp = last.ce_close if pos.side == "CE" else last.pe_close
            _close(engine, pos, ltp=float(ltp), ts=last.ts, reason="REPLAY_END")
        steps[u] = {
            "status": "REPLAY_OK",
            "n_triples": len(triples),
            "hold_meta": hold_meta,
            "logit": logit_meta,
            "logit_xr": logit_xr_meta,
            "ml1": ml1,
            "tape": tape,
            "span_ist": {
                "first": _ist_dt(triples[0].ts).isoformat(timespec="seconds"),
                "last": _ist_dt(triples[-1].ts).isoformat(timespec="seconds"),
            },
        }

    board = build_dashboard(
        engine,
        tapes=tapes,
        steps=steps,
        as_of_ist=now.isoformat(timespec="seconds"),
        source=src,
        root=base,
    )
    if write:
        write_dashboard(board, root=base)
    return board


def _book_what(book_id: str) -> str:
    return {
        "MIX-DEFAULT-BUY": "Dealer CE/PE from INDEX vs ATM CE/PE deltas. Customer default ID; PAPER only.",
        "ML-001": "KMeans+IsolationForest overlay. SKIP if HOLD/FOLLOW-GAP. Does not invent CE/PE.",
        "ML-002": "OU residual |z|≥2 or FOLLOW-GAP SKIP. Windows 40/60/90. Does not invent CE/PE.",
        "ML-1": "Meta-label take/skip on closed paper labels. Else DATA_INSUFFICIENT.",
        "MIX-ML-LOGIT": "INDEX 3m walk-forward logit (ml_leans.py). Scan book. Not customer default.",
        "MIX-ML-LOGIT-XR": "Logit AND range-expansion. Scan book. Not customer default.",
        "MIX-TV-EP-024": "Factory SMA20 INDEX calibrator → ATM CE/PE. KEEP_ALL lab. Not a promote.",
    }.get(book_id, book_id)


def leaderboard_closed(closed: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[float]] = {}
    for row in closed:
        key = (str(row["book_id"]), str(row["underlying"]))
        buckets.setdefault(key, []).append(float(row["realized_pnl"]))
    out = []
    for (book, und), pnls in sorted(buckets.items()):
        out.append(
            {
                "book_id": book,
                "underlying": und,
                "n_closed": len(pnls),
                "sum_premium_pnl": round(sum(pnls), 4),
                "n_wins": sum(1 for p in pnls if p > 0),
                "win_rate": paper_hit_rate(pnls),
                "win_rate_kind": "paper_closed_premium_gt_0",
                "rank_metric": "closed_premium_pnl_only",
            }
        )
    out.sort(key=lambda r: r["sum_premium_pnl"], reverse=True)
    return out


def build_dashboard(
    engine: BookEngine,
    *,
    tapes: dict[str, Any],
    steps: dict[str, Any],
    as_of_ist: str,
    source: str,
    root: Path,
) -> dict[str, Any]:
    inv = inventory_recon(root=root, calendar_days=21, underlyings=("NIFTY", "BANKNIFTY", "SENSEX"))
    index_gap = list(inv.get("data_gaps") or [])
    tv_inventory = []
    for mix in TV_EP_KEEP_ALL:
        bound = mix == "MIX-TV-EP-024"
        shortlist = mix in TV_EP_SHORTLIST
        tv_inventory.append(
            {
                "book_id": mix,
                "live_paper_scalp": bound,
                "paper_tune_shortlist": shortlist,
                "note": (
                    "SMA calibrator bound as scalp book"
                    if bound
                    else (
                        "Fired MOCK tickets in TV-EP paper-tune (INDEX proxy ≠ this board)"
                        if shortlist
                        else "KEEP_ALL catalog. Not a live scalp book this CLI."
                    )
                ),
            }
        )
    models = []
    for book_id in LIVE_BOOKS:
        closed_b = [c for c in engine.closed if c["book_id"] == book_id]
        open_b = [asdict(p) for (b, _u), p in engine.opens.items() if b == book_id]
        pnls = [float(c["realized_pnl"]) for c in closed_b]
        models.append(
            {
                "model_id": book_id,
                "what": _book_what(book_id),
                "last_run_ist": as_of_ist,
                "open": open_b,
                "n_closed": len(closed_b),
                "n_open": len(open_b),
                "n_wins": sum(1 for p in pnls if p > 0),
                "sum_closed_premium_pnl": round(sum(pnls), 4) if pnls else 0.0,
                "win_rate": paper_hit_rate(pnls),
                "win_rate_kind": "paper_closed_premium_gt_0",
            }
        )
    open_rows = [asdict(p) for p in engine.opens.values()]
    all_pnls = [float(c["realized_pnl"]) for c in engine.closed]
    return {
        "ok": True,
        "job": "ML_PAPER_SCALP",
        "as_of_ist": as_of_ist,
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "promote": False,
        "production_params_written": False,
        "research_ready_for_programming": False,
        "execution": "refused",
        "orders": "REFUSED",
        "llm": False,
        "win_rate": paper_hit_rate(all_pnls),
        "win_rate_kind": "paper_closed_premium_gt_0",
        "n_closed": len(all_pnls),
        "n_wins": sum(1 for p in all_pnls if p > 0),
        "source": source,
        "customer_mix": "MIX-DEFAULT-BUY unchanged (dealer book is PAPER parallel, not a live rewrite)",
        "independent_books": True,
        "one_open_per": "book_id × underlying",
        "scalper_exits": {
            "stop": f"long premium LTP <= entry - {STOP_FRAC}×same-side path range",
            "target": f"LTP >= entry + {TARGET_FRAC}×path range",
            "time": f"{SCALP_HOLD_BARS} 1m bars",
            "flatten_ist": "15:00",
            "feasibility": "warehouse.feasibility.evaluate_long_premium",
            "fantasy_lesson": "150/96/250 TARGET_FEASIBILITY_FAIL",
        },
        "models": models,
        "steps": steps,
        "data_pulled": tapes,
        "inventory": {
            "index_1m": inv.get("index_1m"),
            "premium_tape": inv.get("premium_tape"),
            "joins": inv.get("joins"),
            "data_gaps": index_gap,
        },
        "open_trades": open_rows,
        "closed_trades": engine.closed,
        "leaderboard": leaderboard_closed(engine.closed),
        "tv_ep_inventory": tv_inventory,
        "heartbeat": {
            "cli": "python -m desk_ml paper-scalp --replay",
            "loop": "python -m desk_ml paper-scalp --loop  (opt-in; writes this JSON)",
            "stop": f"touch data/recon/{STOP_FLAG_NAME}",
            "does_not_start": ["paper_ops", "npm", "legacy LLM waiters"],
        },
        "honesty": [
            "Closed option-premium P/L only ranks. Open rows do not.",
            "win_rate is paper closed-trade hit rate (pnl>0 / n_closed), not a live claim. NO_PROMOTE.",
            "INDEX 1m is warehouse∪JSON. ATM days without INDEX 1m stay DATA_INSUFFICIENT — never filled bars.",
            "ML-001 inverted HOLD on NIFTY stays a SKIP overlay, still run in parallel.",
        ],
    }


def write_dashboard(board: dict[str, Any], *, root: Optional[Path] = None) -> dict[str, str]:
    base = root or repo_root()
    recon = base / "data" / "recon"
    recon.mkdir(parents=True, exist_ok=True)
    json_path = recon / DASH_JSON_NAME
    json_path.write_text(json.dumps(board, indent=2, default=str) + "\n", encoding="utf-8")
    md = render_markdown(board)
    md_path = base / DASH_MD_REL
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    mock = base / MOCK_JSON_REL
    mock.parent.mkdir(parents=True, exist_ok=True)
    compact = {
        k: board.get(k)
        for k in (
            "ok",
            "job",
            "as_of_ist",
            "gate",
            "promote",
            "win_rate",
            "win_rate_kind",
            "n_closed",
            "n_wins",
            "source",
            "independent_books",
            "scalper_exits",
            "models",
            "leaderboard",
            "heartbeat",
            "honesty",
            "execution",
            "orders",
            "customer_mix",
        )
    }
    compact["inventory"] = {"data_gaps": (board.get("inventory") or {}).get("data_gaps")}
    compact["steps"] = {
        u: {kk: vv for kk, vv in (s or {}).items() if kk in {"status", "n_triples", "span_ist", "logit", "ml1"}}
        for u, s in (board.get("steps") or {}).items()
    }
    compact["n_closed"] = len(board.get("closed_trades") or [])
    compact["n_open"] = len(board.get("open_trades") or [])
    compact["closed_trades_sample"] = (board.get("closed_trades") or [])[-12:]
    compact["open_trades"] = board.get("open_trades") or []
    compact["note"] = "Compact mock. Full closed tape is data/recon/ml_paper_dashboard.json (gitignored)."
    mock.write_text(json.dumps(compact, indent=2, default=str) + "\n", encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path), "mock": str(mock)}


def render_markdown(board: dict[str, Any]) -> str:
    lines = [
        "# ML / paper scalper monitoring board",
        "",
        f"**As of (IST):** `{board.get('as_of_ist')}`  ",
        f"**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** Orders refused. "
        f"paper `win_rate`={board.get('win_rate')} ({board.get('n_wins')}/{board.get('n_closed')} closed, pnl>0).",
        "",
        "Parallel independent books: one OPEN per (`book_id` × underlying). A HOLD on ML-001 does **not** block MIX-DEFAULT-BUY.",
        "",
        "## Leaderboard (CLOSED premium P/L only)",
        "",
        "| book | underlying | n_closed | sum premium P/L | win_rate |",
        "|------|------------|----------|-----------------|----------|",
    ]
    for row in board.get("leaderboard") or []:
        lines.append(
            f"| `{row['book_id']}` | {row['underlying']} | {row['n_closed']} | {row['sum_premium_pnl']} | {row.get('win_rate')} |"
        )
    if not board.get("leaderboard"):
        lines.append("| — | — | 0 | — | — |")
    lines += [
        "",
        "PAPER cache replay only (aligned INDEX∩ATM 1m on disk, typically 2026-09-09..10). "
        "Not fills. Rank ≠ promote. `MIX-ML-LOGIT*` trains on INDEX 3m before the ATM session. "
        "`win_rate` = paper closed hit rate (pnl>0), not a promote. "
        "`MIX-TV-EP-024` SMA lab is KEEP_ALL, not customer default.",
        "",
        "",
        "## Models / steps",
        "",
        "| id | what | closed | wr | last run |",
        "|----|------|--------|----|----------|",
    ]
    for m in board.get("models") or []:
        lines.append(
            f"| `{m['model_id']}` | {m['what']} | {m['n_closed']} | {m.get('win_rate')} | `{m['last_run_ist']}` |"
        )
    lines += ["", "## DATA_INSUFFICIENT", ""]
    gaps = (board.get("inventory") or {}).get("data_gaps") or []
    if not gaps:
        lines.append("- (none on this inventory pass)")
    for g in gaps:
        lines.append(f"- {g}")
    lines += [
        "",
        "## How to watch",
        "",
        "```bash",
        "python -m desk_ml paper-scalp --replay",
        "# opt-in loop (does not start paper_ops / npm):",
        "python -m desk_ml paper-scalp --loop --tick-seconds 45",
        "touch data/recon/ml_paper_scalp_STOPPED.flag",
        "```",
        "",
        "JSON: `data/recon/ml_paper_dashboard.json` (gitignored) · mock: `apps/web/public/mock/ml_paper_dashboard.json`  ",
        "UI: `/pm` and `/desk` (existing Vite; do not restart npm). API: `GET /paper/ml-books`.",
        "",
        "KEEP_ALL STRAT-001–014. No STRAT-015+.",
        "",
    ]
    return "\n".join(lines) + "\n"


def stop_requested(root: Path) -> bool:
    return (root / "data" / "recon" / STOP_FLAG_NAME).is_file()


def run_loop(
    *,
    root: Optional[Path] = None,
    tick_seconds: int = 45,
    max_ticks: int = 0,
    sleep_fn: Optional[Callable[[float], None]] = None,
    source: str = "dual-tape",
) -> dict[str, Any]:
    """Opt-in. Writes heartbeat into dashboard JSON. Does not arm paper_ops."""
    import time

    sleep = sleep_fn or time.sleep
    base = root or repo_root()
    i = 0
    last: dict[str, Any] = {}
    while True:
        if stop_requested(base):
            last = replay_paper_scalp(root=base, source=source, write=True)
            last["loop_stopped"] = "ml_paper_scalp_STOPPED.flag"
            write_dashboard(last, root=base)
            return last
        last = replay_paper_scalp(root=base, source=source, write=True)
        last["heartbeat"] = {
            **(last.get("heartbeat") or {}),
            "tick_index": i,
            "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
            "alive": True,
        }
        write_dashboard(last, root=base)
        i += 1
        if max_ticks > 0 and i >= max_ticks:
            last["loop_stopped"] = "completed_max_ticks"
            return last
        sleep(float(tick_seconds))

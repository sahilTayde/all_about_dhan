"""PROJECT-DERIVED INDEX vs CE vs PE formulas (02 math).

Named overlays for ML-001 features and dual-tape dealer. Not greeks, not IV,
not a neural net, not live alpha. NO_PROMOTE. Holiday/empty cache → DATA_INSUFFICIENT.

Formulas:
  MIX-FORM-BETA-RESID   residual = opt_ret - k * index_ret
  MIX-FORM-DIVERGE-Z    z-score of that residual
  MIX-FORM-STRADDLE-RET ce_ret + pe_ret  (vol-expansion proxy; not IV)
  MIX-FORM-FOLLOW-GAP   index-down & PE not up / index-up & CE not up
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

IST = timezone(timedelta(hours=5, minutes=30))
EPS = 1e-12
INDEX_RET_EPS = 1e-5  # ~0.001% on NIFTY 1m; ignore microstructure
PREMIUM_RET_EPS = 1e-4
DEFAULT_Z_WINDOW = 30
FORMULA_IDS = (
    "MIX-FORM-BETA-RESID",
    "MIX-FORM-DIVERGE-Z",
    "MIX-FORM-STRADDLE-RET",
    "MIX-FORM-FOLLOW-GAP",
)
ORIGIN = "PROJECT-DERIVED"
LAYER = "HYPOTHESIS"


@dataclass(frozen=True)
class CloseBar:
    ts: int
    close: float


def simple_return(prev: float, cur: float) -> Optional[float]:
    if abs(prev) < EPS:
        return None
    return (cur - prev) / abs(prev)


def pearson_corr(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = min(len(xs), len(ys))
    if n < 3:
        return None
    mx = sum(xs[:n]) / n
    my = sum(ys[:n]) / n
    num = 0.0
    dx = 0.0
    dy = 0.0
    for i in range(n):
        a = xs[i] - mx
        b = ys[i] - my
        num += a * b
        dx += a * a
        dy += b * b
    den = math.sqrt(dx * dy)
    if den < EPS:
        return None
    return num / den


def ols_beta(index_rets: Sequence[float], option_rets: Sequence[float]) -> Optional[float]:
    """k in option_ret ≈ k * index_ret (no intercept). k = Σxy / Σx²."""
    n = min(len(index_rets), len(option_rets))
    if n < 3:
        return None
    xx = 0.0
    xy = 0.0
    for i in range(n):
        x = index_rets[i]
        y = option_rets[i]
        xx += x * x
        xy += x * y
    if xx < EPS:
        return None
    return xy / xx


def mix_form_beta_resid(
    index_ret: float,
    option_ret: float,
    k: float,
) -> float:
    """MIX-FORM-BETA-RESID: r_opt − k · r_idx."""
    return option_ret - k * index_ret


def rolling_mean_std(values: Sequence[float], *, end: int, window: int) -> tuple[Optional[float], Optional[float]]:
    start = max(0, end - window + 1)
    chunk = values[start : end + 1]
    if len(chunk) < 3:
        return None, None
    m = sum(chunk) / len(chunk)
    var = sum((v - m) ** 2 for v in chunk) / (len(chunk) - 1)
    if var < EPS:
        return m, None
    return m, math.sqrt(var)


def mix_form_diverge_z(
    residual: float,
    history: Sequence[float],
    *,
    window: int = DEFAULT_Z_WINDOW,
) -> Optional[float]:
    """MIX-FORM-DIVERGE-Z: (resid − mean) / std on trailing history only.

    Current residual is the *score*, not a member of the window (AFML: no same-bar leak).
    """
    if len(history) < 3:
        return None
    m, s = rolling_mean_std(history, end=len(history) - 1, window=window)
    if m is None or s is None:
        return None
    return (residual - m) / s


def mix_form_straddle_ret(ce_ret: float, pe_ret: float) -> float:
    """MIX-FORM-STRADDLE-RET: r_CE + r_PE. Not implied vol."""
    return ce_ret + pe_ret


def mix_form_follow_gap(
    *,
    index_ret: float,
    ce_ret: float,
    pe_ret: float,
    index_eps: float = INDEX_RET_EPS,
    premium_eps: float = PREMIUM_RET_EPS,
) -> dict[str, Any]:
    """MIX-FORM-FOLLOW-GAP flags. Dealer-style: PE should rise when index falls."""
    idx_down = index_ret < -index_eps
    idx_up = index_ret > index_eps
    pe_up = pe_ret > premium_eps
    pe_not_up = pe_ret <= 0.0
    ce_up = ce_ret > premium_eps
    ce_not_up = ce_ret <= 0.0
    pe_div = bool(idx_down and pe_not_up)
    ce_div = bool(idx_up and ce_not_up)
    pe_follow = bool(idx_down and pe_up)
    ce_follow = bool(idx_up and ce_up)
    return {
        "formula_id": "MIX-FORM-FOLLOW-GAP",
        "index_down": idx_down,
        "index_up": idx_up,
        "pe_divergence": pe_div,
        "ce_divergence": ce_div,
        "pe_follow": pe_follow,
        "ce_follow": ce_follow,
        "any_divergence": pe_div or ce_div,
    }


def align_closes(
    index: Sequence[CloseBar],
    ce: Sequence[CloseBar],
    pe: Sequence[CloseBar],
) -> list[tuple[int, float, float, float]]:
    """Inner join on exact epoch seconds (Dhan chart timestamps)."""
    ce_map = {b.ts: b.close for b in ce}
    pe_map = {b.ts: b.close for b in pe}
    out: list[tuple[int, float, float, float]] = []
    for bar in index:
        c = ce_map.get(bar.ts)
        p = pe_map.get(bar.ts)
        if c is None or p is None:
            continue
        if c <= 0 or p <= 0 or bar.close <= 0:
            continue
        out.append((bar.ts, bar.close, c, p))
    return out


def returns_from_aligned(
    aligned: Sequence[tuple[int, float, float, float]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prev: Optional[tuple[int, float, float, float]] = None
    for row in aligned:
        if prev is None:
            prev = row
            continue
        ir = simple_return(prev[1], row[1])
        cr = simple_return(prev[2], row[2])
        pr = simple_return(prev[3], row[3])
        if ir is None or cr is None or pr is None:
            prev = row
            continue
        rows.append(
            {
                "ts": row[0],
                "index_ret": ir,
                "ce_ret": cr,
                "pe_ret": pr,
                "index_close": row[1],
                "ce_close": row[2],
                "pe_close": row[3],
            }
        )
        prev = row
    return rows


def ist_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=IST)


def session_date_ist(ts: int) -> str:
    return ist_dt(ts).date().isoformat()


def is_morning(ts: int) -> bool:
    t = ist_dt(ts).time()
    return time(9, 15) <= t < time(10, 30)


def is_nifty_expiry_week_session(ts: int, expiry_tuesdays: Sequence[str]) -> bool:
    """Mon/Tue of a listed NIFTY weekly Tuesday (FROM_CONTRACT vintage, not frozen)."""
    d = ist_dt(ts)
    day = d.date().isoformat()
    wd = d.weekday()  # Mon=0
    if wd not in (0, 1):
        return False
    return any(abs((d.date() - datetime.fromisoformat(exp).date()).days) <= 1 for exp in expiry_tuesdays)


def apply_named_formulas(
    rows: Sequence[dict[str, Any]],
    *,
    z_window: int = DEFAULT_Z_WINDOW,
) -> list[dict[str, Any]]:
    """Attach k (full-sample OLS — EDA only; paper overlay uses expanding k), residuals, causal z, straddle, follow-gap."""
    if len(rows) < 3:
        return []
    idx = [float(r["index_ret"]) for r in rows]
    ce = [float(r["ce_ret"]) for r in rows]
    pe = [float(r["pe_ret"]) for r in rows]
    k_pe = ols_beta(idx, pe)
    k_ce = ols_beta(idx, ce)
    if k_pe is None or k_ce is None:
        return []
    out: list[dict[str, Any]] = []
    pe_resid_hist: list[float] = []
    ce_resid_hist: list[float] = []
    for r, ir, cr, pr in zip(rows, idx, ce, pe):
        pe_resid = mix_form_beta_resid(ir, pr, k_pe)
        ce_resid = mix_form_beta_resid(ir, cr, k_ce)
        pe_z = mix_form_diverge_z(pe_resid, pe_resid_hist, window=z_window)
        ce_z = mix_form_diverge_z(ce_resid, ce_resid_hist, window=z_window)
        pe_resid_hist.append(pe_resid)
        ce_resid_hist.append(ce_resid)
        gap = mix_form_follow_gap(index_ret=ir, ce_ret=cr, pe_ret=pr)
        item = dict(r)
        item.update(
            {
                "k_pe": k_pe,
                "k_ce": k_ce,
                "pe_resid": pe_resid,
                "ce_resid": ce_resid,
                "pe_diverge_z": pe_z,
                "ce_diverge_z": ce_z,
                "straddle_ret": mix_form_straddle_ret(cr, pr),
                **{f"gap_{k}": v for k, v in gap.items() if k != "formula_id"},
            }
        )
        out.append(item)
    return out


def summarize_eda(
    rows: Sequence[dict[str, Any]],
    *,
    labelled: Sequence[dict[str, Any]],
    source: str,
    n_index: int,
    n_ce: int,
    n_pe: int,
    n_aligned: int,
    ce_sid: str,
    pe_sid: str,
    first_ts: Optional[int],
    last_ts: Optional[int],
    expiry_tuesdays: Sequence[str],
) -> dict[str, Any]:
    if not rows:
        return {
            "ok": False,
            "data_gaps": ["DATA_INSUFFICIENT: no aligned 1m INDEX+CE+PE returns"],
            "source": source,
            "n_index": n_index,
            "n_ce": n_ce,
            "n_pe": n_pe,
            "n_aligned": n_aligned,
        }
    idx = [float(r["index_ret"]) for r in rows]
    ce = [float(r["ce_ret"]) for r in rows]
    pe = [float(r["pe_ret"]) for r in rows]
    k_pe = ols_beta(idx, pe)
    k_ce = ols_beta(idx, ce)
    pe_resid = [mix_form_beta_resid(i, p, k_pe) for i, p in zip(idx, pe)] if k_pe is not None else []
    n_idx_down = sum(1 for i in idx if i < -INDEX_RET_EPS)
    n_idx_up = sum(1 for i in idx if i > INDEX_RET_EPS)
    pe_div_n = sum(1 for i, p in zip(idx, pe) if i < -INDEX_RET_EPS and p <= 0.0)
    ce_div_n = sum(1 for i, c in zip(idx, ce) if i > INDEX_RET_EPS and c <= 0.0)
    pe_follow_n = sum(1 for i, p in zip(idx, pe) if i < -INDEX_RET_EPS and p > PREMIUM_RET_EPS)
    ce_follow_n = sum(1 for i, c in zip(idx, ce) if i > INDEX_RET_EPS and c > PREMIUM_RET_EPS)

    def _slice(pred) -> dict[str, Any]:
        sub_idx = [r["index_ret"] for r in rows if pred(r)]
        sub_ce = [r["ce_ret"] for r in rows if pred(r)]
        sub_pe = [r["pe_ret"] for r in rows if pred(r)]
        if len(sub_idx) < 3:
            return {"n": len(sub_idx), "note": "DATA_INSUFFICIENT"}
        nd = sum(1 for i in sub_idx if i < -INDEX_RET_EPS)
        nu = sum(1 for i in sub_idx if i > INDEX_RET_EPS)
        return {
            "n": len(sub_idx),
            "corr_index_ce": pearson_corr(sub_idx, sub_ce),
            "corr_index_pe": pearson_corr(sub_idx, sub_pe),
            "k_pe": ols_beta(sub_idx, sub_pe),
            "k_ce": ols_beta(sub_idx, sub_ce),
            "pe_div_rate_given_idx_down": (sum(1 for i, p in zip(sub_idx, sub_pe) if i < -INDEX_RET_EPS and p <= 0.0) / nd)
            if nd
            else None,
            "ce_div_rate_given_idx_up": (sum(1 for i, c in zip(sub_idx, sub_ce) if i > INDEX_RET_EPS and c <= 0.0) / nu)
            if nu
            else None,
        }

    morning = _slice(lambda r: is_morning(int(r["ts"])))
    expiry = _slice(lambda r: is_nifty_expiry_week_session(int(r["ts"]), expiry_tuesdays))
    z_abs_pe = [abs(x["pe_diverge_z"]) for x in labelled if x.get("pe_diverge_z") is not None]
    return {
        "ok": True,
        "layer": LAYER,
        "origin": ORIGIN,
        "promote": False,
        "source": source,
        "ce_security_id": ce_sid,
        "pe_security_id": pe_sid,
        "n_index": n_index,
        "n_ce": n_ce,
        "n_pe": n_pe,
        "n_aligned": n_aligned,
        "n_return_bars": len(rows),
        "first_ist": ist_dt(first_ts).isoformat() if first_ts else None,
        "last_ist": ist_dt(last_ts).isoformat() if last_ts else None,
        "corr_index_ce": pearson_corr(idx, ce),
        "corr_index_pe": pearson_corr(idx, pe),
        "k_pe": k_pe,
        "k_ce": k_ce,
        "pe_resid_mean": (sum(pe_resid) / len(pe_resid)) if pe_resid else None,
        "pe_resid_std": (
            math.sqrt(sum((v - (sum(pe_resid) / len(pe_resid))) ** 2 for v in pe_resid) / (len(pe_resid) - 1))
            if len(pe_resid) > 1
            else None
        ),
        "n_index_down": n_idx_down,
        "n_index_up": n_idx_up,
        "pe_divergence_count": pe_div_n,
        "ce_divergence_count": ce_div_n,
        "pe_div_rate_given_idx_down": (pe_div_n / n_idx_down) if n_idx_down else None,
        "ce_div_rate_given_idx_up": (ce_div_n / n_idx_up) if n_idx_up else None,
        "pe_follow_rate_given_idx_down": (pe_follow_n / n_idx_down) if n_idx_down else None,
        "ce_follow_rate_given_idx_up": (ce_follow_n / n_idx_up) if n_idx_up else None,
        "mean_straddle_ret": sum(mix_form_straddle_ret(c, p) for c, p in zip(ce, pe)) / len(rows),
        "morning": morning,
        "expiry_week_mon_tue": expiry,
        "expiry_tuesdays_used": list(expiry_tuesdays),
        "diverge_z_pe_mean_abs": (sum(z_abs_pe) / len(z_abs_pe)) if z_abs_pe else None,
        "formula_ids": list(FORMULA_IDS),
        "note": "Rates are contemporaneous 1m prints, not P/L and not a win rate.",
    }


def bars_from_chart(payload: dict) -> list[CloseBar]:
    opens = payload.get("open") or []
    highs = payload.get("high") or []
    lows = payload.get("low") or []
    closes = payload.get("close") or []
    vols = payload.get("volume") or []
    ts = payload.get("timestamp") or []
    n = min(len(opens), len(highs), len(lows), len(closes), len(vols), len(ts))
    return [CloseBar(ts=int(ts[i]), close=float(closes[i])) for i in range(n)]


def load_ohlc_closes(cache_dir: Path, prefix: str) -> list[CloseBar]:
    merged: dict[int, CloseBar] = {}
    for path in sorted(cache_dir.glob(f"{prefix}*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        for bar in bars_from_chart(raw):
            merged[bar.ts] = bar
    return [merged[k] for k in sorted(merged)]


def load_tape_side(tape_dir: Path, underlying: str, side: str) -> list[CloseBar]:
    merged: dict[int, CloseBar] = {}
    for path in sorted(tape_dir.glob(f"{underlying}_ATM_1m_*.json")):
        blob = json.loads(path.read_text(encoding="utf-8"))
        for row in blob.get(side) or []:
            ts = int(row.get("ts") or 0)
            if not ts:
                continue
            merged[ts] = CloseBar(ts=ts, close=float(row["close"]))
    return [merged[k] for k in sorted(merged)]


def default_expiry_tuesdays() -> list[str]:
    """NIFTY weekly Tuesdays overlapping this cache vintage (03: FROM_CONTRACT)."""
    return [
        "2026-08-18",
        "2026-08-25",
        "2026-09-01",
        "2026-09-08",
        "2026-09-15",
    ]


def run_cache_eda(root: Optional[Path] = None) -> dict[str, Any]:
    """Historical cache only. No Dhan fetch. Ganesh Chaturthi 2026-09-14 holiday."""
    repo = root or Path(__file__).resolve().parents[4]
    ohlc = repo / "data" / "recon" / "ohlc"
    tape = repo / "data" / "recon" / "premium_tape"
    expiries = default_expiry_tuesdays()
    reports: list[dict[str, Any]] = []

    index = load_ohlc_closes(ohlc, "INDEX_IDX_I_13_1_") if ohlc.is_dir() else []
    pairs = [
        ("ohlc_23350CE_47291_vs_23500PE_47298", "47291", "47298"),
        ("ohlc_23350CE_47291_vs_23400PE_47294", "47291", "47294"),
        # 47297 sits between 23450 PE (47296) and 23500 PE (47298) → 23500 CE.
        ("ohlc_23500CE_47297_vs_23500PE_47298", "47297", "47298"),
    ]
    for name, ce_sid, pe_sid in pairs:
        ce = load_ohlc_closes(ohlc, f"OPTIDX_NSE_FNO_{ce_sid}_1_")
        pe = load_ohlc_closes(ohlc, f"OPTIDX_NSE_FNO_{pe_sid}_1_")
        aligned = align_closes(index, ce, pe)
        rows = returns_from_aligned(aligned)
        labelled = apply_named_formulas(rows)
        reports.append(
            summarize_eda(
                rows,
                labelled=labelled,
                source=name,
                n_index=len(index),
                n_ce=len(ce),
                n_pe=len(pe),
                n_aligned=len(aligned),
                ce_sid=ce_sid,
                pe_sid=pe_sid,
                first_ts=aligned[0][0] if aligned else None,
                last_ts=aligned[-1][0] if aligned else None,
                expiry_tuesdays=expiries,
            )
        )

    ce_t = load_tape_side(tape, "NIFTY", "ce") if tape.is_dir() else []
    pe_t = load_tape_side(tape, "NIFTY", "pe") if tape.is_dir() else []
    aligned_t = align_closes(index, ce_t, pe_t)
    rows_t = returns_from_aligned(aligned_t)
    labelled_t = apply_named_formulas(rows_t)
    reports.append(
        summarize_eda(
            rows_t,
            labelled=labelled_t,
            source="premium_tape_NIFTY_ATM",
            n_index=len(index),
            n_ce=len(ce_t),
            n_pe=len(pe_t),
            n_aligned=len(aligned_t),
            ce_sid="ATM_rolling",
            pe_sid="ATM_rolling",
            first_ts=aligned_t[0][0] if aligned_t else None,
            last_ts=aligned_t[-1][0] if aligned_t else None,
            expiry_tuesdays=expiries,
        )
    )
    # ATM CE+PE tape without INDEX (09-09..11 vs INDEX last print 09-03).
    ce_map = {b.ts: b.close for b in ce_t}
    pe_only_rows: list[dict[str, float]] = []
    prev: Optional[tuple[int, float, float]] = None
    for b in pe_t:
        if b.ts not in ce_map:
            continue
        cur = (b.ts, ce_map[b.ts], b.close)
        if prev is None:
            prev = cur
            continue
        cr = simple_return(prev[1], cur[1])
        pr = simple_return(prev[2], cur[2])
        if cr is not None and pr is not None:
            pe_only_rows.append({"ts": float(cur[0]), "ce_ret": cr, "pe_ret": pr})
        prev = cur
    corr_ce_pe_tape = (
        pearson_corr([r["ce_ret"] for r in pe_only_rows], [r["pe_ret"] for r in pe_only_rows])
        if pe_only_rows
        else None
    )

    return {
        "as_of_holiday": "2026-09-14",
        "holiday_note": "Ganesh Chaturthi — historical cache only; no live Dhan.",
        "index_security_id": "13",
        "index_first_ist": ist_dt(index[0].ts).isoformat() if index else None,
        "index_last_ist": ist_dt(index[-1].ts).isoformat() if index else None,
        "n_index": len(index),
        "tape_ce_pe_bars": len(pe_only_rows),
        "tape_corr_ce_pe": corr_ce_pe_tape,
        "tape_index_overlap": reports[-1] if reports else None,
        "reports": reports,
        "formulas": list(FORMULA_IDS),
        "desk_ml_note": "ML-001 KMeans/IsolationForest lives in packages/desk-ml — not rewritten here.",
        "win_rate": None,
        "greeks": None,
        "iv": None,
    }

"""Fill-path observer family: ALLOW / VETO / PASS. No own CE/PE.

SOD: picker proposes one wing, then one observer review, then desk. Not owned
by dealer. Not ML-001 family. STRAT-001–014 vote earlier; they do not fill here.
ATM / missing ITM → PASS. VETO = do not send to desk. NO_PROMOTE.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from desk_ml.features import Triple, EPS
from desk_ml.model import IDX_FLAT, PREM_FLAT

ACTION_ALLOW = "ALLOW"
ACTION_VETO = "VETO"
ACTION_PASS = "PASS"

REASON_NO_SIDE = "OBSERVER_PASS_NO_SIDE"
REASON_ATM = "OBSERVER_PASS_ATM_DAY"
REASON_NO_ITM = "OBSERVER_PASS_NO_ITM"
REASON_STRIKE_ROLL = "OBSERVER_PASS_STRIKE_ROLL"
REASON_NO_1M = "OBSERVER_PASS_WAIT_1M"
REASON_FLAT = "OBSERVER_PASS_INDEX_FLAT"
REASON_ALLOW = "OBSERVER_ALLOW_ITM_CONFIRMS"
REASON_FOLLOW_GAP = "FOLLOW_GAP"
REASON_WING_DEAD = REASON_FOLLOW_GAP  # same rule: ITM wing did not confirm the 1m index
REASON_INDEX_AGAINST = "OBSERVER_VETO_INDEX_AGAINST"
REASON_SELF = "OBSERVER_VETO_SIGNAL_SELF_CONTRADICT"


def _ret(prev: Optional[float], cur: Optional[float]) -> Optional[float]:
    if prev is None or cur is None:
        return None
    if abs(float(prev)) < EPS:
        return None
    return (float(cur) - float(prev)) / abs(float(prev))


def _kind(bar: Triple) -> str:
    return str(getattr(bar, "premium_kind", None) or "").strip().upper()


def _same_strike(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) < 1e-6


def signal_expected_dir(
    side: str,
    *,
    classified: Optional[dict[str, Any]] = None,
    dealer: Optional[dict[str, Any]] = None,
    logit: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """What the fill book is claiming. Missing fields stay UNKNOWN — never guessed."""
    cl = classified or {}
    impulse = cl.get("last3_impulse") or cl.get("last3_impulse_raw")
    idx_dir = cl.get("index_direction") or cl.get("direction")
    want = "UP" if side == "CE" else "DOWN" if side == "PE" else None
    seen = impulse or idx_dir
    dealer_side = (dealer or {}).get("side")
    logit_side = (logit or {}).get("side")
    sources = []
    if dealer_side == side:
        sources.append("dealer")
    if logit_side == side:
        sources.append("logit")
    if impulse in {"UP", "DOWN"}:
        sources.append(f"last3_{impulse}")
    self_contradict = bool(want and seen in {"UP", "DOWN"} and seen != want)
    return {
        "side": side,
        "expected_index": want,
        "seen_index": seen if seen in {"UP", "DOWN"} else None,
        "sources": sources,
        "self_contradict": self_contradict,
        "dealer_verdict": (dealer or {}).get("verdict"),
        "logit_status": (logit or {}).get("status") or (logit or {}).get("reason"),
    }


def follow_gap_itm_1m(prev: Triple, closed: Triple) -> dict[str, Any]:
    """FOLLOW-GAP on two closed 1m bars: INDEX vs ITM CE and ITM PE.

    Same math as premium_divergence_pattern, but ITM LTP + same-strike only.
    ATM / missing ITM / strike roll → follow_gap False and pass_reason set.
    Does not invent prints.
    """
    kinds = {_kind(prev), _kind(closed)} - {""}
    if "ATM" in kinds and "ITM" not in kinds:
        return {"ok": True, "follow_gap": False, "ce_gap": False, "pe_gap": False, "pass_reason": REASON_ATM}
    if "ITM" not in kinds:
        return {"ok": True, "follow_gap": False, "ce_gap": False, "pe_gap": False, "pass_reason": REASON_NO_ITM}
    idx_ret = _ret(prev.idx_close, closed.idx_close)
    ce_ok = _same_strike(prev.itm_ce_strike, closed.itm_ce_strike)
    pe_ok = _same_strike(prev.itm_pe_strike, closed.itm_pe_strike)
    ce_ret = _ret(prev.itm_ce_close, closed.itm_ce_close) if ce_ok else None
    pe_ret = _ret(prev.itm_pe_close, closed.itm_pe_close) if pe_ok else None
    if idx_ret is None:
        return {"ok": True, "follow_gap": False, "ce_gap": False, "pe_gap": False, "pass_reason": REASON_NO_ITM}
    if abs(idx_ret) <= IDX_FLAT:
        return {
            "ok": True,
            "follow_gap": False,
            "ce_gap": False,
            "pe_gap": False,
            "pass_reason": REASON_FLAT,
            "idx_ret": round(float(idx_ret), 8),
        }
    ce_gap = bool(idx_ret > IDX_FLAT and ce_ret is not None and ce_ret <= PREM_FLAT)
    pe_gap = bool(idx_ret < -IDX_FLAT and pe_ret is not None and pe_ret <= PREM_FLAT)
    pass_reason = None
    if idx_ret > IDX_FLAT and not ce_ok:
        pass_reason = REASON_STRIKE_ROLL
    if idx_ret < -IDX_FLAT and not pe_ok:
        pass_reason = REASON_STRIKE_ROLL
    if idx_ret > IDX_FLAT and ce_ret is None and ce_ok:
        pass_reason = REASON_NO_ITM
    if idx_ret < -IDX_FLAT and pe_ret is None and pe_ok:
        pass_reason = REASON_NO_ITM
    return {
        "ok": True,
        "follow_gap": bool(ce_gap or pe_gap),
        "ce_gap": ce_gap,
        "pe_gap": pe_gap,
        "pass_reason": pass_reason,
        "idx_ret": round(float(idx_ret), 8),
        "itm_ce_ret": None if ce_ret is None else round(float(ce_ret), 8),
        "itm_pe_ret": None if pe_ret is None else round(float(pe_ret), 8),
        "rule": "FOLLOW_GAP_ITM_1M",
    }


def observer_review_ticket(
    *,
    side: Optional[str],
    prev: Optional[Triple] = None,
    closed: Optional[Triple] = None,
    classified: Optional[dict[str, Any]] = None,
    dealer: Optional[dict[str, Any]] = None,
    logit: Optional[dict[str, Any]] = None,
    bar_closed_1m: bool = True,
) -> dict[str, Any]:
    """One observer-family verdict on a proposed CE/PE. Does not invent a side.

    Family (KEEP, not rivals): MIX-FORM-FOLLOW-GAP math + ALLOW/VETO/PASS.
    Live check = closed 1m INDEX vs same-strike ITM wing.
    last-3 mismatch is logged on claim — it is not a veto (1m is the clock).
    """
    base: dict[str, Any] = {
        "promote": False,
        "layer": "HYPOTHESIS",
        "execution": "refused",
        "claim": None,
        "follow_gap": False,
        "ce_gap": False,
        "pe_gap": False,
        "side": side if side in {"CE", "PE"} else None,
        "rule": "FOLLOW_GAP_ITM_1M",
    }
    if side not in {"CE", "PE"}:
        return {**base, "action": ACTION_PASS, "reason": REASON_NO_SIDE}
    if not bar_closed_1m or prev is None or closed is None:
        return {**base, "action": ACTION_PASS, "reason": REASON_NO_1M}

    gap = follow_gap_itm_1m(prev, closed)
    base["follow_gap"] = bool(gap.get("follow_gap"))
    base["ce_gap"] = bool(gap.get("ce_gap"))
    base["pe_gap"] = bool(gap.get("pe_gap"))
    for key in ("idx_ret", "itm_ce_ret", "itm_pe_ret"):
        if gap.get(key) is not None:
            base[key] = gap[key]
    if gap.get("pass_reason") in {REASON_ATM, REASON_NO_ITM, REASON_FLAT}:
        return {**base, "action": ACTION_PASS, "reason": gap["pass_reason"]}

    claim = signal_expected_dir(side, classified=classified, dealer=dealer, logit=logit)
    base["claim"] = claim

    if side == "CE" and gap.get("pass_reason") == REASON_STRIKE_ROLL and not gap.get("ce_gap"):
        return {**base, "action": ACTION_PASS, "reason": REASON_STRIKE_ROLL}
    if side == "PE" and gap.get("pass_reason") == REASON_STRIKE_ROLL and not gap.get("pe_gap"):
        return {**base, "action": ACTION_PASS, "reason": REASON_STRIKE_ROLL}

    idx_ret = gap.get("idx_ret")
    if idx_ret is None:
        return {**base, "action": ACTION_PASS, "reason": REASON_NO_ITM}

    if side == "CE" and float(idx_ret) < -IDX_FLAT:
        return {**base, "action": ACTION_VETO, "reason": REASON_INDEX_AGAINST}
    if side == "PE" and float(idx_ret) > IDX_FLAT:
        return {**base, "action": ACTION_VETO, "reason": REASON_INDEX_AGAINST}
    if side == "CE" and gap.get("ce_gap"):
        return {**base, "action": ACTION_VETO, "reason": REASON_FOLLOW_GAP}
    if side == "PE" and gap.get("pe_gap"):
        return {**base, "action": ACTION_VETO, "reason": REASON_FOLLOW_GAP}
    return {**base, "action": ACTION_ALLOW, "reason": REASON_ALLOW}


def follow_gap_series_itm_1m(triples: Sequence[Triple]) -> list[bool]:
    """Per tick: FOLLOW-GAP of the last closed 1m ITM pair. ATM/DI → False."""
    by_min: dict[int, Triple] = {}
    for t in triples:
        by_min[int(t.ts) - int(t.ts) % 60] = t
    minutes = sorted(by_min)
    out: list[bool] = []
    for t in triples:
        mk = int(t.ts) - int(t.ts) % 60
        try:
            i = minutes.index(mk)
        except ValueError:
            out.append(False)
            continue
        if i < 1:
            out.append(False)
            continue
        gap = follow_gap_itm_1m(by_min[minutes[i - 1]], by_min[minutes[i]])
        out.append(bool(gap.get("follow_gap")))
    return out


def apply_observer_to_intents(
    intents: dict[str, tuple[Optional[str], Optional[str]]],
    review: dict[str, Any],
    *,
    fill_books: tuple[str, ...],
    observe_books: tuple[str, ...],
) -> dict[str, tuple[Optional[str], Optional[str]]]:
    """Veto only fill books on the reviewed wing. PASS/ALLOW do not invent CE/PE."""
    out = dict(intents)
    action = str(review.get("action") or ACTION_PASS)
    reason = str(review.get("reason") or REASON_NO_1M)
    veto_side = review.get("side")
    claim = review.get("claim") if isinstance(review.get("claim"), dict) else {}
    if veto_side not in {"CE", "PE"}:
        veto_side = claim.get("side") if claim.get("side") in {"CE", "PE"} else None
    if action == ACTION_VETO:
        for book in fill_books:
            side, skip = out.get(book, (None, None))
            if side not in {"CE", "PE"} or skip is not None:
                continue
            if veto_side in {"CE", "PE"} and side != veto_side:
                continue
            out[book] = (None, reason)
        for book in observe_books:
            out[book] = (None, reason)
    elif action == ACTION_ALLOW:
        for book in observe_books:
            side, skip = out.get(book, (None, None))
            if skip in {None, "OBSERVE_NO_OWN_SIDE", "OBSERVE_NO_OWN_FILL"}:
                out[book] = (None, reason)
    return out


def review_picker_ticket(
    *,
    side: Optional[str],
    prev: Optional[Triple] = None,
    closed: Optional[Triple] = None,
    classified: Optional[dict[str, Any]] = None,
    dealer: Optional[dict[str, Any]] = None,
    logit: Optional[dict[str, Any]] = None,
    bar_closed_1m: bool = True,
) -> dict[str, Any]:
    """SOD: one observer review on the picker's one wing. Does not invent CE/PE."""
    return observer_review_ticket(
        side=side,
        prev=prev,
        closed=closed,
        classified=classified,
        dealer=dealer,
        logit=logit,
        bar_closed_1m=bar_closed_1m,
    )


def review_fill_intents(
    intents: dict[str, tuple[Optional[str], Optional[str]]],
    *,
    prev: Optional[Triple],
    closed: Optional[Triple],
    classified: Optional[dict[str, Any]] = None,
    dealer: Optional[dict[str, Any]] = None,
    logit: Optional[dict[str, Any]] = None,
    fill_books: tuple[str, ...],
    observe_books: tuple[str, ...] = (),
    apply_veto: bool = True,
    bar_closed_1m: bool = True,
) -> tuple[dict[str, tuple[Optional[str], Optional[str]]], dict[str, Any], dict[str, dict[str, Any]]]:
    """Fill-path SOD: each fill book is reviewed on its own proposed side.

    Caller is the paper engine, not dealer and not ML-001. A later STRAT in
    fill_books gets the same 1m family check. Does not invent CE/PE.
    """
    out = dict(intents)
    by_book: dict[str, dict[str, Any]] = {}
    veto_reason: Optional[str] = None
    allow_reason: Optional[str] = None
    for book in fill_books:
        side, skip = out.get(book, (None, None))
        ticket = side if (skip is None and side in {"CE", "PE"}) else None
        rev = observer_review_ticket(
            side=ticket,
            prev=prev,
            closed=closed,
            classified=classified,
            dealer=dealer,
            logit=logit,
            bar_closed_1m=bar_closed_1m,
        )
        by_book[book] = rev
        if not apply_veto or ticket is None:
            continue
        if rev.get("action") == ACTION_VETO:
            reason = str(rev.get("reason") or REASON_FOLLOW_GAP)
            out[book] = (None, reason)
            veto_reason = reason
        elif rev.get("action") == ACTION_ALLOW:
            allow_reason = str(rev.get("reason") or REASON_ALLOW)
    if apply_veto:
        log_reason = veto_reason or allow_reason
        if log_reason:
            for book in observe_books:
                side, skip = out.get(book, (None, None))
                if skip in {None, "OBSERVE_NO_OWN_SIDE", "OBSERVE_NO_OWN_FILL"}:
                    out[book] = (None, log_reason)
    summary = None
    for rev in by_book.values():
        if rev.get("action") == ACTION_VETO:
            summary = rev
            break
    if summary is None:
        for rev in by_book.values():
            if rev.get("action") == ACTION_ALLOW:
                summary = rev
                break
    if summary is None:
        summary = by_book.get("MIX-DEFAULT-BUY") or next(iter(by_book.values()), {
            "action": ACTION_PASS,
            "reason": REASON_NO_SIDE,
            "rule": "FOLLOW_GAP_ITM_1M",
        })
    return out, summary, by_book

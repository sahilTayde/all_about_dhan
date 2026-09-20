"""Boss/picker: RULES majority on spoken CE vs PE. Not LLM. Not paper wr.

Analysts (STRAT-001–014 KEEP_ALL, MIX-FORM-FOLLOWS, logit, XR, greeks,
ML-001/002 silent) vote or stay silent. Silent / DATA_INSUFFICIENT does not
vote. 8-7 or soup = HOLD. INDEX 1m against the winning wing = HOLD.
FOLLOWS is an analyst — not desk, not observer. Does not invent CE/PE.
NO_PROMOTE.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Optional, Sequence

from desk_ml.features import Triple
from desk_ml.model import IDX_FLAT
from desk_ml.observer import follow_gap_itm_1m

STRAT_IDS = tuple(f"STRAT-{i:03d}" for i in range(1, 15))
# Bound enough to *speak* a side from this tape. Filters and unbound stay silent.
STRAT_SPEAK = frozenset({"STRAT-003"})
STRAT_FILTER = frozenset({"STRAT-007", "STRAT-008", "STRAT-009"})
STRAT_SELL_PARK = frozenset({"STRAT-013", "STRAT-014"})

REASON_CONFIRM = "CONFIRM"
REASON_GREEKS = "GREEKS"
REASON_TREND = "TREND"
REASON_BIN = "BIN"

HOLD_NO_SPOKEN = "HOLD_MAJORITY"
HOLD_SOUP = "HOLD_MAJORITY"
HOLD_CLOSE = "HOLD_MAJORITY"
HOLD_TIE = "HOLD_MAJORITY"
HOLD_INDEX_AGAINST = "HOLD_MAJORITY"
DETAIL_NO_SPOKEN = "HOLD_NO_SPOKEN"
DETAIL_SOUP = "HOLD_SOUP"
DETAIL_CLOSE = "HOLD_CLOSE_8_7"
DETAIL_TIE = "HOLD_TIE"
DETAIL_INDEX = "HOLD_INDEX_AGAINST"
DETAIL_OK = "PICKER_MAJORITY"

SOD_PRODUCT_BOOK = "MIX-DEFAULT-BUY"
SOD_LAB_OBSERVE = "SOD_LAB_OBSERVE"
SOD_ONE_OPEN = "SOD_ONE_OPEN"


@dataclass(frozen=True)
class Vote:
    source: str
    side: Optional[str]
    reason_class: str
    silent: bool
    detail: str = ""

    def spoken(self) -> bool:
        return (not self.silent) and self.side in {"CE", "PE"}


def _silent(source: str, detail: str, reason_class: str = "SILENT") -> Vote:
    return Vote(source=source, side=None, reason_class=reason_class, silent=True, detail=detail)


def _vote(source: str, side: str, reason_class: str, detail: str = "") -> Vote:
    if side not in {"CE", "PE"}:
        return _silent(source, detail or "NO_SIDE", reason_class)
    return Vote(source=source, side=side, reason_class=reason_class, silent=False, detail=detail)


def strat_votes(
    *,
    classified: Optional[dict[str, Any]] = None,
    extra: Optional[Sequence[Vote]] = None,
) -> list[Vote]:
    """KEEP_ALL STRAT-001–014 as votes, never fills. Unbound = silent DI."""
    cl = classified or {}
    direction = str(cl.get("direction") or "")
    regime = str(cl.get("regime") or "")
    out: list[Vote] = []
    extra_by = {v.source: v for v in (extra or []) if str(v.source).startswith("STRAT-")}
    for sid in STRAT_IDS:
        if sid in extra_by:
            out.append(extra_by[sid])
            continue
        if sid in STRAT_SELL_PARK:
            out.append(_silent(sid, "SELL_PARK_NO_BUY_VOTE"))
            continue
        if sid in STRAT_FILTER:
            out.append(_silent(sid, "FILTER_NO_SIDE"))
            continue
        if sid == "STRAT-003":
            if regime == "TREND" and direction == "UP":
                out.append(_vote(sid, "CE", REASON_TREND, "strat_003_lean_proxy"))
            elif regime == "TREND" and direction == "DOWN":
                out.append(_vote(sid, "PE", REASON_TREND, "strat_003_lean_proxy"))
            else:
                out.append(_silent(sid, "DATA_INSUFFICIENT"))
            continue
        out.append(_silent(sid, "DATA_INSUFFICIENT"))
    return out


def collect_analyst_votes(
    *,
    follows: Optional[dict[str, Any]] = None,
    dealer: Optional[dict[str, Any]] = None,
    logit: Optional[dict[str, Any]] = None,
    logit_xr: Optional[dict[str, Any]] = None,
    greeks_side: Optional[str] = None,
    greeks_skip: Optional[str] = None,
    ml001_hold: bool = False,
    ml002_hold: bool = False,
    classified: Optional[dict[str, Any]] = None,
    extra: Optional[Sequence[Vote]] = None,
) -> list[Vote]:
    """Spoken CE/PE only. KMeans HOLD is silent — never BUY_CE from ML-001.

    `dealer=` is a legacy alias for the MIX-FORM-FOLLOWS packet. Vote source is
    `follows`. New STRAT/analyst votes go in `extra` (KEEP_ALL, no STRAT-015+).
    """
    votes: list[Vote] = []
    d = follows or dealer or {}
    if d.get("side") in {"CE", "PE"}:
        votes.append(_vote("follows", str(d["side"]), REASON_CONFIRM, str(d.get("verdict") or "")))
    else:
        votes.append(_silent("follows", str(d.get("verdict") or "DATA_INSUFFICIENT")))

    lg = logit or {}
    if lg.get("side") in {"CE", "PE"}:
        votes.append(_vote("logit", str(lg["side"]), REASON_CONFIRM, str(lg.get("status") or "")))
    else:
        votes.append(_silent("logit", str(lg.get("reason") or lg.get("status") or "DATA_INSUFFICIENT")))

    xr = logit_xr or {}
    if xr.get("side") in {"CE", "PE"}:
        votes.append(_vote("xr", str(xr["side"]), REASON_CONFIRM, str(xr.get("status") or "")))
    else:
        votes.append(_silent("xr", str(xr.get("reason") or xr.get("status") or "DATA_INSUFFICIENT")))

    if greeks_side in {"CE", "PE"} and not greeks_skip:
        votes.append(_vote("greeks", greeks_side, REASON_GREEKS, "own_side"))
    else:
        votes.append(_silent("greeks", str(greeks_skip or "DATA_INSUFFICIENT")))

    # ML-001/002: HOLD overlay is not a wing vote.
    votes.append(_silent("ML-001", "HOLD" if ml001_hold else "OBSERVE_NO_OWN_SIDE"))
    votes.append(_silent("ML-002", "HOLD" if ml002_hold else "OBSERVE_NO_OWN_SIDE"))

    extra_non_strat = [v for v in (extra or []) if not str(v.source).startswith("STRAT-")]
    votes.extend(extra_non_strat)
    votes.extend(strat_votes(classified=classified, extra=extra))
    return votes


def _index_against(side: str, prev: Optional[Triple], closed: Optional[Triple]) -> bool:
    if prev is None or closed is None or side not in {"CE", "PE"}:
        return False
    gap = follow_gap_itm_1m(prev, closed)
    idx_ret = gap.get("idx_ret")
    if idx_ret is None:
        return False
    if side == "CE" and float(idx_ret) < -IDX_FLAT:
        return True
    if side == "PE" and float(idx_ret) > IDX_FLAT:
        return True
    return False


def picker_majority(
    votes: Sequence[Vote],
    *,
    prev: Optional[Triple] = None,
    closed: Optional[Triple] = None,
    classified: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """One NIFTY ticket or HOLD. Not wr. Not LLM.

    Same reason class must carry the majority. 8-7 or soup = HOLD.
    INDEX 1m against that wing = HOLD.
    """
    packet_votes = [asdict(v) if isinstance(v, Vote) else dict(v) for v in votes]
    spoken = [v for v in votes if isinstance(v, Vote) and v.spoken()]
    base: dict[str, Any] = {
        "promote": False,
        "layer": "HYPOTHESIS",
        "execution": "refused",
        "llm": False,
        "votes": packet_votes,
        "n_spoken": len(spoken),
        "n_ce": sum(1 for v in spoken if v.side == "CE"),
        "n_pe": sum(1 for v in spoken if v.side == "PE"),
        "side": None,
        "action": "HOLD",
        "skip": HOLD_NO_SPOKEN,
        "detail": DETAIL_NO_SPOKEN,
        "reason_class": None,
        "note": "Picker is RULES majority. STRAT-001–014 vote, they do not fill. NO_PROMOTE.",
    }
    if not spoken:
        return base

    n_ce = int(base["n_ce"])
    n_pe = int(base["n_pe"])
    if n_ce and n_pe and n_ce == n_pe:
        return {**base, "detail": DETAIL_TIE, "skip": HOLD_TIE}
    if n_ce and n_pe and abs(n_ce - n_pe) == 1 and min(n_ce, n_pe) >= 7:
        return {**base, "detail": DETAIL_CLOSE, "skip": HOLD_CLOSE}

    class_n: Counter[str] = Counter()
    class_side: dict[str, Counter[str]] = {}
    for v in spoken:
        class_n[v.reason_class] += 1
        class_side.setdefault(v.reason_class, Counter())[str(v.side)] += 1
    if n_ce and n_pe:
        top_n = class_n.most_common(2)
        if len(top_n) >= 2 and top_n[0][1] == top_n[1][1]:
            return {**base, "detail": DETAIL_SOUP, "skip": HOLD_SOUP, "reason_class": "SOUP"}
        win_class = top_n[0][0]
        sides = class_side[win_class]
        ce_c = int(sides.get("CE", 0))
        pe_c = int(sides.get("PE", 0))
        if ce_c == pe_c:
            return {**base, "detail": DETAIL_TIE, "skip": HOLD_TIE, "reason_class": win_class}
        side = "CE" if ce_c > pe_c else "PE"
    else:
        side = "CE" if n_ce > n_pe else "PE"
        win_class = class_n.most_common(1)[0][0] if class_n else REASON_CONFIRM

    cl = classified or {}
    idx_dir = cl.get("index_direction") or cl.get("direction")
    if side == "CE" and idx_dir == "DOWN":
        return {
            **base,
            "side": None,
            "detail": DETAIL_INDEX,
            "skip": HOLD_INDEX_AGAINST,
            "reason_class": win_class,
            "held_side": side,
        }
    if side == "PE" and idx_dir == "UP":
        return {
            **base,
            "side": None,
            "detail": DETAIL_INDEX,
            "skip": HOLD_INDEX_AGAINST,
            "reason_class": win_class,
            "held_side": side,
        }
    if _index_against(side, prev, closed):
        return {
            **base,
            "side": None,
            "detail": DETAIL_INDEX,
            "skip": HOLD_INDEX_AGAINST,
            "reason_class": win_class,
            "held_side": side,
        }
    return {
        **base,
        "side": side,
        "action": "TICKET",
        "skip": None,
        "detail": DETAIL_OK,
        "reason_class": win_class,
    }


def apply_picker_to_intents(
    intents: dict[str, tuple[Optional[str], Optional[str]]],
    picker: dict[str, Any],
    *,
    fill_books: tuple[str, ...],
    observe_books: tuple[str, ...],
    sod_one_ticket: bool,
    product_book: str = SOD_PRODUCT_BOOK,
) -> dict[str, tuple[Optional[str], Optional[str]]]:
    """LAB books observe-or-skip when SOD one-ticket is on."""
    out = dict(intents)
    side = picker.get("side") if picker.get("action") == "TICKET" else None
    hold_skip = str(picker.get("skip") or HOLD_NO_SPOKEN)
    if side not in {"CE", "PE"}:
        for book in fill_books:
            cur_side, cur_skip = out.get(book, (None, None))
            if cur_skip is None:
                out[book] = (cur_side, hold_skip)
        for book in observe_books:
            out[book] = (None, hold_skip)
        return out
    if sod_one_ticket:
        for book in fill_books:
            if book == product_book:
                out[book] = (side, None)
            else:
                out[book] = (None, SOD_LAB_OBSERVE)
        for book in observe_books:
            out[book] = (None, SOD_LAB_OBSERVE)
        return out
    for book in fill_books:
        cur_side, cur_skip = out.get(book, (None, None))
        if cur_skip is not None:
            continue
        if cur_side in {"CE", "PE"} and cur_side != side:
            out[book] = (None, hold_skip)
        elif cur_side not in {"CE", "PE"}:
            out[book] = (side, None)
    return out

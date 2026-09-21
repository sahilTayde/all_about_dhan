"""06 after-hours SOD exam: honesty slice + fill contract + why-spill story.

write=false. Does not change overlay, picker, or live orders. NO_PROMOTE.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from desk_ml.fill_contract import CONTRACT_ID, CONTRACT_PLAIN, SIGNAL_CLOCK, grade_fill
from desk_ml.persist import repo_root

IST = timezone(timedelta(hours=5, minutes=30))
EXAM_DAYS_DEFAULT = ("2026-09-16", "2026-09-17", "2026-09-18")
SOD_BOOK = "MIX-DEFAULT-BUY"
SLICE_CAP = 2
REPORT_NAME = "sod_exam_report.json"


def compact_exam_event(step: dict[str, Any], *, opened: bool, quote_src: Optional[str]) -> dict[str, Any]:
    picker = step.get("picker") or {}
    observer = step.get("observer") or {}
    desk = step.get("desk") or {}
    exam = step.get("exam") or {}
    votes = []
    for v in step.get("analyst_votes") or []:
        if not isinstance(v, dict):
            continue
        votes.append(
            {
                "source": v.get("source"),
                "side": v.get("side"),
                "silent": v.get("silent"),
            }
        )
    return {
        "ts": step.get("ts"),
        "underlying": step.get("underlying"),
        "picker_action": picker.get("action"),
        "picker_side": picker.get("side"),
        "picker_skip": picker.get("skip"),
        "observer_action": observer.get("action"),
        "observer_reason": observer.get("reason"),
        "observer_side": observer.get("side"),
        "desk_opened": bool(opened or desk.get("opened_this_tick")),
        "votes": votes,
        "exam": exam,
        "quote_src": quote_src,
    }


def _ist_now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _session_kind(root: Path, day: str) -> str:
    blob: dict[str, Any] = {}
    for name in (f"{day}.json", f"NIGHTLY_{day}.json"):
        path = root / "data" / "recon" / name
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
            if isinstance(raw, dict):
                blob = raw
                break
    flags = blob.get("session_flags") or blob.get("session_kind") or blob.get("kind")
    if isinstance(flags, list):
        joined = " ".join(str(x) for x in flags).upper()
    else:
        joined = str(flags or "").upper()
    if "EXPIRY" in joined:
        return "EXPIRY"
    if "NEWS" in joined:
        return "NEWS_DAY"
    if joined in {"NORMAL", "NEWS_DAY", "EXPIRY", "UNKNOWN"}:
        return joined if joined else "UNKNOWN"
    return "UNKNOWN"


def _next_itm_ok(side: str, fill_ts: int, triples: Sequence[Any]) -> Optional[bool]:
    if side not in {"CE", "PE"}:
        return None
    later = [t for t in triples if int(t.ts) > int(fill_ts)]
    if len(later) < 1:
        return None
    nxt = later[0]
    cur = None
    for t in triples:
        if int(t.ts) == int(fill_ts):
            cur = t
            break
    if cur is None:
        return None
    if side == "CE":
        a, b = getattr(cur, "itm_ce_close", None), getattr(nxt, "itm_ce_close", None)
    else:
        a, b = getattr(cur, "itm_pe_close", None), getattr(nxt, "itm_pe_close", None)
    if a is None or b is None:
        return None
    try:
        return float(b) > float(a)
    except (TypeError, ValueError):
        return None


def classify_spill(row: dict[str, Any], *, next_itm_helped: Optional[bool]) -> dict[str, Any]:
    reason = str(row.get("exit_reason") or row.get("reason") or row.get("close_reason") or "")
    sl = bool(row.get("sl_hit") or row.get("stop_hit"))
    pnl = row.get("realized_pnl_inr")
    if pnl is None:
        pnl = row.get("pnl_inr")
    if pnl is None:
        pnl = row.get("pnl")
    try:
        money = float(pnl) if pnl is not None else None
    except (TypeError, ValueError):
        money = None
    lost = money is not None and money < 0
    if not lost:
        return {
            "room": "none",
            "code": "WIN_OR_FLAT",
            "plain": "This ticket did not lose rupees. Exam does not retune from it.",
        }
    if sl or "STOP" in reason.upper() or "SL" in reason.upper():
        if next_itm_helped is True:
            return {
                "room": "overlay",
                "code": "ENTRY_OK_OVERLAY_STOP",
                "plain": (
                    "The next ITM minute went our way, then the booking stop/stall took the loss. "
                    "Do not retune from one day — watch overlay only if many NORMAL days agree."
                ),
            }
        return {
            "room": "overlay",
            "code": "STOP_OR_STALL",
            "plain": (
                "We lost after the fill (stop / stall / against). Entry may have been wrong or booking cut it. "
                "Need more NORMAL days before touching overlay."
            ),
        }
    if "FLATTEN" in reason.upper() or "1516" in reason:
        return {
            "room": "desk",
            "code": "FLATTEN_CUT",
            "plain": "Session flatten closed a loser. Clock rule, not a one-day strategy change.",
        }
    if "CANCEL" in reason.upper() or "AGAINST" in reason.upper():
        return {
            "room": "overlay",
            "code": "CANCEL_AGAINST",
            "plain": "Overlay cancelled after the thesis broke. That can save worse days — do not flip from one loss.",
        }
    return {
        "room": "desk",
        "code": "LOST_OTHER",
        "plain": f"Lost on exit {reason or 'unknown'}. Grade the room, do not promote.",
    }


def _fingerprint(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        event.get("picker_action"),
        event.get("picker_side"),
        event.get("observer_action"),
        event.get("observer_reason"),
        event.get("desk_opened"),
    )


def _pick_slice_ts(events: Sequence[dict[str, Any]]) -> list[int]:
    tickets = [int(e["ts"]) for e in events if e.get("desk_opened") and e.get("ts") is not None]
    if not tickets:
        spoken = [int(e["ts"]) for e in events if e.get("picker_action") == "TICKET" and e.get("ts") is not None]
        tickets = spoken
    if not tickets:
        return []
    if len(tickets) == 1:
        return tickets[:1]
    return [tickets[0], tickets[-1]][:SLICE_CAP]


def _analyst_hits(events: Sequence[dict[str, Any]], triples_by_und: dict[str, list[Any]]) -> list[dict[str, Any]]:
    tallies: dict[str, Counter[str]] = {}
    for ev in events:
        und = str(ev.get("underlying") or "")
        triples = triples_by_und.get(und) or []
        ts = ev.get("ts")
        for v in ev.get("votes") or []:
            src = str(v.get("source") or "")
            side = v.get("side")
            if not src or side not in {"CE", "PE"} or v.get("silent"):
                continue
            ok = _next_itm_ok(str(side), int(ts), triples) if ts is not None else None
            bucket = tallies.setdefault(src, Counter())
            bucket["spoken"] += 1
            if ok is True:
                bucket["next_itm_ok"] += 1
            elif ok is False:
                bucket["next_itm_miss"] += 1
            else:
                bucket["next_itm_unknown"] += 1
    rows = []
    for src, c in sorted(tallies.items()):
        spoken = int(c["spoken"])
        hit = int(c["next_itm_ok"])
        miss = int(c["next_itm_miss"])
        known = hit + miss
        rows.append(
            {
                "source": src,
                "spoken": spoken,
                "next_itm_ok": hit,
                "next_itm_miss": miss,
                "hit_pct": round(100.0 * hit / known, 1) if known else None,
                "note": "Not a customer win rate. Next finished ITM print only. UNKNOWN if ATM tape.",
            }
        )
    return rows


def run_day_exam(
    *,
    day: str,
    root: Optional[Path] = None,
    underlyings: Sequence[str] = ("NIFTY",),
    source: str = "dual-tape",
) -> dict[str, Any]:
    from desk_ml.paper_scalp import replay_paper_scalp
    from desk_ml.tape import load_dual_tape_triples, load_triples

    base = root or repo_root()
    loaded: dict[str, list[Any]] = {}
    tapes: dict[str, Any] = {}
    for und in underlyings:
        u = und.upper()
        if source.replace("_", "-") in {"dual-tape", "dualtape"}:
            triples, tape = load_dual_tape_triples(u, root=base, session_ist_date=day)
        else:
            triples, tape = load_triples(u, root=base)
            triples = [t for t in triples if _ist_date(int(t.ts)) == day]
            tape = {**tape, "session_ist_date": day, "aligned_triples": len(triples)}
        loaded[u] = triples
        tapes[u] = tape

    n_triples = sum(len(v) for v in loaded.values())
    if n_triples < 8:
        return {
            "ok": True,
            "day": day,
            "honesty": "NOT_ENOUGH_DATA",
            "session_kind": _session_kind(base, day),
            "n_triples": n_triples,
            "tapes": tapes,
            "story": (
                f"{day}: not enough 1m triples to exam. "
                "ATM-only files still load; ITM fill contract may skip. Not a promote."
            ),
            "promote": False,
            "orders": "REFUSED",
        }

    full = replay_paper_scalp(
        root=base,
        underlyings=tuple(loaded.keys()),
        source=source,
        triples_by_und=loaded,
        write=False,
        live_session=True,
        session_ist_date=day,
        sod_one_ticket=True,
        picker_majority=True,
    )
    events = list(full.get("exam_events") or [])
    closed = [
        r
        for r in (full.get("closed_trades") or [])
        if str(r.get("book_id") or r.get("model") or "") == SOD_BOOK
    ]
    fill_grades = [e.get("exam") or {} for e in events if (e.get("exam") or {}).get("verdict")]
    bad_fills = [g for g in fill_grades if g.get("ok") is False]
    kinds = {str(tapes[u].get("premium_kind") or tapes[u].get("kind") or "") for u in tapes}
    tape_note = "ATM tape on disk for this day — ITM-only SOD fill may skip (honest)."
    if any("ITM" in str(tapes[u]).upper() for u in tapes):
        tape_note = "ITM kind present on at least one tape row."

    slice_rows = []
    peeked = 0
    do_slice = any(e.get("desk_opened") or e.get("picker_action") == "TICKET" for e in events)
    for und, triples in loaded.items():
        if not do_slice:
            break
        und_events = [e for e in events if e.get("underlying") == und]
        for cut_ts in _pick_slice_ts(und_events):
            prefix = [t for t in triples if int(t.ts) <= int(cut_ts)]
            if len(prefix) < 8:
                continue
            sliced = replay_paper_scalp(
                root=base,
                underlyings=(und,),
                source=source,
                triples_by_und={und: prefix},
                write=False,
                live_session=True,
                session_ist_date=day,
                sod_one_ticket=True,
                picker_majority=True,
            )
            full_ev = next((e for e in und_events if int(e.get("ts") or 0) == int(cut_ts)), None)
            slice_ev = None
            for e in reversed(sliced.get("exam_events") or []):
                if int(e.get("ts") or 0) == int(cut_ts):
                    slice_ev = e
                    break
            if full_ev is None or slice_ev is None:
                slice_rows.append(
                    {
                        "underlying": und,
                        "cut_ts": cut_ts,
                        "status": "DATA_INSUFFICIENT",
                        "plain": "Slice had no matching SOD event at that minute.",
                    }
                )
                continue
            same = _fingerprint(full_ev) == _fingerprint(slice_ev)
            if not same:
                peeked += 1
            slice_rows.append(
                {
                    "underlying": und,
                    "cut_ts": cut_ts,
                    "status": "CLEAN" if same else "PEEKED",
                    "full": _fingerprint(full_ev),
                    "sliced": _fingerprint(slice_ev),
                    "plain": (
                        "Same picker/observer/desk when later candles are hidden."
                        if same
                        else "Decision moved when later candles were hidden — treat paper wr as suspect."
                    ),
                }
            )

    if peeked:
        honesty = "PEEKED"
    elif not events:
        honesty = "NOT_ENOUGH_DATA"
    else:
        honesty = "CLEAN"

    stories = []
    for row in closed:
        ts = row.get("opened_ts") or row.get("ts") or row.get("filled_ts")
        und = str(row.get("underlying") or row.get("und") or "NIFTY")
        side = str(row.get("side") or "")
        helped = _next_itm_ok(side, int(ts), loaded.get(und) or []) if ts else None
        spill = classify_spill(row, next_itm_helped=helped)
        stories.append(
            {
                "day": day,
                "underlying": und,
                "side": side,
                "pnl_inr": row.get("pnl_inr", row.get("pnl")),
                "exit": row.get("exit_reason") or row.get("reason"),
                "next_itm_helped": helped,
                **spill,
            }
        )

    room_counts = Counter(s.get("room") for s in stories if s.get("code") != "WIN_OR_FLAT")
    if honesty == "PEEKED":
        headline = (
            f"{day}: scoreboard may have peeked. Do not trust wr. "
            "Fix the exam/signal clock before changing overlay."
        )
        improve = "analyst / signal clock (or how 3m logit bars are built)"
    elif bad_fills:
        headline = (
            f"{day}: a paper fill broke the written ITM contract "
            f"({bad_fills[0].get('verdict')}). Money on the board may be a fill story."
        )
        improve = "desk fill rule"
    elif room_counts.get("overlay"):
        headline = (
            f"{day}: honest exam, losses after fill (stop/stall/cancel). "
            "One day is not enough to recode overlay."
        )
        improve = "overlay — only if more NORMAL days agree (founder confirm)"
    elif room_counts.get("desk"):
        headline = f"{day}: losses on flatten or other desk clock. Not a promote."
        improve = "desk clock / flatten — watch, do not retune tonight"
    elif not closed:
        headline = (
            f"{day}: no SOD MIX-DEFAULT-BUY closes. "
            f"{tape_note} Observer/ITM skip can leave n_open=0. That is a data story, not a silent win."
        )
        improve = "need ITM tape or accept ATM days as DATA_INSUFFICIENT for ITM fills"
    else:
        headline = f"{day}: exam {honesty}. Closed tickets exist — read spill rows. No promote."
        improve = "analyst IC if hit_pct stays near coin on more NORMAL days"

    return {
        "ok": True,
        "day": day,
        "honesty": honesty,
        "session_kind": _session_kind(base, day),
        "n_triples": n_triples,
        "n_exam_events": len(events),
        "n_sod_closed": len(closed),
        "n_slice": len(slice_rows),
        "n_peeked_slices": peeked,
        "n_fill_contract_fail": len(bad_fills),
        "fill_contract": CONTRACT_ID,
        "tape_note": tape_note,
        "tapes": {u: {"aligned_triples": tapes[u].get("aligned_triples"), "source": tapes[u].get("source")} for u in tapes},
        "slices": slice_rows,
        "analyst_next_itm": _analyst_hits(events, loaded),
        "spills": stories[:40],
        "room_counts": dict(room_counts),
        "story": headline,
        "improve": improve,
        "one_day_is_not_retune": True,
        "promote": False,
        "orders": "REFUSED",
        "pnl_note": "Use board net ₹ only if honesty=CLEAN and fill contract ok.",
        "win_rate": None,
    }


def _ist_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), IST).date().isoformat()


def run_sod_exam(
    *,
    days: Sequence[str] = EXAM_DAYS_DEFAULT,
    root: Optional[Path] = None,
    underlyings: Sequence[str] = ("NIFTY",),
    source: str = "dual-tape",
    persist: bool = True,
) -> dict[str, Any]:
    base = root or repo_root()
    day_rows = []
    for day in days:
        day_rows.append(
            run_day_exam(day=day, root=base, underlyings=underlyings, source=source)
        )
    honesties = [d.get("honesty") for d in day_rows]
    if "PEEKED" in honesties:
        overall = "PEEKED"
    elif all(h == "NOT_ENOUGH_DATA" for h in honesties):
        overall = "NOT_ENOUGH_DATA"
    elif "CLEAN" in honesties:
        overall = "CLEAN"
    else:
        overall = "NOT_ENOUGH_DATA"

    stories = [d.get("story") for d in day_rows if d.get("story")]
    improve = []
    for d in day_rows:
        if d.get("improve") and d.get("improve") not in improve:
            improve.append(d["improve"])

    report = {
        "ok": True,
        "job": "sod-exam",
        "as_of_ist": _ist_now(),
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "promote": False,
        "orders": "REFUSED",
        "win_rate": None,
        "one_day_is_not_retune": True,
        "contract": {
            "id": CONTRACT_ID,
            "signal_clock": SIGNAL_CLOCK,
            "plain": CONTRACT_PLAIN,
        },
        "how_to_read": {
            "where": "Founder /pm → Honesty exam. Also GET /paper/sod-exam.",
            "when": "After close or when you run: python -m desk_ml sod-exam",
            "boxes": [
                "Honesty: CLEAN / PEEKED / NOT_ENOUGH_DATA",
                "Fill contract: did we book ATM as ITM or fill on a forming bar?",
                "Analyst next-ITM: who was useful (not customer wr)",
                "Spill story: which room leaked — do not retune from one day",
            ],
        },
        "overall_honesty": overall,
        "headline": (
            "Exam is a grade, not a promote. Bad days happen. "
            "Use the room name to know what to watch next — not to rewrite tonight."
        ),
        "days": day_rows,
        "stories": stories,
        "watch_next": improve,
        "cli": "python -m desk_ml sod-exam --days 2026-09-16,2026-09-17,2026-09-18 --no-write-board",
        "note": "write=false replay. Overlay unchanged. NO_PROMOTE.",
    }
    if persist:
        out = base / "data" / "recon" / REPORT_NAME
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        mock = base / "apps" / "web" / "public" / "mock" / REPORT_NAME
        mock.parent.mkdir(parents=True, exist_ok=True)
        mock.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        report["path"] = str(out)
        report["mock_path"] = str(mock)
    return report

"""Held-contract pin list for the V2 recorder (paper / shadow only).

Reads open contracts from the paper books, decision journal, V2 shadow journal,
and the paper ledger. Missing or corrupt sources add nothing. The recorder
keeps every returned instrument subscribed until it leaves this set.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterable
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from marketdata.instruments import UNDERLYINGS, Universe

log = logging.getLogger(__name__)

PAPER_BOOKED_REL = Path("data") / "recon" / "paper_booked"
DECISION_JOURNAL_REL = Path("data") / "recon" / "decision_journal"
SHADOW_V2_REL = Path("data") / "shadow" / "v2"
RESEARCH_RULES_REL = Path("data") / "recon" / "research_rules"
LEDGER_REL = Path("data") / "ledger" / "ledger.sqlite"
# 2026-10-21 recentre-pin fix: paper_extra book (desk-counted and shadow rows) and a generic
# held_pins journal that any watcher (lab shadow, re-entry, forward exits) appends to.
PAPER_EXTRA_REL = Path("data") / "recon" / "paper_extra"
HELD_PINS_REL = Path("data") / "recon" / "held_pins"
# Minutes a contract stays pinned after its trade closes (re-entry / late fills). 0 = off.
DEFAULT_COOLDOWN_S = 15 * 60.0
# Hard cap on pins per underlying so the Dhan subscription budget is never breached.
DEFAULT_MAX_PINNED = 40
_OPEN_STATUSES = frozenset({"OPEN", "HELD", "IN_TRADE", "LIVE"})

_OPEN_JOURNAL_STAGES = frozenset({"imm", "in_trade"})
_CLOSED_JOURNAL_STAGES = frozenset({"exit"})


def option_instrument_id(underlying: str, expiry: str, strike: float | int, side: str) -> str:
    name = str(underlying or "").upper()
    exch, _ = UNDERLYINGS.get(name, ("NSE", "NSE_FNO"))
    return f"{exch}_FNO:{name}:{expiry}:{int(float(strike))}:{side.upper()}"


def is_option_id(instrument_id: str) -> bool:
    parts = str(instrument_id).split(":")
    return len(parts) >= 5 and parts[-1] in {"CE", "PE"}


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:
        return None
    return out


def _side(value: Any) -> str | None:
    raw = str(value or "").upper()
    return raw if raw in {"CE", "PE"} else None


def _jsonl(path: Path) -> Iterable[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except OSError as exc:
        log.warning("pin source unreadable %s: %s", path, type(exc).__name__)
        return
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            yield row


def _json_obj(path: Path) -> dict[str, Any]:
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        log.warning("pin source unreadable %s: %s", path, type(exc).__name__)
        return {}
    return blob if isinstance(blob, dict) else {}


class HeldPinReader:
    """Callable pin list. Cached until any source file's mtime changes."""

    def __init__(
        self,
        root: Path,
        day: date,
        universes: Iterable[Universe] = (),
        *,
        extra: bool = True,
        cooldown_s: float = DEFAULT_COOLDOWN_S,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.root = Path(root)
        self.day = day
        # extra=False is the off switch: old sources only, no cooldown (pre-2026-10-21 behaviour).
        self.extra = extra
        self.cooldown_s = cooldown_s if extra else 0.0
        self.now = now
        # iid -> (priority, sort key). priority 0 = open trade, 1 = closed within cooldown.
        self._recent: dict[str, float] = {}
        self._open_since: dict[str, float] = {}
        self._expiry: dict[str, str] = {}
        self._known: set[str] = set()
        self._strike: dict[tuple[str, int, str], str] = {}
        for universe in universes:
            name = universe.underlying.upper()
            self._expiry[name] = universe.expiry
            for inst in universe.all_instruments():
                self._known.add(inst.instrument_id)
            for (strike, side), inst in universe.options.items():
                self._strike[(name, int(strike), side)] = inst.instrument_id
        self._cached: set[str] = set()
        self._mtimes: tuple[tuple[str, float], ...] = ()

    def paths(self) -> list[Path]:
        day = self.day.isoformat()
        return [
            self.root / PAPER_BOOKED_REL / f"{day}.jsonl",
            self.root / PAPER_BOOKED_REL / f"{day}.state.json",
            self.root / DECISION_JOURNAL_REL / f"{day}.jsonl",
            self.root / SHADOW_V2_REL / day / "decisions.jsonl",
            self.root / SHADOW_V2_REL / day / "pnl.jsonl",
            self.root / LEDGER_REL,
            self.root / RESEARCH_RULES_REL / f"{day}.json",
        ] + (
            [
                self.root / PAPER_EXTRA_REL / f"{day}.json",
                self.root / HELD_PINS_REL / f"{day}.jsonl",
            ]
            if self.extra
            else []
        )

    def __call__(self) -> set[str]:
        return set(self.ranked())

    def ranked(self) -> list[str]:
        """Open contracts first (oldest open first), then contracts closed within the cooldown
        (most recent close first). Callers cap this list; the order decides who survives a cap."""
        stamp = self._mtime_stamp()
        if stamp != self._mtimes:
            self._recent = {}
            self._open_since = {}
            self._cached = self._load()
            self._mtimes = stamp
        now_s = self.now()
        open_ids = sorted(self._cached, key=lambda i: (self._open_since.get(i, 0.0), i))
        recent = [
            iid
            for iid, closed_s in sorted(self._recent.items(), key=lambda kv: (-kv[1], kv[0]))
            if iid not in self._cached and now_s - closed_s <= self.cooldown_s
        ]
        known = self._known
        return [i for i in open_ids + recent if not known or i in known]

    def _mtime_stamp(self) -> tuple[tuple[str, float], ...]:
        out: list[tuple[str, float]] = []
        for path in self.paths():
            try:
                out.append((str(path), path.stat().st_mtime))
            except OSError:
                continue
        return tuple(out)

    def _load(self) -> set[str]:
        ids: set[str] = set()
        ids.update(self._from_paper_booked())
        ids.update(self._from_decision_journal())
        ids.update(self._from_shadow())
        ids.update(self._from_ledger())
        ids.update(self._from_research_rules())
        if self.extra:
            ids.update(self._from_paper_extra())
            ids.update(self._from_held_pins())
        if self._known:
            return {iid for iid in ids if iid in self._known}
        return ids

    def resolve(self, row: dict[str, Any]) -> str | None:
        for key in ("instrument_id", "iid"):
            raw = str(row.get(key) or "").strip()
            if is_option_id(raw):
                return raw
        inputs = row.get("inputs") if isinstance(row.get("inputs"), dict) else {}
        for blob in (row, inputs):
            raw = str(blob.get("instrument_id") or "").strip()
            if is_option_id(raw):
                return raw
        underlying = str(row.get("underlying") or inputs.get("underlying") or "").upper()
        side = _side(row.get("side") or inputs.get("side"))
        strike = _num(row.get("atm_strike") if "atm_strike" in row else None)
        if strike is None:
            strike = _num(row.get("strike") or inputs.get("strike") or inputs.get("atm_strike"))
        if not underlying or side is None or strike is None:
            return None
        known = self._strike.get((underlying, int(strike), side))
        if known:
            return known
        expiry = self._expiry.get(underlying)
        if not expiry:
            return None
        return option_instrument_id(underlying, expiry, strike, side)

    def _from_paper_booked(self) -> set[str]:
        day = self.day.isoformat()
        ids: set[str] = set()
        for row in _jsonl(self.root / PAPER_BOOKED_REL / f"{day}.jsonl"):
            if _is_closed_trade(row):
                continue
            iid = self.resolve(row)
            if iid:
                ids.add(iid)
        state = _json_obj(self.root / PAPER_BOOKED_REL / f"{day}.state.json")
        open_rows = state.get("open")
        if isinstance(open_rows, dict):
            for blob in open_rows.values():
                if isinstance(blob, dict):
                    iid = self.resolve(blob)
                    if iid:
                        ids.add(iid)
        return ids

    def _from_decision_journal(self) -> set[str]:
        open_rows: dict[str, dict[str, Any]] = {}
        closed: set[str] = set()
        for row in _jsonl(self.root / DECISION_JOURNAL_REL / f"{self.day.isoformat()}.jsonl"):
            cid = str(row.get("candidate_id") or row.get("trade_id") or "")
            stage = str(row.get("stage") or "")
            if not cid:
                iid = self.resolve(row)
                if iid and stage not in _CLOSED_JOURNAL_STAGES:
                    open_rows.setdefault(iid, row)
                continue
            if stage in _OPEN_JOURNAL_STAGES and str(row.get("decision") or "") in {"fill", "pass"}:
                open_rows[cid] = row
            if stage in _CLOSED_JOURNAL_STAGES:
                closed.add(cid)
        ids: set[str] = set()
        for cid, row in open_rows.items():
            if cid in closed:
                continue
            iid = self.resolve(row)
            if iid:
                ids.add(iid)
        return ids

    def _from_shadow(self) -> set[str]:
        folder = self.root / SHADOW_V2_REL / self.day.isoformat()
        held: set[str] = set()
        for row in _jsonl(folder / "decisions.jsonl"):
            iid = str(row.get("instrument_id") or "")
            if not is_option_id(iid):
                iid = self.resolve(row) or ""
            if not iid:
                continue
            action = str(row.get("action") or "").upper()
            if action == "ENTER":
                held.add(iid)
            elif action in {"EXIT", "FLAT", "SHADOW_FLAT"}:
                held.discard(iid)
        for row in _jsonl(folder / "pnl.jsonl"):
            iid = str(row.get("instrument_id") or "")
            if not is_option_id(iid):
                continue
            kind = str(row.get("kind") or "").upper()
            if kind in {"SHADOW_OPEN", "OPEN"}:
                held.add(iid)
            elif kind in {"SHADOW_FLAT", "FLAT", "EXIT"}:
                held.discard(iid)
        return held

    def _from_research_rules(self) -> set[str]:
        """Desk (open) and shadow (shadow_parked.open) research-rule positions from the board journal."""
        blob = _json_obj(self.root / RESEARCH_RULES_REL / f"{self.day.isoformat()}.json")
        rows = list(blob.get("open") or [])
        sp = blob.get("shadow_parked") if isinstance(blob.get("shadow_parked"), dict) else {}
        rows += list(sp.get("open") or [])
        ids: set[str] = set()
        closed_rows = list(blob.get("closed") or []) + list(sp.get("closed") or [])
        if self.extra:
            for row in closed_rows:
                if isinstance(row, dict):
                    r = dict(row)
                    r.setdefault("strike", row.get("held_strike") or row.get("atm_strike"))
                    iid = self.resolve(r)
                    if iid:
                        self._closed(iid, row.get("closed_ts") or row.get("exit_time"))
        for row in rows:
            if not isinstance(row, dict) or _is_closed_trade(row):
                continue
            r = dict(row)
            r.setdefault("strike", row.get("held_strike") or row.get("atm_strike"))
            iid = self.resolve(r)
            if iid:
                ids.add(iid)
        return ids

    def _closed(self, iid: str, when: Any) -> None:
        ts = self._ts(when)
        if ts is not None and self.cooldown_s > 0:
            self._recent[iid] = max(ts, self._recent.get(iid, 0.0))

    def _opened(self, iid: str, when: Any) -> None:
        ts = self._ts(when)
        if ts is not None:
            self._open_since[iid] = min(ts, self._open_since.get(iid, ts))

    def _ts(self, value: Any) -> float | None:
        """Epoch seconds from epoch, ISO 8601, or IST "HH:MM[:SS]" on the session day."""
        if value is None or value == "":
            return None
        num = _num(value)
        if num is not None:
            return num / 1000.0 if num > 1e11 else num
        raw = str(value).strip()
        ist = timezone(timedelta(hours=5, minutes=30))
        try:
            if "T" in raw or "-" in raw[:10]:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return (dt if dt.tzinfo else dt.replace(tzinfo=ist)).timestamp()
            parts = [int(float(p)) for p in raw.split(":")]
            hh, mm, ss = (parts + [0, 0])[:3]
            return datetime(self.day.year, self.day.month, self.day.day, hh, mm, ss, tzinfo=ist).timestamp()
        except (ValueError, TypeError):
            return None

    def _from_paper_extra(self) -> set[str]:
        """paper_extra book: desk-counted and shadow rows. Open = status OPEN or no exit_time."""
        blob = _json_obj(self.root / PAPER_EXTRA_REL / f"{self.day.isoformat()}.json")
        ids: set[str] = set()
        for row in blob.get("rows") or []:
            if not isinstance(row, dict) or row.get("entry_time") in (None, ""):
                continue
            iid = self.resolve(row)
            if not iid:
                continue
            status = str(row.get("status") or "").upper()
            if status in _OPEN_STATUSES or (not status and row.get("exit_time") in (None, "")):
                ids.add(iid)
                self._opened(iid, row.get("entry_time"))
            elif row.get("exit_time") not in (None, ""):
                self._closed(iid, row.get("exit_time"))
        return ids

    def _from_held_pins(self) -> set[str]:
        """Generic journal, one JSON object per line: {"event": "open"|"close", "ts": ..., and
        instrument_id or underlying/strike/side, "source": "..."}. Open/close are counted per
        (source, trade_id) so two watchers on one contract both have to close it."""
        live: dict[str, set[str]] = {}
        for row in _jsonl(self.root / HELD_PINS_REL / f"{self.day.isoformat()}.jsonl"):
            iid = self.resolve(row)
            if not iid:
                continue
            key = f"{row.get('source') or ''}|{row.get('trade_id') or ''}"
            event = str(row.get("event") or "").lower()
            if event == "open":
                live.setdefault(iid, set()).add(key)
                self._opened(iid, row.get("ts"))
            elif event == "close":
                live.get(iid, set()).discard(key)
                self._closed(iid, row.get("ts"))
        return {iid for iid, keys in live.items() if keys}

    def _from_ledger(self) -> set[str]:
        path = self.root / LEDGER_REL
        if not path.is_file():
            return set()
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        except sqlite3.Error:
            return set()
        try:
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            ids: set[str] = set()
            for table in ("positions_v2", "positions"):
                if table not in tables:
                    continue
                try:
                    for (iid,) in con.execute(f"SELECT instrument_id FROM {table} WHERE net_qty != 0"):
                        raw = str(iid or "")
                        if is_option_id(raw):
                            ids.add(raw)
                except sqlite3.Error:
                    continue
            return ids
        except sqlite3.Error:
            return set()
        finally:
            con.close()


def _is_closed_trade(row: dict[str, Any]) -> bool:
    return row.get("closed_ts") not in (None, "", 0, "0")

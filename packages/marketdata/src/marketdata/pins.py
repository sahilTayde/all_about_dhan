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
from datetime import date
from pathlib import Path
from typing import Any

from marketdata.instruments import UNDERLYINGS, Universe

log = logging.getLogger(__name__)

PAPER_BOOKED_REL = Path("data") / "recon" / "paper_booked"
DECISION_JOURNAL_REL = Path("data") / "recon" / "decision_journal"
SHADOW_V2_REL = Path("data") / "shadow" / "v2"
RESEARCH_RULES_REL = Path("data") / "recon" / "research_rules"
LEDGER_REL = Path("data") / "ledger" / "ledger.sqlite"

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
    ) -> None:
        self.root = Path(root)
        self.day = day
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
        ]

    def __call__(self) -> set[str]:
        stamp = self._mtime_stamp()
        if stamp != self._mtimes:
            self._cached = self._load()
            self._mtimes = stamp
        return set(self._cached)

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
        for row in rows:
            if not isinstance(row, dict) or _is_closed_trade(row):
                continue
            r = dict(row)
            r.setdefault("strike", row.get("held_strike") or row.get("atm_strike"))
            iid = self.resolve(r)
            if iid:
                ids.add(iid)
        return ids

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

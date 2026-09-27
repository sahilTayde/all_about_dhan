"""Founder emergency controls (roadmap step 14): one POST per command, GET for the history. PAPER only.

Each POST appends one timestamped command (actor, reason) to the durable founder log
(``desk_ml.founder_commands``) and returns the ack once the line is fsync'd. The engine applies
it from that timestamp on its next cycle and reports applied / rejected. A resent
``command_id`` returns the stored ack instead of a second command.

Localhost only, unless ``AAD_FOUNDER_CONTROLS_REMOTE=1`` (put your own auth in front first).
Kill switch, cut loss and re-arm need a single-use token from ``POST /founder/controls/confirm``.
Nothing here places or routes an order.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

REMOTE_ENV = "AAD_FOUNDER_CONTROLS_REMOTE"
LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
TOKEN_TTL_S = 120
KNOWN_INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
_ID = r"^[A-Za-z0-9_.:-]{1,64}$"
_HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


def local_only(request: Request) -> None:
    if os.environ.get(REMOTE_ENV) == "1":
        return
    host = request.client.host if request.client else None
    if host not in LOCAL_HOSTS or "x-forwarded-for" in request.headers:
        raise HTTPException(403, f"founder controls are localhost-only (set {REMOTE_ENV}=1 behind your own auth)")


def data_root(request: Request) -> Path:
    root = getattr(request.app.state, "founder_root", None)
    if root is not None:
        return Path(root)
    from desk_ml.persist import repo_root

    return repo_root()


class ConfirmTokens:
    """Single-use HMAC tokens bound to (kind, trade_id). Per process: a restart voids them."""

    def __init__(self) -> None:
        self._key = secrets.token_bytes(32)
        self._used: dict[str, float] = {}
        self._lock = threading.Lock()

    def _sig(self, kind: str, target: str, exp: int, nonce: str) -> str:
        return hmac.new(self._key, f"{kind}|{target}|{exp}|{nonce}".encode(), hashlib.sha256).hexdigest()[:32]

    def issue(self, kind: str, target: Optional[str], now: float) -> dict[str, Any]:
        exp, nonce = int(now) + TOKEN_TTL_S, secrets.token_hex(8)
        return {"confirm_token": f"{exp}.{nonce}.{self._sig(kind, target or '', exp, nonce)}", "expires_in_s": TOKEN_TTL_S}

    def consume(self, token: Optional[str], kind: str, target: Optional[str], now: float) -> Optional[str]:
        """None when valid (and now spent); otherwise why not."""
        try:
            exp_s, nonce, sig = str(token or "").split(".")
            exp = int(exp_s)
        except ValueError:
            return "missing or malformed confirmation token"
        if not hmac.compare_digest(sig, self._sig(kind, target or "", exp, nonce)):
            return "confirmation token is for a different command"
        if now > exp:
            return "confirmation token expired"
        with self._lock:
            self._used = {t: e for t, e in self._used.items() if e >= now}
            if token in self._used:
                return "confirmation token already used"
            self._used[str(token)] = exp
        return None


TOKENS = ConfirmTokens()


# ------------------------------------------------------------------ bodies


class _Cmd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: Optional[str] = Field(None, pattern=_ID, description="idempotency key; resend = same command")
    actor: str = Field("founder", min_length=1, max_length=64)
    reason: str = Field(..., min_length=1, max_length=500)


class _Confirmed(_Cmd):
    confirm_token: str = Field(..., min_length=1, max_length=200)


class PauseBody(_Cmd):
    minutes: int = Field(..., ge=0, le=24 * 60, description="0 resumes now")


class Window(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str = Field(..., pattern=_HHMM)
    end: str = Field(..., pattern=_HHMM)


class WindowsBody(_Cmd):
    windows: list[Window] = Field(..., max_length=12, description="IST; replaces the whole list; [] clears")


class TradeBody(_Cmd):
    trade_id: str = Field(..., min_length=1, max_length=200)


class CutLossBody(_Confirmed):
    trade_id: str = Field(..., min_length=1, max_length=200)


class LotsBody(_Cmd):
    lots: Optional[int] = Field(..., ge=1, description="lots for the next fills; null clears")


class IndexBody(_Cmd):
    underlying: str = Field(..., pattern=r"^[A-Z][A-Z0-9]{1,19}$")
    enabled: bool


class MinCapitalBody(_Cmd):
    amount_inr: Optional[float] = Field(..., ge=0, le=1e8, description="null clears")


class FundsBody(_Cmd):
    amount_inr: float = Field(..., gt=0, le=1e8)


class ConfirmBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["KILL", "CUT_LOSS", "REARM"]
    trade_id: Optional[str] = Field(None, min_length=1, max_length=200)


# ----------------------------------------------------------------- helpers


def lots_cap(root: Path) -> Optional[int]:
    """Largest lots override allowed: the engine's paper max and the risk limits for the active mode."""
    try:
        from desk_ml.paper_scalp import PAPER_MAX_LOTS
        from risk_engine.engine import load_limits

        cfg = load_limits(root / "config" / "risk_limits.yaml")
        return min(int(PAPER_MAX_LOTS), int(cfg["modes"][cfg["mode"]]["max_lots_per_trade"]))
    except Exception:
        return None


def _ist(ts: float) -> str:
    from desk_ml.founder_commands.book import IST

    return datetime.fromtimestamp(float(ts), IST).isoformat(timespec="seconds")


def _read_board(root: Path) -> dict[str, Any]:
    try:
        blob = json.loads((root / "data" / "recon" / "ml_paper_dashboard.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return blob if isinstance(blob, dict) else {}


def _submit(
    root: Path, kind: str, args: dict[str, Any], body: _Cmd, *, token: Optional[str] = None,
    target: Optional[str] = None,
) -> dict[str, Any]:
    from desk_ml.founder_commands import (
        CONFIRM_KINDS, CommandBook, append_command, make_row, read_commands, validate_args, write_account_view,
    )

    now = time.time()
    cid = body.command_id or uuid.uuid4().hex
    have = next((r for r in read_commands(root).rows if r["id"] == cid), None)
    if have is not None:  # idempotent resend: never re-judge, never a second command
        return _ack(have, duplicate=True, where="log")
    err = validate_args(kind, args)
    if err:
        raise HTTPException(422, err)
    reject = None
    if kind in CONFIRM_KINDS:
        why = TOKENS.consume(token, kind, target, now)
        reject = f"CONFIRMATION_REQUIRED: {why}" if why else None
    elif kind == "SET_LOTS" and args["lots"] is not None:
        cap = lots_cap(root)
        if cap is None:
            reject = "RISK_LIMITS_UNREADABLE: cannot check the lots limit, so no change"
        elif args["lots"] > cap:
            reject = f"LOTS_OVER_LIMIT: at most {cap} lots per trade (engine and risk limits)"
    row = make_row(kind, args, actor=body.actor, reason=body.reason, ts=now, command_id=cid, reject_reason=reject)
    try:
        stored, dup, where = append_command(root, row)
    except OSError as exc:
        raise HTTPException(503, {"recorded": False, "reason": f"command NOT recorded: {exc.strerror or exc}"}) from None
    if kind in {"MIN_CAPITAL", "ADD_FUNDS"} and not reject:
        res = read_commands(root)
        st = CommandBook(res.rows, res.problems, res.blocked_from).state_at(now)
        write_account_view(root, {
            "funds_added_inr": round(st.funds_added, 2), "min_capital_inr": st.min_capital,
            "as_of_ist": _ist(now), "source": "desk_ml.founder_commands log", "paper_only": True,
        })
    ack = _ack(stored, duplicate=dup, where=where)
    if ack["status"] == "rejected":
        raise HTTPException(409, ack)
    return ack


def _ack(row: dict[str, Any], *, duplicate: bool, where: str) -> dict[str, Any]:
    rejected = row.get("status") == "rejected"
    return {
        "ack": True, "recorded": True, "stored_in": where, "duplicate": duplicate,
        "id": row["id"], "kind": row["kind"], "args": row.get("args"), "ts": row["ts"], "ts_ist": _ist(row["ts"]),
        "actor": row["actor"], "reason": row["reason"],
        "status": "rejected" if rejected else "pending", "status_reason": row.get("reject_reason"),
        "note": "PAPER only. The engine applies it from ts on its next cycle.",
    }


def _entries_now(book: Any, now: float) -> Optional[str]:
    """Why new entries are blocked right now (the engine also checks minimum capital per ticket)."""
    from desk_ml.founder_commands import book as b

    if book.blocked_from is not None and now >= book.blocked_from:
        return b.UNREADABLE
    st = book.state_at(now)
    if st.killed_ts is not None:
        return b.KILLED
    if not st.running:
        return b.STOPPED
    if st.pause_until is not None and now < st.pause_until:
        return b.PAUSED
    dt = datetime.fromtimestamp(now, b.IST)
    if any(a <= dt.hour * 60 + dt.minute < z for a, z in st.windows):
        return b.BLOCKED_WINDOW
    return None


# ------------------------------------------------------------------ routes

router = APIRouter(prefix="/founder/controls", tags=["founder-controls"], dependencies=[Depends(local_only)])


@router.get("")
def history(request: Request, limit: int = 200) -> dict[str, Any]:
    """Every command (newest first) with pending / applied / rejected, the current state and open tickets."""
    from desk_ml.founder_commands import CommandBook, read_commands, read_statuses

    root, now = data_root(request), time.time()
    res = read_commands(root)
    book = CommandBook(res.rows, res.problems, res.blocked_from)
    board = _read_board(root)
    live = {r["id"]: r for r in ((board.get("founder_controls") or {}).get("results") or []) if r.get("id")}
    acks = read_statuses(root)
    rows = []
    for row in sorted(res.rows, key=lambda r: float(r["ts"]), reverse=True)[: max(1, min(int(limit), 1000))]:
        ack = _ack(row, duplicate=False, where="log")
        seen = live.get(row["id"]) or {}
        engine = seen if seen.get("status") in {"applied", "rejected"} else acks.get(row["id"]) or seen
        if ack["status"] != "rejected" and engine.get("status") in {"applied", "rejected"}:
            ack["status"], ack["status_reason"] = engine["status"], engine.get("status_reason")
            ack["applied_ts"] = engine.get("applied_ts")
            ack["applied_ist"] = _ist(engine["applied_ts"]) if engine.get("applied_ts") else None
            ack["detail"] = {k: v for k, v in engine.items() if k in {"trade_id", "exit_px", "flattened", "target"}}
        for k in ("ack", "recorded", "stored_in", "duplicate", "note"):
            ack.pop(k)
        rows.append(ack)
    state = book.state_at(now)
    known = sorted(set(KNOWN_INDICES) | set(state.index))
    opens = [
        {k: t.get(k) for k in ("trade_id", "underlying", "side", "atm_strike", "lots", "entry", "last_ltp", "filled",
                                "target", "stop", "founder_t2", "book_id")}
        for t in (board.get("open_trades") or []) if isinstance(t, dict) and t.get("trade_id")
    ]
    return {
        "commands": rows,
        "state": {**state.as_dict(now=now), "entries_blocked_reason": _entries_now(book, now)},
        "problems": res.problems,
        "open_trades": opens,
        "limits": {"max_lots": lots_cap(root), "known_indices": known, "confirm_kinds": ["CUT_LOSS", "KILL", "REARM"]},
        "board_as_of_ist": board.get("as_of_ist"),
        "desk_capital_inr": board.get("starting_desk_inr"),
        "paper_only": True,
        "orders": "REFUSED",
    }


@router.post("/confirm")
def confirm(body: ConfirmBody) -> dict[str, Any]:
    if body.kind == "CUT_LOSS" and not body.trade_id:
        raise HTTPException(422, "CUT_LOSS confirmation needs the trade_id")
    return {"kind": body.kind, "trade_id": body.trade_id, **TOKENS.issue(body.kind, body.trade_id, time.time())}


@router.post("/start")
def start(body: _Cmd, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "START", {}, body)


@router.post("/stop")
def stop(body: _Cmd, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "STOP", {}, body)


@router.post("/pause")
def pause(body: PauseBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "PAUSE", {"minutes": body.minutes}, body)


@router.post("/blocked-windows")
def blocked_windows(body: WindowsBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "BLOCK_WINDOWS", {"windows": [w.model_dump() for w in body.windows]}, body)


@router.post("/cut-loss")
def cut_loss(body: CutLossBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "CUT_LOSS", {"trade_id": body.trade_id}, body,
                   token=body.confirm_token, target=body.trade_id)


@router.post("/go-t2")
def go_t2(body: TradeBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "GO_T2", {"trade_id": body.trade_id}, body)


@router.post("/lots")
def lots(body: LotsBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "SET_LOTS", {"lots": body.lots}, body)


@router.post("/kill")
def kill(body: _Confirmed, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "KILL", {}, body, token=body.confirm_token)


@router.post("/rearm")
def rearm(body: _Confirmed, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "REARM", {}, body, token=body.confirm_token)


@router.post("/index")
def index(body: IndexBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "INDEX", {"underlying": body.underlying, "enabled": body.enabled}, body)


@router.post("/min-capital")
def min_capital(body: MinCapitalBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "MIN_CAPITAL", {"amount_inr": body.amount_inr}, body)


@router.post("/add-funds")
def add_funds(body: FundsBody, request: Request) -> dict[str, Any]:
    return _submit(data_root(request), "ADD_FUNDS", {"amount_inr": body.amount_inr}, body)

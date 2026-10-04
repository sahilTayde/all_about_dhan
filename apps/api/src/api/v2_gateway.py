"""V2-13 gateway: GET /v2/snapshot, WS /v2/ws, V2-11 founder control routes.

Paper only. Browser never talks to Dhan or Redis. Control actions never place
an entry. Timestamps are IST (+05:30). No look-ahead: envelopes with
available_ts in the future are refused. Legacy /ui/* and /ws/* stay as they are.

Auth: Bearer header, first WS message, or Sec-WebSocket-Protocol.
Never a real credential on the URL query. Empty gateway token + empty
JWT secret + bind 127.0.0.1 = localhost-dev (Mac). V2-23 JWT / founder
2FA (packages/auth) fail closed when AAD_JWT_SECRET is set. A client-
supplied role is never trusted. Mutating control commands are rate-
limited (1/s). JWT mode also caps REST 10/s and WS subscribe 5/s.
GET /v2/control is not command-rate-limited. Missing/unknown shared
token = customer. Subscribe cannot change token or role. Control routes
are localhost-only unless the founder token or a founder JWT+2FA is
present. The paper `founder` query token is a role label, not a secret.
"""

from __future__ import annotations

import asyncio
import os
import queue
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, TypedDict

from contracts.envelope import Envelope
from events.bus import EventBus
from events.schema import Event, EventType
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, ConfigDict, Field

from api.gateway_auth import (
    AuthIdentity,
    CommandRateLimiter,
    GatewayAuth,
    audit_control,
    bearer_from_authorization,
    check_host_origin,
    identity_from_headers,
    identity_from_token,
    query_has_auth_attempt,
    tokens_from_protocol,
)

try:
    from auth import AuthRateLimiter, looks_like_jwt, verify_access
    from control.authz import authorize_command as jwt_authorize_command
except (ImportError, TypeError, SyntaxError):  # pragma: no cover - legacy 3.9 venv
    AuthRateLimiter = None  # type: ignore[misc, assignment]
    looks_like_jwt = None  # type: ignore[assignment]
    verify_access = None  # type: ignore[assignment]
    jwt_authorize_command = None  # type: ignore[assignment]

IST = timezone(timedelta(hours=5, minutes=30))
CONTROL_FLAG = "AAD_V2_CONTROL_ROUTES"
MUTATING_CONTROL_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
REMOTE_ENV = "AAD_FOUNDER_CONTROLS_REMOTE"
LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
LOCAL_HOST_HEADERS = frozenset({"127.0.0.1", "localhost", "[::1]"})
CONTROL_KINDS = (
    "START",
    "STOP",
    "PAUSE",
    "BLOCKED_WINDOWS",
    "CUT_LOSS",
    "FLATTEN_ALL",
    "KILL",
    "REARM",
    "SET_LOTS",
    "INDEX",
    "BASKET_REMOVE",
    "MIN_CAPITAL",
    "ADD_FUNDS",
)
FOUNDER_CHANNELS = frozenset(
    {
        "positions",
        "decisions",
        "health",
        "trace",
        "market:NIFTY",
        "market:BANKNIFTY",
        "market:SENSEX",
    }
)
CUSTOMER_CHANNELS = frozenset({"signals:public"})
CUSTOMER_SIGNAL_FIELDS = frozenset(
    {
        "underlying",
        "side",
        "decision",
        "trend",
        "chain_3m",
        "news",
        "cited_news",
    }
)
_HTTP_BASE_KEYS = frozenset(
    {
        "ok",
        "as_of",
        "role",
        "channels",
        "denied",
        "positions",
        "traces",
        "orders",
        "promote",
        "v2",
    }
)
FOUNDER_LEGACY_KEYS = frozenset(
    {
        "board",
        "exam",
        "alerts",
        "days",
        "account",
        "founder",
        "founder_book",
        "risk_halt",
        "history_complete",
        "tape_last_ist",
        "health_rows",
    }
)


class RoleAcl(TypedDict):
    channels: frozenset[str]
    snapshot_keys: frozenset[str]
    legacy_keys: frozenset[str]
    signal_fields: frozenset[str]
    trace: bool


# One allow-list per role. Enforced on WS snapshot, WS deltas, /v2/snapshot, /v2/trace.
ROLE_ACL: dict[str, RoleAcl] = {
    "founder": {
        "channels": FOUNDER_CHANNELS | CUSTOMER_CHANNELS,
        "snapshot_keys": _HTTP_BASE_KEYS | FOUNDER_LEGACY_KEYS,
        "legacy_keys": FOUNDER_LEGACY_KEYS,
        "signal_fields": frozenset(),
        "trace": True,
    },
    "customer": {
        "channels": CUSTOMER_CHANNELS,
        "snapshot_keys": _HTTP_BASE_KEYS,
        "legacy_keys": frozenset(),
        "signal_fields": CUSTOMER_SIGNAL_FIELDS,
        "trace": False,
    },
}
ROLE_CHANNELS: dict[str, frozenset[str]] = {
    role: spec["channels"] for role, spec in ROLE_ACL.items()
}
_POS_TYPES = frozenset({"POSITION_UPDATE", "POSITION_CLOSED"})
_DEC_TYPES = frozenset(
    {
        "DECISION",
        "SIGNAL",
        "RISK_DECISION",
        "ENTRY_VETOED",
        "ENTRY_APPROVED",
        "NO_ENTRY",
    }
)
_HEALTH_TYPES = frozenset({"HEALTH_ALERT", "ENGINE_STATUS", "FEED_STATUS"})
_MKT_TYPES = frozenset(
    {"TICK", "MARKET_TICK", "BAR_CLOSED", "QUOTE_SNAPSHOT", "CHAIN_SNAPSHOT"}
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class LiveIstClock:
    def now(self) -> datetime:
        return datetime.now(IST)


def ist_iso(now: datetime | None = None) -> str:
    dt = (now or datetime.now(IST)).astimezone(IST)
    text = dt.isoformat(timespec="milliseconds")
    return (
        text
        if text.endswith("+05:30")
        else dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+05:30"
    )


def parse_ist(raw: str) -> datetime:
    dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware IST")
    return dt.astimezone(IST)


def role_from_token(token: str | None) -> str:
    """Paper labels only — not credentials. Founder iff token == founder."""
    return "founder" if (token or "").strip().lower() == "founder" else "customer"


def resolve_role(role: str | None, token: str | None) -> str:
    """Token decides. Client-supplied role is ignored (never trusted)."""
    del role
    return role_from_token(token)


def acl_for(role: str) -> RoleAcl:
    return ROLE_ACL.get(role, ROLE_ACL["customer"])


def channel_for(env: Envelope) -> str | None:
    kind = env.event_type
    if kind in _POS_TYPES:
        return "positions"
    if kind in _DEC_TYPES:
        return "decisions"
    if kind in _HEALTH_TYPES:
        return "health"
    if kind in _MKT_TYPES:
        und = str(env.payload.get("underlying") or "").upper()
        if not und:
            inst = str(env.payload.get("instrument_id") or "")
            parts = inst.split(":")
            und = parts[1].upper() if len(parts) > 1 else ""
        return f"market:{und}" if und in {"NIFTY", "BANKNIFTY", "SENSEX"} else None
    return None


def customer_safe(payload: dict[str, Any]) -> dict[str, Any]:
    """CUSTOMER_TALK.md: trend + 3m chain + cited news. No indicator soup."""
    fields = ROLE_ACL["customer"]["signal_fields"]
    return {k: payload[k] for k in fields if k in payload and payload[k] is not None}


def envelope_for_role(role: str, envelope: dict[str, Any]) -> dict[str, Any]:
    fields = acl_for(role)["signal_fields"]
    payload = envelope.get("payload")
    if not fields or not isinstance(payload, dict):
        return envelope
    return {**envelope, "payload": customer_safe(payload)}


def project_snapshot(role: str, body: dict[str, Any]) -> dict[str, Any]:
    allowed = acl_for(role)["snapshot_keys"]
    return {k: v for k, v in body.items() if k in allowed}


def apply_legacy_overlay(role: str, body: dict[str, Any], ui: dict[str, Any]) -> None:
    """Founder-only desk overlay. Customers get no legacy board/account/founder keys."""
    if not ui:
        return
    for key in acl_for(role)["legacy_keys"]:
        if key == "health_rows":
            if "health" in ui:
                body["health_rows"] = ui.get("health")
            continue
        if key in ui:
            body[key] = ui[key]


def _pid(row: dict[str, Any]) -> str:
    return str(row.get("position_id") or row.get("trade_id") or "")


@dataclass
class WsClient:
    role: str
    channels: frozenset[str]
    last_seq: dict[str, int]
    outbound: queue.SimpleQueue[dict[str, Any]]
    suppress: set[int] = field(default_factory=set)

    def push(self, msg: dict[str, Any]) -> None:
        seq = msg.get("seq")
        if isinstance(seq, int) and seq in self.suppress:
            self.suppress.discard(seq)
            return
        self.outbound.put(msg)


class GatewayHub:
    """Hot state + per-channel seq. Source: MemoryBus and ingest(Envelope)."""

    def __init__(
        self,
        bus: EventBus | None = None,
        *,
        clock: Clock | None = None,
        ledger_open: list[dict[str, Any]] | None = None,
    ) -> None:
        self.clock: Clock = clock or LiveIstClock()
        self.seq: dict[str, int] = {}
        self.hot: dict[str, list[dict[str, Any]]] = {}
        self.traces: dict[str, dict[str, Any]] = {}
        self._ledger_open: dict[str, dict[str, Any]] = {
            _pid(r): r for r in (ledger_open or []) if _pid(r)
        }
        self._clients: list[WsClient] = []
        if bus is not None:
            bus.subscribe([t.value for t in EventType], self._on_bus)

    def set_ledger_open(self, rows: list[dict[str, Any]]) -> None:
        self._ledger_open = {_pid(r): dict(r) for r in rows if _pid(r)}

    def now(self) -> datetime:
        return self.clock.now().astimezone(IST)

    def _on_bus(self, event: Event) -> None:
        env = Envelope.from_json(event.to_json())
        # Legacy MemoryBus events carry wall-clock timestamp. A sim clock in the
        # past would refuse them as lookahead. Delivery on this hub is "now".
        if env.v == 1:
            now = ist_iso(self.now())
            env = replace(env, available_ts=now, event_ts=now, timestamp=now)
        self.ingest(env)

    def ingest(self, env: Envelope) -> int | None:
        """Apply envelope if available_ts <= now. Returns new channel seq, or None if refused."""
        available = parse_ist(env.available_ts)
        if available > self.now():
            return None
        ch = channel_for(env)
        if ch is None:
            self._index_trace(env)
            return None
        n = self.seq.get(ch, 0) + 1
        self.seq[ch] = n
        body = env.to_json()
        self.hot.setdefault(ch, []).append(body)
        if ch == "positions":
            self._apply_position(env)
        self._index_trace(env)
        self._fanout(ch, n, body)
        if env.event_type == "SIGNAL":
            self._fanout_public(env, body)
        return n

    def _apply_position(self, env: Envelope) -> None:
        pid = _pid(env.payload)
        if not pid:
            return
        if env.event_type == "POSITION_CLOSED":
            self._ledger_open.pop(pid, None)
            return
        prev = self._ledger_open.get(pid, {})
        self._ledger_open[pid] = {**prev, **env.payload, "position_id": pid}

    def _index_trace(self, env: Envelope) -> None:
        cid = (
            env.correlation_id
            or env.payload.get("decision_id")
            or env.payload.get("signal_id")
        )
        if not cid:
            return
        row = self.traces.setdefault(
            str(cid),
            {
                "correlation_id": str(cid),
                "envelopes": [],
                "strike_choice": None,
                "alternatives": [],
            },
        )
        row["envelopes"].append(env.to_json())
        choice = env.payload.get("strike_choice")
        if isinstance(choice, dict):
            row["strike_choice"] = choice
            alts = choice.get("alternatives")
            row["alternatives"] = alts if isinstance(alts, list) else []
        self.seq["trace"] = self.seq.get("trace", 0) + 1

    def _fanout(self, channel: str, seq: int, envelope: dict[str, Any]) -> None:
        as_of = ist_iso(self.now())
        for c in self._clients:
            if channel not in acl_for(c.role)["channels"]:
                continue
            if channel not in c.channels:
                continue
            c.push(
                {
                    "op": "delta",
                    "channel": channel,
                    "seq": seq,
                    "envelope": envelope_for_role(c.role, envelope),
                    "as_of": as_of,
                }
            )

    def _fanout_public(self, env: Envelope, body: dict[str, Any]) -> None:
        ch = "signals:public"
        n = self.seq.get(ch, 0) + 1
        self.seq[ch] = n
        safe = {**body, "payload": customer_safe(env.payload)}
        self.hot.setdefault(ch, []).append(safe)
        self._fanout(ch, n, safe)

    def positions(self) -> list[dict[str, Any]]:
        """REG-04c: every ledger-open position, plus hot overlays."""
        return [dict(v) for v in self._ledger_open.values()]

    def allowed(self, role: str, requested: list[str]) -> tuple[list[str], list[str]]:
        scope = acl_for(role)["channels"]
        ok = [c for c in requested if c in scope]
        denied = [c for c in requested if c not in scope]
        return ok, denied

    def snapshot_channel(self, channel: str, role: str = "founder") -> dict[str, Any]:
        if channel not in acl_for(role)["channels"]:
            return {"seq": self.seq.get(channel, 0), "items": []}
        if channel == "positions":
            items: list[Any] = self.positions()
        elif channel == "trace":
            items = list(self.traces.values())
        else:
            items = list(self.hot.get(channel, ()))
        if role != "founder":
            items = [
                envelope_for_role(role, it) if isinstance(it, dict) else it
                for it in items
            ]
        return {"seq": self.seq.get(channel, 0), "items": items}

    def snapshot(self, channels: list[str], role: str) -> dict[str, Any]:
        ok, denied = self.allowed(role, channels)
        body = {
            "ok": True,
            "as_of": ist_iso(self.now()),
            "role": role,
            "channels": {c: self.snapshot_channel(c, role) for c in ok},
            "denied": denied,
            "positions": self.positions() if role == "founder" else [],
            "traces": dict(self.traces) if role == "founder" else {},
            "orders": "REFUSED",
            "promote": False,
            "v2": True,
        }
        return project_snapshot(role, body)

    def connect(self, *, role: str) -> WsClient:
        client = WsClient(
            role=role, channels=frozenset(), last_seq={}, outbound=queue.SimpleQueue()
        )
        self._clients.append(client)
        return client

    def disconnect(self, client: WsClient) -> None:
        if client in self._clients:
            self._clients.remove(client)

    def subscribe(self, client: WsClient, channels: list[str]) -> list[str]:
        ok, denied = self.allowed(client.role, channels)
        client.channels = frozenset(ok)
        as_of = ist_iso(self.now())
        for ch in ok:
            data = self.snapshot_channel(ch, client.role)
            client.last_seq[ch] = int(data["seq"])
            client.push(
                {
                    "op": "snapshot",
                    "channel": ch,
                    "seq": data["seq"],
                    "data": data,
                    "as_of": as_of,
                }
            )
        if denied:
            client.push(
                {
                    "op": "error",
                    "code": "FORBIDDEN_CHANNEL",
                    "denied": denied,
                    "role": client.role,
                }
            )
        return denied

    def resync(self, client: WsClient, channel: str) -> None:
        if (
            channel not in client.channels
            or channel not in acl_for(client.role)["channels"]
        ):
            client.push(
                {
                    "op": "error",
                    "code": "FORBIDDEN_CHANNEL",
                    "denied": [channel],
                    "role": client.role,
                }
            )
            return
        data = self.snapshot_channel(channel, client.role)
        client.last_seq[channel] = int(data["seq"])
        client.push(
            {
                "op": "snapshot",
                "channel": channel,
                "seq": data["seq"],
                "data": data,
                "as_of": ist_iso(self.now()),
                "resync": True,
            }
        )

    def handle_op(self, client: WsClient, body: dict[str, Any]) -> None:
        if "role" in body or "token" in body:
            client.push(
                {
                    "op": "error",
                    "code": "IDENTITY_IMMUTABLE",
                    "role": client.role,
                    "note": "role and token are fixed at connect from the authenticated token",
                }
            )
            body = {k: v for k, v in body.items() if k not in {"role", "token"}}
        op = str(body.get("op") or "")
        if op == "subscribe":
            chans = [str(c) for c in (body.get("channels") or [])]
            self.subscribe(client, chans)
        elif op == "resync":
            self.resync(client, str(body.get("channel") or ""))
        elif op == "ping":
            client.push({"op": "pong", "as_of": ist_iso(self.now())})


def envelope_from_parts(
    event_type: str,
    payload: dict[str, Any],
    *,
    available_ts: str,
    event_ts: str | None = None,
    stream: str = "test",
    source: str = "test",
    correlation_id: str | None = None,
    event_id: str | None = None,
    account_id: str | None = None,
) -> Envelope:
    ts = event_ts or available_ts
    return Envelope(
        v=2,
        event_type=event_type,
        event_id=event_id or "0" * 32,
        stream=stream,
        source=source,
        event_ts=ts,
        available_ts=available_ts,
        timestamp=ts,
        account_id=account_id,
        correlation_id=correlation_id,
        causation_id=None,
        payload=payload,
    )


def _legacy_ui() -> dict[str, Any]:
    """Read-only desk snapshot so /v2/snapshot can drive Desk/Founder. Never writes."""
    from api import ui_feed

    try:
        return ui_feed.build_snapshot(budget_s=ui_feed.SNAPSHOT_BUDGET_S)
    except Exception:  # noqa: BLE001 — UI overlay is advisory; v2 channels must still load
        return {}


router = APIRouter()


def _settings(request: Request) -> GatewayAuth:
    return request.app.state.v2_auth  # type: ignore[no-any-return]


def _now_ts(request: Request) -> float:
    hub: GatewayHub = request.app.state.v2_hub
    return hub.clock.now().timestamp()


def _jwt_decision(token: str | None, settings: GatewayAuth, now: float) -> Any:
    if verify_access is None or looks_like_jwt is None or not settings.jwt_secret:
        return None
    if not looks_like_jwt(token):
        return None
    return verify_access(token, settings.jwt_secret, now)


def _attach_jwt(
    request: Request, ident: AuthIdentity | None, settings: GatewayAuth
) -> AuthIdentity | None:
    request.state.v2_auth_decision = None
    bearer = bearer_from_authorization(request.headers.get("authorization"))
    decision = _jwt_decision(bearer, settings, _now_ts(request))
    if decision is None:
        return ident
    if not decision.ok:
        raise HTTPException(
            status_code=401,
            detail={
                "ok": False,
                "code": str(decision.reason).upper(),
                "orders": "REFUSED",
            },
        )
    request.state.v2_auth_decision = decision
    return AuthIdentity(role=decision.role, source="jwt")


def _rate_limit_rest(request: Request) -> None:
    settings = _settings(request)
    limiter = getattr(request.app.state, "v2_auth_rates", None)
    if not settings.jwt_required or limiter is None:
        return
    key = request.client.host if request.client else "unknown"
    if limiter.allow(f"rest:{key}", "rest"):
        return
    raise HTTPException(
        status_code=429,
        detail={"ok": False, "code": "RATE_LIMIT", "orders": "REFUSED"},
    )


def _http_identity(request: Request, *, control: bool = False) -> AuthIdentity | None:
    settings = _settings(request)
    reason = check_host_origin(
        request.headers.get("host"), request.headers.get("origin"), settings
    )
    if reason:
        raise HTTPException(
            status_code=403,
            detail={"ok": False, "code": reason.upper(), "orders": "REFUSED"},
        )
    if query_has_auth_attempt(request.url.query):
        raise HTTPException(
            status_code=401,
            detail={"ok": False, "code": "QUERY_TOKEN_REFUSED", "orders": "REFUSED"},
        )
    ident = identity_from_headers(request.headers.get("authorization"), None, settings)
    ident = _attach_jwt(request, ident, settings)
    if settings.auth_required and ident is None:
        raise HTTPException(
            status_code=401,
            detail={"ok": False, "code": "UNAUTHORIZED", "orders": "REFUSED"},
        )
    if not control:
        _rate_limit_rest(request)
    return ident


def _rate_limit_command(request: Request) -> None:
    """1/s on POST /v2/control/commands after authorize. GET/confirm are not limited."""
    limiter: CommandRateLimiter = request.app.state.v2_limiter
    key = request.client.host if request.client else "unknown"
    if limiter.allow(key):
        return
    audit_control(
        result="rate_limited",
        method=request.method,
        path=request.url.path,
    )
    raise HTTPException(
        status_code=429,
        detail={"ok": False, "code": "RATE_LIMIT", "orders": "REFUSED"},
    )


def _role_for(ident: AuthIdentity | None, paper_token: str) -> str:
    return ident.role if ident is not None else role_from_token(paper_token)


@router.get("/v2/snapshot")
def v2_snapshot(
    request: Request,
    channels: str = Query(default="positions,decisions,health,market:NIFTY"),
    role: str = Query(default=""),
    token: str = Query(default=""),
) -> dict[str, Any]:
    del role  # never trusted; token only
    ident = _http_identity(request)
    who = _role_for(ident, token)
    chans = [c.strip() for c in channels.split(",") if c.strip()]
    hub: GatewayHub = request.app.state.v2_hub
    body = hub.snapshot(chans, who)
    apply_legacy_overlay(who, body, _legacy_ui())
    return project_snapshot(who, body)


@router.get("/v2/trace")
def v2_trace(
    request: Request,
    trade_id: str | None = None,
    correlation_id: str | None = None,
    token: str = Query(default=""),
    role: str = Query(default=""),
) -> dict[str, Any]:
    del role  # never trusted; token only
    ident = _http_identity(request)
    who = _role_for(ident, token)
    if not acl_for(who)["trace"]:
        raise HTTPException(
            status_code=403,
            detail={
                "ok": False,
                "code": "FOUNDER_ONLY",
                "role": who,
                "orders": "REFUSED",
            },
        )
    hub: GatewayHub = request.app.state.v2_hub
    cid = correlation_id or trade_id
    row = hub.traces.get(cid or "")
    if row:
        choice = row.get("strike_choice") or {}
        return {
            "ok": True,
            "trade_id": trade_id or cid,
            "correlation_id": row["correlation_id"],
            "strike_choice": choice,
            "alternatives": row.get("alternatives") or choice.get("alternatives") or [],
            "envelopes": row["envelopes"],
            "steps": _trace_steps(row),
            "orders": "REFUSED",
        }
    from api import ui_feed

    return ui_feed.trade_trace(trade_id=trade_id or "", budget_s=1.0)


def _trace_steps(row: dict[str, Any]) -> list[dict[str, Any]]:
    choice = row.get("strike_choice") or {}
    alts = row.get("alternatives") or choice.get("alternatives") or []
    chosen = choice.get("chosen")
    reason = choice.get("reason")
    decided = f"{chosen} ({reason})" if chosen else None
    return [
        {
            "id": "desk",
            "title": "Desk",
            "status": "OK" if decided else "NO_DATA",
            "decided": decided,
            "why": reason,
            "fields": {"strike_choice": choice, "alternatives": alts},
            "source": "v2 correlation",
        }
    ]


def _host_name(header: str | None) -> str:
    h = str(header or "").strip().lower()
    if h.startswith("["):
        return h[: h.find("]") + 1] if "]" in h else h
    return h.split(":")[0]


def authorize_control(request: Request, token: str | None) -> None:
    """Founder JWT+2FA, founder paper token, or localhost. Customer never passes."""
    decision = getattr(request.state, "v2_auth_decision", None)
    if decision is not None and jwt_authorize_command is not None:
        why = jwt_authorize_command(decision, required=True)
        if why:
            raise HTTPException(
                403,
                {"ok": False, "code": why.upper(), "orders": "REFUSED"},
            )
        return
    raw = (token or "").strip()
    if raw and role_from_token(raw) != "founder":
        raise HTTPException(403, "founder controls are founder-only")
    if role_from_token(raw) == "founder":
        return
    host = request.client.host if request.client else None
    local = (
        host in LOCAL_HOSTS
        and _host_name(request.headers.get("host")) in LOCAL_HOST_HEADERS
        and "x-forwarded-for" not in request.headers
        and os.environ.get(REMOTE_ENV) != "1"
    )
    if local:
        return
    raise HTTPException(
        403, "founder controls are localhost-only unless V2-13 auth is on"
    )


class ConfirmBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(..., min_length=1, max_length=32)
    target: str | None = Field(None, max_length=200)


class CommandBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(..., min_length=1, max_length=32)
    args: dict[str, Any] = Field(default_factory=dict)
    command_id: str | None = Field(None, max_length=64)
    actor: str = Field("founder", min_length=1, max_length=64)
    reason: str = Field(..., min_length=1, max_length=500)
    confirm_token: str | None = Field(None, max_length=200)
    available_ts: str | None = None


@router.get("/v2/control")
def v2_control_surface(request: Request, token: str = "") -> dict[str, Any]:
    """Real V2-11 surface. GET is not rate-limited; query credentials still refused."""
    _http_identity(request, control=True)
    authorize_control(request, token)
    from control.kinds import KINDS

    handler = getattr(request.app.state, "v2_control", None)
    state = (
        handler.book().state_at(handler.clock.now().timestamp()).as_dict()
        if handler
        else {}
    )
    return {
        "stub": False,
        "ticket": "V2-11",
        "implemented": True,
        "flag": CONTROL_FLAG,
        "enabled": True,
        "kinds": list(KINDS),
        "state": state,
        "orders": "REFUSED",
    }


@router.post("/v2/control/confirm")
def v2_control_confirm(
    request: Request, body: ConfirmBody, token: str = ""
) -> dict[str, Any]:
    _http_identity(request, control=True)
    authorize_control(request, token)
    from control.kinds import CONFIRM_KINDS, canonical_kind
    from control.tokens import ConfirmTokens

    kind = canonical_kind(body.kind)
    if kind not in CONFIRM_KINDS:
        raise HTTPException(422, f"{kind} does not need a confirm token")
    tokens: ConfirmTokens = request.app.state.v2_tokens
    hub: GatewayHub = request.app.state.v2_hub
    return tokens.issue(kind, body.target, hub.clock.now().timestamp())


@router.post("/v2/control/commands", response_model=None)
def v2_control_command(
    request: Request, body: CommandBody, token: str = ""
) -> dict[str, Any]:
    """Apply one founder command. Rate-limited. Idempotent. Never places an entry."""
    _http_identity(request, control=True)
    authorize_control(request, token)
    _rate_limit_command(request)
    from control.handler import submit
    from control.kinds import CONFIRM_KINDS, KINDS, canonical_kind, validate_args

    kind = canonical_kind(body.kind)
    if kind not in KINDS:
        audit_control(
            result="unknown_kind",
            kind=kind,
            method=request.method,
            path=request.url.path,
        )
        raise HTTPException(422, f"unknown kind {kind!r}")
    err = validate_args(kind, body.args)
    if err:
        audit_control(
            result="invalid_args",
            kind=kind,
            method=request.method,
            path=request.url.path,
        )
        raise HTTPException(422, err)
    if kind in CONFIRM_KINDS:
        tokens = request.app.state.v2_tokens
        target = None
        if kind == "CUT_LOSS":
            target = str(
                body.args.get("position_id")
                or body.args.get("trade_id")
                or body.args.get("instrument_id")
                or ""
            )
        why = tokens.consume(
            body.confirm_token,
            kind,
            target,
            request.app.state.v2_hub.clock.now().timestamp(),
        )
        if why:
            audit_control(
                result="confirm_required",
                kind=kind,
                method=request.method,
                path=request.url.path,
            )
            raise HTTPException(422, why)
    handler = request.app.state.v2_control
    cid = body.command_id or uuid.uuid4().hex[:16]
    existing = handler.store.get(cid)
    if existing is not None and existing.get("status") in {"applied", "rejected"}:
        ack = existing
    else:
        ack = submit(
            handler,
            kind,
            dict(body.args),
            actor=body.actor,
            reason=body.reason,
            command_id=cid,
            available_ts=body.available_ts or handler.clock.now(),
        )
        if handler.bus is not None:
            handler.bus.publish(
                "FOUNDER_COMMAND",
                {
                    "command_id": cid,
                    "kind": kind,
                    "args": dict(body.args),
                    "actor": body.actor,
                    "reason": body.reason,
                    "available_ts": ack.get("available_ts"),
                },
                source="gateway",
            )
    audit_control(
        result=str(ack.get("status") or "applied"),
        kind=kind,
        method=request.method,
        path=request.url.path,
    )
    return {
        "stub": False,
        "ticket": "V2-11",
        "implemented": True,
        "command_id": ack.get("command_id") or cid,
        "status": ack.get("status"),
        "reason": ack.get("status_reason"),
        "kind": kind,
        "actor": body.actor,
        "who": body.actor,
        "when": ack.get("applied_ts") or ack.get("available_ts"),
        "why": body.reason,
        "applied": ack.get("status") == "applied",
        "orders": "REFUSED"
        if kind not in {"CUT_LOSS", "FLATTEN_ALL", "KILL"}
        else "EXIT_ONLY",
    }


@router.websocket("/v2/ws")
async def v2_ws(
    websocket: WebSocket,
    role: str = "",
    token: str = "",
    channels: str = "",
) -> None:
    del role  # never trusted; paper query token is role-only in localhost-dev
    settings: GatewayAuth = websocket.app.state.v2_auth
    reason = check_host_origin(
        websocket.headers.get("host"), websocket.headers.get("origin"), settings
    )
    if reason:
        raise HTTPException(
            status_code=403,
            detail={"ok": False, "code": reason.upper(), "orders": "REFUSED"},
        )
    if query_has_auth_attempt(websocket.url.query):
        raise HTTPException(
            status_code=401,
            detail={"ok": False, "code": "QUERY_TOKEN_REFUSED", "orders": "REFUSED"},
        )
    ident = identity_from_headers(
        websocket.headers.get("authorization"),
        websocket.headers.get("sec-websocket-protocol"),
        settings,
    )
    jwt_now = websocket.app.state.v2_hub.clock.now().timestamp()
    bearer = bearer_from_authorization(websocket.headers.get("authorization"))
    if bearer is None:
        for _offered, cand in tokens_from_protocol(
            websocket.headers.get("sec-websocket-protocol")
        ):
            bearer = cand
            break
    decision = _jwt_decision(bearer, settings, jwt_now)
    if decision is not None:
        if not decision.ok:
            await websocket.accept()
            await websocket.send_json(
                {"op": "error", "code": str(decision.reason).upper()}
            )
            await websocket.close(code=4401)
            return
        ident = AuthIdentity(
            role=decision.role,
            source="jwt",
            subprotocol=getattr(ident, "subprotocol", None) if ident else None,
        )
    first: dict[str, Any] | None = None
    if settings.auth_required and ident is None:
        await websocket.accept()
        try:
            raw_first = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        except Exception:  # noqa: BLE001 — handshake timeout or non-JSON
            await websocket.close(code=4401)
            return
        if not isinstance(raw_first, dict):
            await websocket.close(code=4401)
            return
        first_token = str(raw_first.get("token") or "") or None
        decision = _jwt_decision(first_token, settings, jwt_now)
        if decision is not None:
            if not decision.ok:
                await websocket.send_json(
                    {"op": "error", "code": str(decision.reason).upper()}
                )
                await websocket.close(code=4401)
                return
            ident = AuthIdentity(role=decision.role, source="jwt")
        else:
            ident = identity_from_token(first_token, settings)
        if ident is None:
            await websocket.send_json({"op": "error", "code": "UNAUTHORIZED"})
            await websocket.close(code=4401)
            return
        first = {k: v for k, v in raw_first.items() if k != "token"}
    elif ident is not None and ident.subprotocol:
        await websocket.accept(subprotocol=ident.subprotocol)
    else:
        await websocket.accept()
    hub: GatewayHub = websocket.app.state.v2_hub
    who = _role_for(ident, token)
    client = hub.connect(role=who)
    if first:
        hub.handle_op(client, first)
    elif channels.strip():
        hub.subscribe(client, [c.strip() for c in channels.split(",") if c.strip()])
    try:
        while True:
            while True:
                try:
                    await websocket.send_json(client.outbound.get_nowait())
                except queue.Empty:
                    break
            try:
                body = await asyncio.wait_for(websocket.receive_json(), timeout=0.05)
            except TimeoutError:
                continue
            if isinstance(body, dict):
                if (
                    body.get("op") == "subscribe"
                    and settings.jwt_required
                    and getattr(websocket.app.state, "v2_auth_rates", None) is not None
                ):
                    key = websocket.client.host if websocket.client else "unknown"
                    if not websocket.app.state.v2_auth_rates.allow(
                        f"ws:{key}", "ws_subscribe"
                    ):
                        await websocket.send_json(
                            {"op": "error", "code": "RATE_LIMIT", "orders": "REFUSED"}
                        )
                        continue
                hub.handle_op(client, body)
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(client)


def desk_state_dir() -> Path:
    """Persistent desk root (same tree as the ledger). Tests set AAD_STATE_DIR."""
    import sys

    env = os.environ.get("AAD_STATE_DIR")
    if env:
        return Path(env)
    # pytest collection imports create_app() before PYTEST_CURRENT_TEST exists.
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        import tempfile

        return Path(tempfile.mkdtemp(prefix="aad-ctl-"))
    return Path.cwd()


def _wire_paper_desk(
    handler: Any, clock: Any, bus: EventBus | None, root: Path
) -> None:
    """Paper router + manager so HTTP KILL/FLATTEN actually flatten. Never DhanBroker."""
    from brokers.factory import make_broker  # type: ignore[import-untyped]
    from oms import OrderRouter, PositionManager  # type: ignore[import-untyped]
    from oms.ledger_stub import MemoryLedger  # type: ignore[import-untyped]
    from risk_engine.last_good import V2RiskEngine  # type: ignore[import-untyped]

    store = MemoryLedger()
    risk = V2RiskEngine(ledger=store, root=root, bus=bus)
    broker = make_broker(mode="paper", clock=clock)
    router = OrderRouter(
        clock=clock, risk=risk, broker=broker, store=store, bus=bus, controls=handler
    )
    manager = PositionManager(clock=clock, router=router, store=store, bus=bus)
    handler.manager = manager
    handler.risk = risk
    handler._sync_lots_cap()


def attach_gateway(app: Any, bus: EventBus | None = None) -> GatewayHub:
    from control.handler import ControlHandler
    from control.tokens import ConfirmTokens

    now_raw = os.environ.get("AAD_NOW")
    clock = None
    if now_raw:
        from contracts.clock import SimClock

        dt = datetime.fromisoformat(now_raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        clock = SimClock(dt)
    hub = GatewayHub(bus, clock=clock)
    app.state.v2_hub = hub
    app.state.v2_bus = bus
    handler = getattr(app.state, "v2_control", None)
    if handler is None:
        root = desk_state_dir()
        ledger_dir = root / "data" / "ledger"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        handler = ControlHandler(
            bus=bus,
            clock=hub.clock,
            root=root,
            kill_switch_path=ledger_dir / "KILL_SWITCH",
        )
        _wire_paper_desk(handler, hub.clock, bus, root)
        app.state.v2_control = handler
        app.state.v2_desk_root = root
        if bus is not None:

            def _on_cmd(event: Event) -> None:
                handler.on_bus_event(event)

            bus.subscribe(["FOUNDER_COMMAND"], _on_cmd, priority=0)
    if getattr(app.state, "v2_tokens", None) is None:
        app.state.v2_tokens = ConfirmTokens()
    if (
        getattr(app.state, "v2_auth_rates", None) is None
        and AuthRateLimiter is not None
    ):
        app.state.v2_auth_rates = AuthRateLimiter()
    return hub


__all__ = [
    "CONTROL_FLAG",
    "CONTROL_KINDS",
    "CUSTOMER_CHANNELS",
    "CUSTOMER_SIGNAL_FIELDS",
    "FOUNDER_CHANNELS",
    "FOUNDER_LEGACY_KEYS",
    "IST",
    "MUTATING_CONTROL_METHODS",
    "ROLE_ACL",
    "GatewayHub",
    "WsClient",
    "acl_for",
    "attach_gateway",
    "envelope_from_parts",
    "ist_iso",
    "resolve_role",
    "role_from_token",
    "router",
]

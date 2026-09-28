"""V2-13 gateway: GET /v2/snapshot, WS /v2/ws, V2-11 control-route stub.

Paper only. Browser never talks to Dhan or Redis. No founder control actions.
Timestamps are IST (+05:30). No look-ahead: envelopes with available_ts in the
future are refused. Legacy /ui/* and /ws/* stay as they are.

Identity is the paper token only (JWT is V2-23). A client-supplied role is
never trusted. Missing/unknown token = customer. Subscribe cannot change
token or role.
"""

from __future__ import annotations

import asyncio
import os
import queue
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
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

IST = timezone(timedelta(hours=5, minutes=30))
CONTROL_FLAG = "AAD_V2_CONTROL_ROUTES"
# V2-11 STUB — surface only. Do not apply START/STOP/KILL/… here.
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


@router.get("/v2/snapshot")
def v2_snapshot(
    request: Request,
    channels: str = Query(default="positions,decisions,health,market:NIFTY"),
    role: str = Query(default=""),
    token: str = Query(default=""),
) -> dict[str, Any]:
    del role  # never trusted; token only
    who = role_from_token(token)
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
    who = role_from_token(token)
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


@router.get("/v2/control")
def v2_control_surface() -> dict[str, Any]:
    """V2-11 STUB: lists the founder-control route surface. Does not apply commands."""
    return {
        "stub": True,
        "ticket": "V2-11",
        "implemented": False,
        "flag": CONTROL_FLAG,
        "enabled": os.environ.get(CONTROL_FLAG) == "1",
        "kinds": list(CONTROL_KINDS),
        "note": "V2-11 STUB: route surface only. Founder control actions are not implemented.",
        "orders": "REFUSED",
    }


@router.post("/v2/control/commands", response_model=None)
def v2_control_command() -> dict[str, Any]:
    """V2-11 STUB: never applies START/STOP/KILL/CUT_LOSS/…. Always 501."""
    body = {
        "stub": True,
        "ticket": "V2-11",
        "implemented": False,
        "applied": False,
        "note": "V2-11 STUB: founder control actions are not implemented on this branch.",
        "orders": "REFUSED",
    }
    if os.environ.get(CONTROL_FLAG) != "1":
        body["reason"] = f"{CONTROL_FLAG} is off"
    raise HTTPException(status_code=501, detail=body)
    return body


@router.websocket("/v2/ws")
async def v2_ws(
    websocket: WebSocket,
    role: str = "",
    token: str = "",
    channels: str = "",
) -> None:
    del role  # never trusted; token only
    await websocket.accept()
    hub: GatewayHub = websocket.app.state.v2_hub
    who = role_from_token(token)
    client = hub.connect(role=who)
    if channels.strip():
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
                hub.handle_op(client, body)
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(client)


def attach_gateway(app: Any, bus: EventBus | None = None) -> GatewayHub:
    hub = GatewayHub(bus)
    app.state.v2_hub = hub
    app.state.v2_bus = bus
    return hub


__all__ = [
    "CONTROL_FLAG",
    "CONTROL_KINDS",
    "CUSTOMER_CHANNELS",
    "CUSTOMER_SIGNAL_FIELDS",
    "FOUNDER_CHANNELS",
    "FOUNDER_LEGACY_KEYS",
    "IST",
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

"""V2-13 gateway: GET /v2/snapshot, WS /v2/ws, V2-11 control-route stub.

Paper only. Browser never talks to Dhan or Redis. No founder control actions.
Timestamps are IST (+05:30). No look-ahead: envelopes with available_ts in the
future are refused. Legacy /ui/* and /ws/* stay as they are.
"""

from __future__ import annotations

import asyncio
import os
import queue
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from contracts.envelope import Envelope
from events.bus import EventBus  # type: ignore[import-untyped]
from events.schema import Event, EventType  # type: ignore[import-untyped]
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
ROLE_CHANNELS: dict[str, frozenset[str]] = {
    "founder": FOUNDER_CHANNELS | CUSTOMER_CHANNELS,
    "customer": CUSTOMER_CHANNELS,
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


def resolve_role(role: str | None, token: str | None) -> str:
    """Paper role labels only — not credentials. customer token cannot be founder."""
    r = (role or "").strip().lower()
    t = (token or "").strip().lower()
    if t == "customer" or r == "customer":
        return "customer"
    return "founder"


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
    return {
        k: payload[k]
        for k in (
            "underlying",
            "side",
            "decision",
            "trend",
            "chain_3m",
            "news",
            "cited_news",
        )
        if k in payload and payload[k] is not None
    }


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
        self.ingest(Envelope.from_json(event.to_json()))

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
        msg = {
            "op": "delta",
            "channel": channel,
            "seq": seq,
            "envelope": envelope,
            "as_of": ist_iso(self.now()),
        }
        for c in self._clients:
            if channel in c.channels:
                c.push(msg)

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
        scope = ROLE_CHANNELS.get(role, CUSTOMER_CHANNELS)
        ok = [c for c in requested if c in scope]
        denied = [c for c in requested if c not in scope]
        return ok, denied

    def snapshot_channel(self, channel: str) -> dict[str, Any]:
        if channel == "positions":
            items: list[Any] = self.positions()
        elif channel == "trace":
            items = list(self.traces.values())
        else:
            items = list(self.hot.get(channel, ()))
        return {"seq": self.seq.get(channel, 0), "items": items}

    def snapshot(self, channels: list[str], role: str) -> dict[str, Any]:
        ok, denied = self.allowed(role, channels)
        return {
            "ok": True,
            "as_of": ist_iso(self.now()),
            "role": role,
            "channels": {c: self.snapshot_channel(c) for c in ok},
            "denied": denied,
            "positions": self.positions() if role == "founder" else [],
            "traces": dict(self.traces) if role == "founder" else {},
            "orders": "REFUSED",
            "promote": False,
            "v2": True,
        }

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
            data = self.snapshot_channel(ch)
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
        if channel not in client.channels:
            client.push(
                {
                    "op": "error",
                    "code": "FORBIDDEN_CHANNEL",
                    "denied": [channel],
                    "role": client.role,
                }
            )
            return
        data = self.snapshot_channel(channel)
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
    role: str = Query(default="founder"),
    token: str = Query(default=""),
) -> dict[str, Any]:
    who = resolve_role(role, token)
    chans = [c.strip() for c in channels.split(",") if c.strip()]
    hub: GatewayHub = request.app.state.v2_hub
    body = hub.snapshot(chans, who)
    ui = _legacy_ui()
    if ui:
        for key in (
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
        ):
            if key in ui:
                body[key] = ui[key]
        body["health_rows"] = ui.get("health")
    return body


@router.get("/v2/trace")
def v2_trace(
    request: Request,
    trade_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
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
    role: str = "founder",
    token: str = "",
    channels: str = "",
) -> None:
    await websocket.accept()
    hub: GatewayHub = websocket.app.state.v2_hub
    who = resolve_role(role, token)
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
                if "role" in body or "token" in body:
                    client.role = resolve_role(
                        str(body.get("role") or client.role),
                        str(body.get("token") or token),
                    )
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
    "FOUNDER_CHANNELS",
    "IST",
    "GatewayHub",
    "WsClient",
    "attach_gateway",
    "envelope_from_parts",
    "ist_iso",
    "resolve_role",
    "router",
]

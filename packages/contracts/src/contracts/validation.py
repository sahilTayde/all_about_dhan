"""JSON schema validation and JSON-to-dataclass loaders for V2 events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft7Validator, FormatChecker
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from contracts import payloads

_SCHEMAS_DIR = Path(__file__).parent / "schemas"
_REGISTRY: Registry | None = None


def _build_registry() -> Registry:
    """Build a referencing.Registry with all schemas in the schemas/ directory."""
    resources = {}
    for schema_file in _SCHEMAS_DIR.glob("*.json"):
        schema_data = json.loads(schema_file.read_text())
        # Use the filename as the URI (e.g. "exit_plan.json")
        uri = schema_file.name
        resources[uri] = Resource.from_contents(schema_data, default_specification=DRAFT7)
    return Registry().with_resources([(uri, res) for uri, res in resources.items()])


def _get_registry() -> Registry:
    """Get or create the schema registry (cached)."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def _load_schema(name: str) -> dict[str, Any]:
    """Load JSON schema by name."""
    schema_path = _SCHEMAS_DIR / f"{name}.json"
    data: dict[str, Any] = json.loads(schema_path.read_text())
    return data


def validate_payload(payload_type: str, data: dict[str, Any]) -> None:
    """
    Validate payload data against JSON schema (with $ref resolution via Registry).

    Raises:
        ImportError: If jsonschema is not installed.
        jsonschema.ValidationError: If validation fails.
    """
    if not HAS_JSONSCHEMA:
        raise ImportError("jsonschema is required for validation (install with test extra)")

    schema = _load_schema(payload_type)
    registry = _get_registry()
    validator = Draft7Validator(schema, registry=registry, format_checker=FormatChecker())
    validator.validate(data)


# JSON-to-dataclass loaders for all section 4.4 types


def load_tick(data: dict[str, Any]) -> payloads.Tick:
    """Load TICK from JSON dict."""
    validate_payload("tick", data)
    return payloads.Tick(**data)


def load_depth_quote(data: dict[str, Any]) -> payloads.DepthQuote:
    """Load DEPTH_QUOTE from JSON dict."""
    validate_payload("depth_quote", data)
    return payloads.DepthQuote(**data)


def load_quote_snapshot(data: dict[str, Any]) -> payloads.QuoteSnapshot:
    """Load QUOTE_SNAPSHOT from JSON dict."""
    validate_payload("quote_snapshot", data)
    return payloads.QuoteSnapshot(**data)


def load_oi_cadence(data: dict[str, Any]) -> payloads.OiCadence:
    """Load OI_CADENCE from JSON dict."""
    validate_payload("oi_cadence", data)
    return payloads.OiCadence(**data)


def load_bar_closed(data: dict[str, Any]) -> payloads.BarClosed:
    """Load BAR_CLOSED from JSON dict."""
    validate_payload("bar_closed", data)
    return payloads.BarClosed(**data)


def load_chain_snapshot(data: dict[str, Any]) -> payloads.ChainSnapshot:
    """Load CHAIN_SNAPSHOT from JSON dict."""
    validate_payload("chain_snapshot", data)
    strikes = [
        payloads.ChainStrike(
            strike=s["strike"],
            ce=payloads.ChainOptionData(**s["ce"]),
            pe=payloads.ChainOptionData(**s["pe"]),
        )
        for s in data["strikes"]
    ]
    return payloads.ChainSnapshot(
        underlying=data["underlying"],
        expiry=data["expiry"],
        spot=data["spot"],
        strikes=strikes,
    )


def load_clock(data: dict[str, Any]) -> payloads.Clock:
    """Load CLOCK from JSON dict."""
    validate_payload("clock", data)
    return payloads.Clock(**data)


def load_feed_status(data: dict[str, Any]) -> payloads.FeedStatus:
    """Load FEED_STATUS from JSON dict."""
    validate_payload("feed_status", data)
    return payloads.FeedStatus(**data)


def load_signal(data: dict[str, Any]) -> payloads.Signal:
    """Load SIGNAL from JSON dict."""
    validate_payload("signal", data)
    return payloads.Signal(**data)


def load_decision(data: dict[str, Any]) -> payloads.Decision:
    """Load DECISION from JSON dict."""
    validate_payload("decision", data)
    return payloads.Decision(**data)


def load_entry_plan(data: dict[str, Any]) -> payloads.EntryPlan:
    """Load ENTRY_PLAN from JSON dict."""
    validate_payload("entry_plan", data)
    return payloads.EntryPlan(**data)


def load_entry_plan_result(data: dict[str, Any]) -> payloads.EntryPlanResult:
    """Load ENTRY_PLAN_RESULT from JSON dict."""
    validate_payload("entry_plan_result", data)
    return payloads.EntryPlanResult(**data)


def load_risk_decision(data: dict[str, Any]) -> payloads.RiskDecision:
    """Load RISK_DECISION from JSON dict."""
    validate_payload("risk_decision", data)
    return payloads.RiskDecision(**data)


def load_order_update(data: dict[str, Any]) -> payloads.OrderUpdate:
    """Load ORDER_UPDATE from JSON dict (maps 'from'/'to' to from_/to_)."""
    validate_payload("order_update", data)
    # Map JSON field names to Python field names (from/to are Python keywords)
    kwargs = {**data}
    if "from" in kwargs:
        kwargs["from_"] = kwargs.pop("from")
    if "to" in kwargs:
        kwargs["to_"] = kwargs.pop("to")
    return payloads.OrderUpdate(**kwargs)


def load_fill(data: dict[str, Any]) -> payloads.Fill:
    """Load FILL from JSON dict."""
    validate_payload("fill", data)
    return payloads.Fill(**data)


def load_position_update(data: dict[str, Any]) -> payloads.PositionUpdate:
    """Load POSITION_UPDATE from JSON dict."""
    validate_payload("position_update", data)
    return payloads.PositionUpdate(**data)


def load_position_closed(data: dict[str, Any]) -> payloads.PositionClosed:
    """Load POSITION_CLOSED from JSON dict."""
    validate_payload("position_closed", data)
    return payloads.PositionClosed(**data)


def load_founder_command(data: dict[str, Any]) -> payloads.FounderCommand:
    """Load FOUNDER_COMMAND from JSON dict."""
    validate_payload("founder_command", data)
    return payloads.FounderCommand(**data)


def load_command_ack(data: dict[str, Any]) -> payloads.CommandAck:
    """Load COMMAND_ACK from JSON dict."""
    validate_payload("command_ack", data)
    return payloads.CommandAck(**data)


def load_advice(data: dict[str, Any]) -> payloads.Advice:
    """Load ADVICE from JSON dict."""
    validate_payload("advice", data)
    return payloads.Advice(**data)


def load_engine_status(data: dict[str, Any]) -> payloads.EngineStatus:
    """Load ENGINE_STATUS from JSON dict."""
    validate_payload("engine_status", data)
    return payloads.EngineStatus(**data)

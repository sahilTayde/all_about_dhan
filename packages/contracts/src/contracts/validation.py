"""JSON Schema validation for payloads."""

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft7Validator

    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False


_SCHEMA_DIR = Path(__file__).parent / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    """Load JSON schema by name (e.g. 'depth_quote')."""
    schema_path = _SCHEMA_DIR / f"{name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path) as f:
        return json.load(f)  # type: ignore[no-any-return]


def validate(payload: dict[str, Any], schema_name: str) -> None:
    """
    Validate payload against JSON schema.

    Args:
        payload: Payload dict to validate
        schema_name: Schema name (e.g. 'depth_quote', 'quote_snapshot')

    Raises:
        ImportError: if jsonschema is not installed
        jsonschema.ValidationError: if validation fails
    """
    if not _JSONSCHEMA_AVAILABLE:
        raise ImportError("jsonschema is required for validation; install it separately")

    schema = load_schema(schema_name)
    validator = Draft7Validator(schema)
    validator.validate(payload)

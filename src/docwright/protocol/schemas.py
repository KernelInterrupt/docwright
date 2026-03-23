"""Transport-neutral serialization helpers for protocol schemas."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any


def serialize_schema(value: Any) -> Any:
    """Recursively convert protocol/schema objects into transport-safe data."""

    if hasattr(value, "as_protocol_event") and callable(value.as_protocol_event):
        return serialize_schema(value.as_protocol_event())
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return serialize_schema(value.as_dict())
    if value.__class__.__name__ == "EventName" and hasattr(value, "family") and hasattr(value, "action"):
        return str(value)
    if is_dataclass(value):
        return {field.name: serialize_schema(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [serialize_schema(item) for item in value]
    if isinstance(value, list):
        return [serialize_schema(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_schema(item) for key, item in value.items()}
    return value

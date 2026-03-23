"""Transport-neutral protocol event primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from docwright._compat import StrEnum
from typing import Any


class EventFamily(StrEnum):
    """Top-level event namespaces shared across transports."""

    RUNTIME = "runtime"
    NODE = "node"
    HIGHLIGHT = "highlight"
    WARNING = "warning"
    WORKSPACE = "workspace"
    GUARDRAIL = "guardrail"


@dataclass(slots=True, frozen=True)
class EventName:
    """Structured event name that serializes as ``family.action``."""

    family: EventFamily
    action: str

    def __str__(self) -> str:
        return f"{self.family.value}.{self.action}"


@dataclass(slots=True, frozen=True)
class RunEventSchema:
    """Transport schema for run-scoped event payloads."""

    run_id: str
    document_id: str
    adapter_name: str | None = None
    capability_name: str | None = None


@dataclass(slots=True, frozen=True)
class SessionEventSchema:
    """Transport schema for session-scoped event payloads."""

    run_id: str
    session_id: str
    document_id: str
    status: str
    step_index: int | None = None
    node_id: str | None = None
    workspace_id: str | None = None


@dataclass(slots=True)
class ProtocolEvent:
    """Transport-neutral event record.

    Later checklist items can layer richer runtime/session semantics on top of
    this base envelope without changing the protocol module boundary.
    """

    event_id: str
    name: EventName | str
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_name(self) -> str:
        return str(self.name)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "event_id": self.event_id,
            "name": self.event_name,
            "payload": dict(self.payload),
            "correlation_id": self.correlation_id,
            "occurred_at": self.occurred_at.isoformat(),
        }

"""Core runtime event envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from docwright.protocol.events import EventName, ProtocolEvent


@dataclass(slots=True, frozen=True)
class RuntimeEventContext:
    """Core-owned context attached to runtime events."""

    run_id: str
    session_id: str
    step_index: int | None = None
    node_id: str | None = None
    workspace_id: str | None = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "session_id": self.session_id,
        }
        if self.step_index is not None:
            payload["step_index"] = self.step_index
        if self.node_id is not None:
            payload["node_id"] = self.node_id
        if self.workspace_id is not None:
            payload["workspace_id"] = self.workspace_id
        return payload


@dataclass(slots=True)
class RuntimeEventEnvelope:
    """Core event with runtime context and transport-neutral serialization."""

    name: EventName | str
    context: RuntimeEventContext
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt-{uuid4()}")

    def as_protocol_event(self) -> ProtocolEvent:
        merged_payload = self.context.as_payload()
        merged_payload.update(self.payload)
        return ProtocolEvent(
            event_id=self.event_id,
            name=self.name,
            correlation_id=self.context.run_id,
            payload=merged_payload,
        )

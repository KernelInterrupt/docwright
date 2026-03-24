"""Minimal render protocol for externally visible agent actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RenderToolCallStatus = Literal["completed", "failed"]


@dataclass(slots=True, frozen=True)
class RenderToolCall:
    """One externally visible tool call performed by an agent."""

    sequence: int
    call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    status: RenderToolCallStatus = "completed"
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


@dataclass(slots=True, frozen=True)
class RenderTrace:
    """Transport-neutral render payload containing agent tool-call actions."""

    adapter: str
    session_id: str
    run_id: str
    operations: tuple[RenderToolCall, ...] = ()

"""Shared types for the Codex-compatible adapter bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class CodexToolSpec:
    """A transport-neutral tool definition exposed to Codex-like runtimes."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(slots=True, frozen=True)
class CodexToolCall:
    """A tool invocation produced by an external Codex runtime."""

    call_id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CodexToolResult:
    """A structured result returned after executing a DocWright tool call."""

    call_id: str
    name: str
    output: dict[str, Any]


@dataclass(slots=True, frozen=True)
class CodexMessage:
    """A transport-neutral conversational item for Codex-facing harnesses."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(slots=True, frozen=True)
class CodexRuntimeContract:
    """The DocWright state snapshot exported to a Codex host for one step."""

    instructions: str
    turn_prompt: str
    tools: tuple[CodexToolSpec, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CodexTurnRequest:
    """A generic turn request used by optional in-process Codex harnesses."""

    contract: CodexRuntimeContract
    input_items: tuple[CodexMessage | CodexToolResult, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CodexTurnResponse:
    """A generic turn response carrying tool calls and optional text output."""

    tool_calls: tuple[CodexToolCall, ...] = ()
    output_text: str = ""
    stop_reason: str | None = None
    raw: Any | None = None


BridgeEventKind = Literal[
    "step_exported",
    "tool_call_started",
    "tool_call_completed",
    "tool_call_failed",
    "runtime_events_emitted",
    "output_delta",
    "output_recorded",
]


@dataclass(slots=True, frozen=True)
class CodexBridgeEvent:
    """Observer event emitted by the Codex bridge for external runtimes."""

    kind: BridgeEventKind
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CodexTraceRecord:
    """Structured trace record emitted by the adapter for diagnostics."""

    sequence: int
    kind: BridgeEventKind
    adapter_name: str
    session_id: str | None = None
    run_id: str | None = None
    step_index: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CodexUsageSnapshot:
    """Adapter-local usage counters for Codex bridge activity."""

    step_exports: int = 0
    tool_calls_started: int = 0
    tool_calls_completed: int = 0
    tool_call_failures: int = 0
    runtime_event_batches: int = 0
    runtime_events_emitted: int = 0
    output_deltas: int = 0
    output_delta_chars: int = 0
    outputs_recorded: int = 0
    output_chars_recorded: int = 0


@runtime_checkable
class CodexBridgeObserver(Protocol):
    """Observer hook for external runtimes integrating with the Codex bridge."""

    def on_bridge_event(self, event: CodexBridgeEvent) -> None:
        """Receive a bridge lifecycle event."""


@runtime_checkable
class CodexTraceSink(Protocol):
    """Trace sink hook for adapter-local diagnostics and usage analysis."""

    def record_trace(self, record: CodexTraceRecord) -> None:
        """Receive a structured trace record from the bridge."""


@runtime_checkable
class CodexTurnDriver(Protocol):
    """Optional in-process bridge harness for tests or local runners.

    DocWright's Codex adapter is primarily a tool surface that Codex calls into.
    This protocol exists only for smoke tests and local harnesses that want to
    drive the bridge from inside Python without tying the adapter to any one SDK
    or transport.
    """

    async def next_turn(self, request: CodexTurnRequest) -> CodexTurnResponse:
        """Return the next Codex-side turn for the exported DocWright contract."""

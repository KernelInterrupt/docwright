"""Codex-compatible bridge for DocWright Core.

This adapter exposes DocWright runtime state and tool execution in a shape that
Codex-like runtimes can call into. It does not make OpenAI or SDK assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docwright.adapters.agent.base import AdapterDescriptor
from docwright.adapters.agent.codex_prompting import CodexPromptAssembler, load_agents_md
from docwright.adapters.agent.codex_tools import CodexToolRegistry
from docwright.adapters.agent.codex_types import (
    BridgeEventKind,
    CodexBridgeEvent,
    CodexBridgeObserver,
    CodexMessage,
    CodexRuntimeContract,
    CodexToolCall,
    CodexToolResult,
    CodexTraceRecord,
    CodexTraceSink,
    CodexTurnDriver,
    CodexTurnRequest,
    CodexTurnResponse,
    CodexUsageSnapshot,
)
from docwright.protocol.schemas import serialize_schema

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession


@dataclass(slots=True)
class CodexAdapter:
    """Codex-facing tool bridge for DocWright Core.

    Primary responsibilities:
    - export step-scoped instructions and runtime context for a Codex host
    - publish tool schemas derived from the active capability/skills
    - execute Codex-originated tool calls against DocWright Core
    - optionally provide an in-process driver loop for smoke tests
    - emit observer hooks for external runtime streaming/observability needs
    - emit tracing and usage metrics for adapter-local diagnostics
    """

    prompt_assembler: CodexPromptAssembler = field(default_factory=CodexPromptAssembler)
    tool_registry: CodexToolRegistry = field(default_factory=CodexToolRegistry)
    agents_md_path: Path | None = None
    driver: CodexTurnDriver | None = None
    observers: tuple[CodexBridgeObserver, ...] = ()
    trace_sinks: tuple[CodexTraceSink, ...] = ()
    max_iterations_per_step: int = 12
    descriptor: AdapterDescriptor = field(
        default_factory=lambda: AdapterDescriptor(
            name="codex",
            transport="tool_bridge",
            metadata={"tool_mode": "function_calling", "integration": "codex_compatible"},
        )
    )
    _usage: dict[str, int] = field(
        default_factory=lambda: {
            "step_exports": 0,
            "tool_calls_started": 0,
            "tool_calls_completed": 0,
            "tool_call_failures": 0,
            "runtime_event_batches": 0,
            "runtime_events_emitted": 0,
            "output_deltas": 0,
            "output_delta_chars": 0,
            "outputs_recorded": 0,
            "output_chars_recorded": 0,
        },
        init=False,
        repr=False,
    )
    _trace_sequence: int = field(default=0, init=False, repr=False)

    def describe_step(
        self,
        session: RuntimeSession,
        capability: CapabilityProfile | None = None,
    ) -> CodexRuntimeContract:
        """Export the Codex-callable contract for the current DocWright step."""

        agents_md_text = load_agents_md(self.agents_md_path)
        contract = CodexRuntimeContract(
            instructions=self.prompt_assembler.build_instructions(
                session,
                capability,
                agents_md_text=agents_md_text,
            ),
            turn_prompt=self.prompt_assembler.build_turn_prompt(session),
            tools=self.tool_registry.tools_for(session, capability),
            metadata={
                "session_id": session.model.session_id,
                "run_id": session.model.run_id,
                "document_id": session.model.document_id,
                "current_node_id": None if session.model.step is None else session.model.step.node_id,
                "capability": None if capability is None else capability.descriptor.name,
                "adapter": self.descriptor.name,
                "workspace_registry_ready": session.workspace_registry_ready(),
                "workspace_compile_ready": session.workspace_compile_ready(),
                "workspace_compiler": session.workspace_compiler_info(),
            },
        )
        self._bump_usage("step_exports")
        self._emit_signal("step_exported", {"contract": serialize_schema(contract)}, session=session)
        return contract

    def execute_tool_call(
        self,
        *,
        session: RuntimeSession,
        capability: CapabilityProfile | None,
        call: CodexToolCall,
    ) -> CodexToolResult:
        """Execute one Codex-originated tool call against DocWright Core."""

        before_events = len(session.events())
        serialized_call = serialize_schema(call)
        self._bump_usage("tool_calls_started")
        self._emit_signal("tool_call_started", {"call": serialized_call}, session=session)

        try:
            result = self.tool_registry.execute_tool(session=session, capability=capability, call=call)
        except Exception as exc:
            self._bump_usage("tool_call_failures")
            self._emit_signal(
                "tool_call_failed",
                {
                    "call": serialized_call,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                },
                session=session,
            )
            self._emit_runtime_events(session, before_events)
            raise

        self._bump_usage("tool_calls_completed")
        self._emit_signal(
            "tool_call_completed",
            {
                "call": serialized_call,
                "result": serialize_schema(result),
            },
            session=session,
        )
        self._emit_runtime_events(session, before_events)
        return result

    def execute_tool_calls(
        self,
        *,
        session: RuntimeSession,
        capability: CapabilityProfile | None,
        calls: tuple[CodexToolCall, ...],
    ) -> tuple[CodexToolResult, ...]:
        """Execute a batch of Codex-originated tool calls in order."""

        return tuple(
            self.execute_tool_call(session=session, capability=capability, call=call)
            for call in calls
        )

    def stream_output_delta(
        self,
        *,
        session: RuntimeSession | None = None,
        text_delta: str = "",
        raw: object | None = None,
    ) -> None:
        """Emit a non-persistent streaming output hook for external runtimes."""

        if not text_delta and raw is None:
            return
        self._bump_usage("output_deltas")
        self._bump_usage("output_delta_chars", amount=len(text_delta))
        self._emit_signal(
            "output_delta",
            {
                "text_delta": text_delta,
                "raw": raw,
            },
            session=session,
        )

    def record_output(
        self,
        session: RuntimeSession,
        *,
        output_text: str = "",
        stop_reason: str | None = None,
        raw: object | None = None,
    ) -> None:
        """Record Codex-side output as an adapter event for observability."""

        if not output_text and stop_reason is None and raw is None:
            return

        before_events = len(session.events())
        self._bump_usage("outputs_recorded")
        self._bump_usage("output_chars_recorded", amount=len(output_text))
        self._emit_signal(
            "output_recorded",
            {
                "output_text": output_text,
                "stop_reason": stop_reason,
                "raw": raw,
            },
            session=session,
        )
        session.emit_event(
            "adapter.codex_output",
            {
                "output_text": output_text,
                "stop_reason": stop_reason,
                "raw": raw,
            },
        )
        self._emit_runtime_events(session, before_events)

    def usage_snapshot(self) -> CodexUsageSnapshot:
        """Return a snapshot of adapter-local usage counters."""

        return CodexUsageSnapshot(**self._usage)

    async def run_step(self, session: RuntimeSession, capability: CapabilityProfile | None = None) -> None:
        """Run one step through an optional in-process Codex driver.

        This is a convenience harness for local smoke tests and headless runners.
        In production integrations, an external Codex runtime can instead call
        ``describe_step`` and ``execute_tool_call`` directly.
        """

        if self.driver is None:
            raise RuntimeError(
                "CodexAdapter is a bridge surface. Configure a CodexTurnDriver only "
                "for in-process smoke runs, or call describe_step/execute_tool_call directly."
            )

        contract = self.describe_step(session, capability)
        transcript: list[CodexMessage | CodexToolResult] = [
            CodexMessage(role="user", content=contract.turn_prompt)
        ]

        for iteration in range(self.max_iterations_per_step):
            response = await self.driver.next_turn(
                CodexTurnRequest(
                    contract=contract,
                    input_items=tuple(transcript),
                    metadata={
                        **contract.metadata,
                        "iteration": iteration,
                    },
                )
            )
            self._append_response_to_transcript(transcript, response)
            self.record_output(
                session,
                output_text=response.output_text,
                stop_reason=response.stop_reason,
                raw=response.raw,
            )

            if not response.tool_calls:
                return

            tool_results = self.execute_tool_calls(
                session=session,
                capability=capability,
                calls=response.tool_calls,
            )
            transcript.extend(tool_results)

            if session.model.status.value in {"completed", "failed"}:
                return

        raise RuntimeError("Codex adapter exceeded max_iterations_per_step before step completion")

    def _append_response_to_transcript(
        self,
        transcript: list[CodexMessage | CodexToolResult],
        response: CodexTurnResponse,
    ) -> None:
        if response.output_text:
            transcript.append(CodexMessage(role="assistant", content=response.output_text))

    def _emit_runtime_events(self, session: RuntimeSession, before_events: int) -> None:
        new_events = session.events()[before_events:]
        if not new_events:
            return
        self._bump_usage("runtime_event_batches")
        self._bump_usage("runtime_events_emitted", amount=len(new_events))
        self._emit_signal(
            "runtime_events_emitted",
            {"events": serialize_schema(new_events)},
            session=session,
        )

    def _emit_signal(
        self,
        kind: BridgeEventKind,
        payload: dict[str, Any],
        *,
        session: RuntimeSession | None,
    ) -> None:
        self._notify_observers(kind, payload)
        self._record_trace(kind, payload, session=session)

    def _notify_observers(self, kind: BridgeEventKind, payload: dict[str, Any]) -> None:
        if not self.observers:
            return
        event = CodexBridgeEvent(kind=kind, payload=payload)
        for observer in self.observers:
            observer.on_bridge_event(event)

    def _record_trace(
        self,
        kind: BridgeEventKind,
        payload: dict[str, Any],
        *,
        session: RuntimeSession | None,
    ) -> None:
        if not self.trace_sinks:
            return
        self._trace_sequence += 1
        record = CodexTraceRecord(
            sequence=self._trace_sequence,
            kind=kind,
            adapter_name=self.descriptor.name,
            session_id=None if session is None else session.model.session_id,
            run_id=None if session is None else session.model.run_id,
            step_index=None if session is None else session.model.step.index,
            payload=payload,
        )
        for sink in self.trace_sinks:
            sink.record_trace(record)

    def _bump_usage(self, key: str, *, amount: int = 1) -> None:
        self._usage[key] += amount

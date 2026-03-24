"""Generic host-facing bridge for direct DocWright runtime control.

This module exposes a small transport-layer bridge that lets an external host
hold a live DocWright session, export the current step contract, execute
structured tool calls, inspect usage counters, and retrieve a minimal render
trace of visible tool activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from docwright.adapters.agent.codex import CodexAdapter
from docwright.adapters.agent.codex_types import (
    CodexRuntimeContract,
    CodexToolCall,
    CodexToolResult,
    CodexUsageSnapshot,
)
from docwright.protocol.render import RenderToolCall, RenderTrace

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession


@dataclass(slots=True)
class RuntimeHostBridge:
    """Host-facing bridge around one live runtime session.

    The bridge is host-generic: Codex is the first consumer, but the same
    surface can also back human-facing CLIs, debug shells, replay tooling, or
    other runtimes that want to operate DocWright through exported step
    contracts plus structured tool calls.
    """

    session: RuntimeSession
    capability: CapabilityProfile | None = None
    adapter: CodexAdapter = field(default_factory=CodexAdapter)
    _render_operations: list[RenderToolCall] = field(default_factory=list, init=False, repr=False)

    def export_step(self) -> CodexRuntimeContract:
        """Return the current step contract for the external host."""

        return self.adapter.describe_step(self.session, self.capability)

    def execute_tool_call(self, call: CodexToolCall) -> CodexToolResult:
        """Execute one structured tool call against the live DocWright session."""

        try:
            result = self.adapter.execute_tool_call(
                session=self.session,
                capability=self.capability,
                call=call,
            )
        except Exception as exc:
            self._record_render_failure(call, exc)
            raise
        self._record_render_success(call, result)
        return result

    def execute_tool_calls(self, calls: tuple[CodexToolCall, ...]) -> tuple[CodexToolResult, ...]:
        """Execute multiple structured tool calls against the live DocWright session."""

        return tuple(self.execute_tool_call(call) for call in calls)

    def stream_output_delta(self, *, text_delta: str = '', raw: object | None = None) -> None:
        """Forward a streaming output delta to bridge observers and trace sinks."""

        self.adapter.stream_output_delta(session=self.session, text_delta=text_delta, raw=raw)

    def record_output(
        self,
        *,
        output_text: str = '',
        stop_reason: str | None = None,
        raw: object | None = None,
    ) -> None:
        """Record host-side text or metadata as adapter output on the session."""

        self.adapter.record_output(
            self.session,
            output_text=output_text,
            stop_reason=stop_reason,
            raw=raw,
        )

    def render_operations(self) -> tuple[RenderToolCall, ...]:
        """Return externally visible agent actions as a minimal render log."""

        return tuple(self._render_operations)

    def render_trace(self) -> RenderTrace:
        """Return a transport-neutral render payload for external consumers."""

        return RenderTrace(
            adapter=self.adapter.descriptor.name,
            session_id=self.session.model.session_id,
            run_id=self.session.model.run_id,
            operations=self.render_operations(),
        )

    def _record_render_success(self, call: CodexToolCall, result: CodexToolResult) -> None:
        self._render_operations.append(
            RenderToolCall(
                sequence=len(self._render_operations) + 1,
                call_id=call.call_id,
                tool_name=call.name,
                arguments=dict(call.arguments),
                status='completed',
                output=result.output,
            )
        )

    def _record_render_failure(self, call: CodexToolCall, exc: Exception) -> None:
        self._render_operations.append(
            RenderToolCall(
                sequence=len(self._render_operations) + 1,
                call_id=call.call_id,
                tool_name=call.name,
                arguments=dict(call.arguments),
                status='failed',
                error={'type': type(exc).__name__, 'message': str(exc)},
            )
        )

    def usage_snapshot(self) -> CodexUsageSnapshot:
        """Return adapter-local usage counters for this bridge instance."""

        return self.adapter.usage_snapshot()

    def available_tool_names(self) -> tuple[str, ...]:
        """Return the current tool names exported for the active capability."""

        return tuple(tool.name for tool in self.export_step().tools)

    def is_terminal(self) -> bool:
        """Return whether the underlying DocWright runtime session is terminal."""

        return self.session.model.status.value in {'completed', 'failed'}


__all__ = ['RuntimeHostBridge']

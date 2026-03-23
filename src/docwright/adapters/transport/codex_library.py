"""Direct-library host helper for Codex-compatible DocWright integrations.

This module keeps the integration Playwright-like: an external Codex host can
hold a live DocWright session object, export the current step contract, execute
structured tool calls, stream output deltas to hooks, inspect usage counters,
and feed final model output back for observability.
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

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession


@dataclass(slots=True)
class CodexLibraryBridge:
    """Small host-facing bridge for direct-library Codex integrations.

    A Codex host can keep one bridge per live DocWright runtime session and call
    these methods directly, without introducing MCP or provider-specific client
    code into Core.
    """

    session: RuntimeSession
    capability: CapabilityProfile | None = None
    adapter: CodexAdapter = field(default_factory=CodexAdapter)

    def export_step(self) -> CodexRuntimeContract:
        """Return the current step contract for the external Codex host."""

        return self.adapter.describe_step(self.session, self.capability)

    def execute_tool_call(self, call: CodexToolCall) -> CodexToolResult:
        """Execute one Codex tool call against the live DocWright session."""

        return self.adapter.execute_tool_call(
            session=self.session,
            capability=self.capability,
            call=call,
        )

    def execute_tool_calls(self, calls: tuple[CodexToolCall, ...]) -> tuple[CodexToolResult, ...]:
        """Execute multiple Codex tool calls against the live DocWright session."""

        return self.adapter.execute_tool_calls(
            session=self.session,
            capability=self.capability,
            calls=calls,
        )

    def stream_output_delta(self, *, text_delta: str = "", raw: object | None = None) -> None:
        """Forward a streaming output delta to bridge observers and trace sinks."""

        self.adapter.stream_output_delta(session=self.session, text_delta=text_delta, raw=raw)

    def record_output(
        self,
        *,
        output_text: str = "",
        stop_reason: str | None = None,
        raw: object | None = None,
    ) -> None:
        """Record Codex-side text or metadata as adapter output on the session."""

        self.adapter.record_output(
            self.session,
            output_text=output_text,
            stop_reason=stop_reason,
            raw=raw,
        )

    def usage_snapshot(self) -> CodexUsageSnapshot:
        """Return adapter-local usage counters for this bridge instance."""

        return self.adapter.usage_snapshot()

    def available_tool_names(self) -> tuple[str, ...]:
        """Return the current tool names exported for the active capability."""

        return tuple(tool.name for tool in self.export_step().tools)

    def is_terminal(self) -> bool:
        """Return whether the underlying DocWright runtime session is terminal."""

        return self.session.model.status.value in {"completed", "failed"}

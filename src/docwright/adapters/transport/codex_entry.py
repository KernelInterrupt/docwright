"""Launch-oriented Codex entry helper for DocWright.

This module is the ergonomic setup surface for hosts that want to connect Codex
(or another Codex-like runtime) to DocWright with minimal boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from docwright.adapters.agent.codex import CodexAdapter
from docwright.adapters.agent.codex_types import (
    CodexRuntimeContract,
    CodexToolCall,
    CodexToolResult,
    CodexUsageSnapshot,
)
from docwright.adapters.transport.codex_library import CodexLibraryBridge
from docwright.core.guardrails import RuntimeGuardrailPolicy, RuntimePermissions
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.document.interfaces import DocumentHandle
    from docwright.workspace.compiler import WorkspaceCompiler


@dataclass(slots=True)
class DocWrightCodexEntry:
    """Minimal setup wrapper for launching Codex against a DocWright session."""

    session: RuntimeSession
    bridge: CodexLibraryBridge
    capability: CapabilityProfile | None = None

    @classmethod
    def from_document(
        cls,
        document: DocumentHandle,
        *,
        capability: CapabilityProfile | None = None,
        session_id: str = "session-1",
        run_id: str = "run-1",
        permissions: RuntimePermissions | None = None,
        guardrail_policy: RuntimeGuardrailPolicy | None = None,
        workspace_compiler: WorkspaceCompiler | None = None,
        adapter: CodexAdapter | None = None,
    ) -> "DocWrightCodexEntry":
        """Construct a runtime session + bridge pair from a document handle."""

        resolved_adapter = adapter or CodexAdapter()
        resolved_capability_name = None if capability is None else capability.descriptor.name
        resolved_guardrail_policy = (
            guardrail_policy if guardrail_policy is not None else None if capability is None else capability.guardrail_policy()
        )
        session = RuntimeSession(
            RuntimeSessionModel(
                session_id=session_id,
                run_id=run_id,
                document_id=document.document_id,
                capability_name=resolved_capability_name,
                adapter_name=resolved_adapter.descriptor.name,
            ),
            document=document,
            permissions=permissions,
            guardrail_policy=resolved_guardrail_policy,
            workspace_compiler=workspace_compiler,
        )
        bridge = CodexLibraryBridge(
            session=session,
            capability=capability,
            adapter=resolved_adapter,
        )
        return cls(session=session, bridge=bridge, capability=capability)

    def export_step(self) -> CodexRuntimeContract:
        return self.bridge.export_step()

    def execute_tool_call(self, call: CodexToolCall) -> CodexToolResult:
        return self.bridge.execute_tool_call(call)

    def execute_tool_calls(self, calls: tuple[CodexToolCall, ...]) -> tuple[CodexToolResult, ...]:
        return self.bridge.execute_tool_calls(calls)

    def stream_output_delta(self, *, text_delta: str = "", raw: object | None = None) -> None:
        self.bridge.stream_output_delta(text_delta=text_delta, raw=raw)

    def record_output(
        self,
        *,
        output_text: str = "",
        stop_reason: str | None = None,
        raw: object | None = None,
    ) -> None:
        self.bridge.record_output(output_text=output_text, stop_reason=stop_reason, raw=raw)

    def usage_snapshot(self) -> CodexUsageSnapshot:
        return self.bridge.usage_snapshot()

    def is_terminal(self) -> bool:
        return self.bridge.is_terminal()

"""Launch-oriented Codex entry helper for DocWright.

This module is the ergonomic setup surface for hosts that want to connect Codex
(or another Codex-like runtime) to DocWright with minimal boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from docwright.adapters.agent.codex import CodexAdapter
from docwright.adapters.agent.codex_types import (
    CodexRuntimeContract,
    CodexToolCall,
    CodexToolResult,
    CodexUsageSnapshot,
)
from docwright.adapters.transport.codex_host import CodexHostBridge
from docwright.core.guardrails import RuntimeGuardrailPolicy, RuntimePermissions
from docwright.document import in_memory_document_from_ir, ir_converter
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.workspace.builtins import (
    build_default_latex_workspace_compiler,
    build_default_workspace_registry,
    select_default_latex_compiler_profile,
    select_default_workspace_sandbox_profile,
)

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.document.interfaces import DocumentHandle
    from docwright.workspace.compiler import WorkspaceCompiler
    from docwright.workspace.registry import WorkspaceProfileRegistry


@dataclass(slots=True)
class DocWrightCodexEntry:
    """Minimal setup wrapper for launching Codex against a DocWright session."""

    session: RuntimeSession
    bridge: CodexHostBridge
    capability: CapabilityProfile | None = None

    @classmethod
    def from_pdf(
        cls,
        pdf_path: str,
        *,
        goal: str | None = None,
        document_backend_kwargs: dict[str, Any] | None = None,
        capability: CapabilityProfile | None = None,
        session_id: str = "session-1",
        run_id: str = "run-1",
        permissions: RuntimePermissions | None = None,
        guardrail_policy: RuntimeGuardrailPolicy | None = None,
        workspace_compiler: WorkspaceCompiler | None = None,
        workspace_registry: WorkspaceProfileRegistry | None = None,
        adapter: CodexAdapter | None = None,
    ) -> "DocWrightCodexEntry":
        """Construct a runtime entry directly from a PDF path via the optional document backend."""

        converter_kwargs: dict[str, Any] = dict(document_backend_kwargs or {})
        if goal is not None:
            converter_kwargs.setdefault("goal", goal)
        ir_payload = ir_converter(pdf_path, **converter_kwargs)
        document = in_memory_document_from_ir(ir_payload)
        return cls.from_document(
            document,
            capability=capability,
            session_id=session_id,
            run_id=run_id,
            permissions=permissions,
            guardrail_policy=guardrail_policy,
            workspace_compiler=workspace_compiler,
            workspace_registry=workspace_registry,
            adapter=adapter,
        )

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
        workspace_registry: WorkspaceProfileRegistry | None = None,
        adapter: CodexAdapter | None = None,
    ) -> "DocWrightCodexEntry":
        """Construct a runtime session + bridge pair from a document handle."""

        resolved_adapter = adapter or CodexAdapter()
        resolved_capability_name = None if capability is None else capability.descriptor.name
        resolved_guardrail_policy = (
            guardrail_policy if guardrail_policy is not None else None if capability is None else capability.guardrail_policy()
        )
        resolved_workspace_registry = workspace_registry
        resolved_workspace_compiler = workspace_compiler

        if resolved_workspace_registry is None and resolved_workspace_compiler is None:
            default_profile = select_default_latex_compiler_profile()
            default_sandbox = None if default_profile is None else select_default_workspace_sandbox_profile()
            resolved_workspace_registry = build_default_workspace_registry(
                compiler_profile=default_profile,
                sandbox_profile=default_sandbox,
            )
            if default_profile is not None:
                resolved_workspace_compiler = build_default_latex_workspace_compiler(profile=default_profile)
        elif resolved_workspace_registry is None and resolved_workspace_compiler is not None:
            compiler_info = getattr(resolved_workspace_compiler, "describe", None)
            profile = None
            sandbox_profile = None
            if callable(compiler_info):
                described = compiler_info()
                if hasattr(described, "profile"):
                    profile = described.profile
                    sandbox_profile = described.sandbox_backend
                elif isinstance(described, dict):
                    profile = described.get("profile")
                    sandbox_profile = described.get("sandbox_backend")
            resolved_workspace_registry = build_default_workspace_registry(
                compiler_profile=profile,
                sandbox_profile=sandbox_profile,
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
            workspace_compiler=resolved_workspace_compiler,
            workspace_registry=resolved_workspace_registry,
        )
        bridge = CodexHostBridge(
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

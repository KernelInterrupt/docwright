"""Core runtime session object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from docwright.core.events import RuntimeEventContext, RuntimeEventEnvelope
from docwright.core.guardrails import (
    GuardrailCode,
    GuardrailViolation,
    GuardrailViolationError,
    RuntimeGuardrailPolicy,
    RuntimePermissions,
)
from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus
from docwright.document.interfaces import DocumentHandle, NodeContextSlice, NodeRelationRef
from docwright.protocol.events import EventFamily, EventName
from docwright.workspace.compiler import WorkspaceCompiler
from docwright.workspace.models import EditableRegion, WorkspaceSessionModel
from docwright.workspace.registry import WorkspaceProfileRegistry
from docwright.workspace.session import WorkspaceSession


@dataclass(slots=True)
class RuntimeNodeView:
    """Session-aware runtime node wrapper.

    It preserves document query behavior while exposing Core-owned actions on the
    current runtime step.
    """

    session: RuntimeSession
    raw_node: object

    @property
    def node_id(self) -> str:
        return getattr(self.raw_node, "node_id")

    @property
    def kind(self) -> str:
        return getattr(self.raw_node, "kind")

    @property
    def page_number(self) -> int:
        return getattr(self.raw_node, "page_number")

    def text_content(self) -> str | None:
        text_getter = getattr(self.raw_node, "text_content", None)
        return text_getter() if callable(text_getter) else None

    def relations(self) -> tuple[NodeRelationRef, ...]:
        relation_getter = getattr(self.raw_node, "relations", None)
        if callable(relation_getter):
            return tuple(relation_getter())
        return ()

    def highlight(self, *, level: str, reason: str | None = None) -> RuntimeEventEnvelope:
        return self.session.record_highlight(level=level, reason=reason)

    def warning(
        self,
        *,
        kind: str,
        severity: str,
        message: str,
        evidence: tuple[str, ...] = (),
    ) -> RuntimeEventEnvelope:
        return self.session.record_warning(
            kind=kind,
            severity=severity,
            message=message,
            evidence=evidence,
        )

    def open_workspace(
        self,
        *,
        task: str,
        capability: str | None = None,
        language: str | None = None,
        initial_body: str | None = None,
        editable_region: EditableRegion | None = None,
        compiler: WorkspaceCompiler | None = None,
        workspace_profile: str | None = None,
        template_id: str | None = None,
        body_kind: str | None = None,
        compiler_profile: str | None = None,
    ) -> WorkspaceSession:
        return self.session.open_workspace(
            task=task,
            capability=capability,
            language=language,
            initial_body=initial_body,
            editable_region=editable_region,
            compiler=compiler,
            workspace_profile=workspace_profile,
            template_id=template_id,
            body_kind=body_kind,
            compiler_profile=compiler_profile,
        )


class RuntimeSession:
    """Core-owned runtime session."""

    def __init__(
        self,
        model: RuntimeSessionModel,
        *,
        document: DocumentHandle,
        permissions: RuntimePermissions | None = None,
        guardrail_policy: RuntimeGuardrailPolicy | None = None,
        workspace_compiler: WorkspaceCompiler | None = None,
        workspace_registry: WorkspaceProfileRegistry | None = None,
    ):
        self._model = model
        self._document = document
        self._permissions = permissions or RuntimePermissions()
        self._guardrail_policy = guardrail_policy or RuntimeGuardrailPolicy()
        self._workspace_compiler = workspace_compiler
        self._workspace_registry = workspace_registry
        self._events: list[RuntimeEventEnvelope] = []
        self._workspaces: dict[str, WorkspaceSession] = {}

        self._model.status = RuntimeSessionStatus.ACTIVE
        self._initialize_step()
        self._model.touch()
        self.emit_event(EventName(EventFamily.RUNTIME, "started"))
        if self._model.step.node_id is not None:
            self.emit_event(EventName(EventFamily.NODE, "entered"))

    @property
    def model(self) -> RuntimeSessionModel:
        return self._model

    @property
    def document(self) -> DocumentHandle:
        return self._document

    @property
    def permissions(self) -> RuntimePermissions:
        return self._permissions

    @property
    def guardrail_policy(self) -> RuntimeGuardrailPolicy:
        return self._guardrail_policy

    @property
    def workspace_registry(self) -> WorkspaceProfileRegistry | None:
        return self._workspace_registry

    def events(self) -> tuple[RuntimeEventEnvelope, ...]:
        return tuple(self._events)

    def workspaces(self) -> tuple[WorkspaceSession, ...]:
        return tuple(self._workspaces.values())

    def emit_event(
        self,
        name: EventName | str,
        payload: dict[str, Any] | None = None,
        *,
        workspace_id: str | None = None,
    ) -> RuntimeEventEnvelope:
        envelope = RuntimeEventEnvelope(
            name=name,
            context=RuntimeEventContext(
                run_id=self._model.run_id,
                session_id=self._model.session_id,
                step_index=self._model.step.index,
                node_id=self._model.step.node_id,
                workspace_id=workspace_id,
            ),
            payload=payload or {},
        )
        self._events.append(envelope)
        self._model.touch()
        return envelope

    def current_node(self) -> RuntimeNodeView | None:
        node_id = self._model.step.node_id
        if node_id is None:
            return None
        return RuntimeNodeView(session=self, raw_node=self._get_node(node_id))

    def get_context(self, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        node_id = self._model.step.node_id
        if node_id is None:
            return NodeContextSlice(focus_node_id="", before_node_ids=(), after_node_ids=())

        get_context = getattr(self._document, "get_context", None)
        if callable(get_context):
            return get_context(node_id, before=before, after=after)

        reading_order = self._get_reading_order()
        index = reading_order.index(node_id)
        return NodeContextSlice(
            focus_node_id=node_id,
            before_node_ids=tuple(reading_order[max(0, index - before) : index]),
            after_node_ids=tuple(reading_order[index + 1 : index + 1 + after]),
        )

    def record_highlight(self, *, level: str, reason: str | None = None) -> RuntimeEventEnvelope:
        self._permissions.ensure_allowed("highlight")
        self._model.step.highlight_count += 1
        payload: dict[str, Any] = {"level": level}
        if reason is not None:
            payload["reason"] = reason
        return self.emit_event(EventName(EventFamily.HIGHLIGHT, "applied"), payload)

    def record_warning(
        self,
        *,
        kind: str,
        severity: str,
        message: str,
        evidence: tuple[str, ...] = (),
    ) -> RuntimeEventEnvelope:
        self._permissions.ensure_allowed("warning")
        self._model.step.warning_count += 1
        return self.emit_event(
            EventName(EventFamily.WARNING, "raised"),
            {
                "kind": kind,
                "severity": severity,
                "message": message,
                "evidence": list(evidence),
            },
        )

    def open_workspace(
        self,
        *,
        task: str,
        capability: str | None = None,
        language: str | None = None,
        initial_body: str | None = None,
        editable_region: EditableRegion | None = None,
        compiler: WorkspaceCompiler | None = None,
        workspace_profile: str | None = None,
        template_id: str | None = None,
        body_kind: str | None = None,
        compiler_profile: str | None = None,
    ) -> WorkspaceSession:
        node = self.current_node()
        resolved_profile = None
        resolved_template = None
        resolved_editable_region = editable_region
        resolved_template_id = template_id
        resolved_body_kind = body_kind
        resolved_compiler_profile = compiler_profile
        compile_required_before_submit = True
        patch_scope = "editable_region_only"
        locked_sections: tuple[str, ...] = ()
        model_summary = ""

        if workspace_profile is not None:
            if self._workspace_registry is None:
                raise ValueError("workspace_profile requires a configured workspace registry")
            resolved_profile = self._workspace_registry.profile(workspace_profile)
            if resolved_profile.task != task:
                raise ValueError(
                    f"workspace profile {workspace_profile!r} requires task {resolved_profile.task!r}, got {task!r}"
                )
            resolved_template = self._workspace_registry.resolve_template_for_profile(
                workspace_profile,
                template_id=template_id,
            )
            resolved_template_id = resolved_template.template_id
            resolved_body_kind = resolved_body_kind or resolved_profile.body_kind or resolved_template.body_kind
            resolved_compiler_profile = (
                resolved_compiler_profile
                or resolved_profile.compiler_profile
                or resolved_template.compiler_profile
            )
            compile_required_before_submit = resolved_profile.compile_required_before_submit
            patch_scope = resolved_profile.patch_scope
            locked_sections = resolved_profile.locked_sections
            model_summary = resolved_profile.model_summary
        elif template_id is not None:
            if self._workspace_registry is None:
                raise ValueError("template_id requires a configured workspace registry")
            resolved_template = self._workspace_registry.template(template_id)
            if resolved_template.task != task:
                raise ValueError(
                    f"workspace template {template_id!r} requires task {resolved_template.task!r}, got {task!r}"
                )
            resolved_template_id = resolved_template.template_id
            resolved_body_kind = resolved_body_kind or resolved_template.body_kind
            resolved_compiler_profile = resolved_compiler_profile or resolved_template.compiler_profile

        if resolved_editable_region is None and resolved_template is not None:
            resolved_editable_region = resolved_template.default_region_spec().as_runtime_region()

        workspace_id = f"ws-{uuid4()}"
        self.record_workspace_opened(workspace_id=workspace_id, task=task)

        workspace = WorkspaceSession(
            WorkspaceSessionModel(
                workspace_id=workspace_id,
                task=task,
                capability_name=capability or self._model.capability_name,
                workspace_profile=workspace_profile,
                template_id=resolved_template_id,
                body_kind=resolved_body_kind,
                compiler_profile=resolved_compiler_profile,
                compile_required_before_submit=compile_required_before_submit,
                patch_scope=patch_scope,
                locked_sections=locked_sections,
                model_summary=model_summary,
                editable_region=resolved_editable_region or EditableRegion(),
                current_body=initial_body if initial_body is not None else (node.text_content() if node else ""),
            ),
            compiler=compiler or self._workspace_compiler,
        )
        self._workspaces[workspace_id] = workspace
        self.emit_event(
            EventName(EventFamily.WORKSPACE, "session_created"),
            {
                "workspace_id": workspace_id,
                "task": task,
                "capability": capability,
                "language": language,
            },
            workspace_id=workspace_id,
        )
        return workspace

    def workspace(self, workspace_id: str) -> WorkspaceSession:
        return self._workspaces[workspace_id]

    def record_workspace_opened(self, *, workspace_id: str, task: str) -> RuntimeEventEnvelope:
        self._permissions.ensure_allowed("open_workspace")
        max_workspaces = self._guardrail_policy.max_workspaces_per_step
        if max_workspaces is not None and self._model.step.workspace_open_count >= max_workspaces:
            raise GuardrailViolationError(
                GuardrailViolation(
                    code=GuardrailCode.WORKSPACE_LIMIT_REACHED,
                    message="workspace-per-step limit reached for the current node",
                    details={
                        "step_index": self._model.step.index,
                        "node_id": self._model.step.node_id,
                        "max_workspaces_per_step": max_workspaces,
                    },
                )
            )

        self._model.step.workspace_open_count += 1
        self._model.step.workspace_opened = True
        return self.emit_event(
            EventName(EventFamily.WORKSPACE, "opened"),
            {"workspace_id": workspace_id, "task": task},
            workspace_id=workspace_id,
        )

    def advance(self) -> RuntimeNodeView | None:
        self._permissions.ensure_allowed("advance")
        if (
            self._guardrail_policy.require_highlight_before_advance
            and self._model.step.highlight_count < 1
        ):
            raise GuardrailViolationError(
                GuardrailViolation(
                    code=GuardrailCode.HIGHLIGHT_REQUIRED_BEFORE_ADVANCE,
                    message="must highlight the current node before advancing",
                    details={
                        "step_index": self._model.step.index,
                        "node_id": self._model.step.node_id,
                    },
                )
            )

        reading_order = self._get_reading_order()
        next_index = self._model.step.index + 1
        if next_index >= len(reading_order):
            self._model.status = RuntimeSessionStatus.COMPLETED
            self.emit_event(EventName(EventFamily.RUNTIME, "completed"))
            return None

        next_node_id = reading_order[next_index]
        self._model.step.enter_node(index=next_index, node_id=next_node_id)
        self.emit_event(EventName(EventFamily.NODE, "entered"))
        return self.current_node()

    def _initialize_step(self) -> None:
        reading_order = self._get_reading_order()
        if reading_order and self._model.step.node_id is None:
            self._model.step.enter_node(index=0, node_id=reading_order[0])

    def _get_reading_order(self) -> tuple[str, ...]:
        reading_order = getattr(self._document, "reading_order", None)
        if callable(reading_order):
            reading_order = reading_order()
        if reading_order is None and hasattr(self._document, "get_reading_order"):
            reading_order = self._document.get_reading_order()
        if reading_order is None:
            return ()
        return tuple(reading_order)

    def _get_node(self, node_id: str) -> object:
        getter = getattr(self._document, "get_node", None)
        if callable(getter):
            return getter(node_id)
        selector = getattr(self._document, "select", None)
        if callable(selector):
            return selector(node_id)
        raise AttributeError("document does not expose get_node/select lookup")

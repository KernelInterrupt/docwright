"""Core runtime session object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
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
from docwright.document.interfaces import (
    DocumentHandle,
    InternalLinkHit,
    NodeContextSlice,
    NodeRelationRef,
    NodeStructureSlice,
    TextSearchHit,
)
from docwright.protocol.events import EventFamily, EventName
from docwright.workspace.compiler import WorkspaceCompiler, describe_workspace_compiler
from docwright.workspace.models import EditableRegion, WorkspaceSessionModel
from docwright.workspace.registry import WorkspaceProfileRegistry
from docwright.workspace.session import WorkspaceSession

_STRUCTURAL_KINDS = {"document", "section", "heading", "chapter", "subsection", "subsubsection"}


@dataclass(slots=True)
class NodeRef:
    """Session-aware runtime node reference.

    A ``NodeRef`` is bound to one concrete runtime-visible node. It preserves
    document query behavior while exposing Core-owned node-level actions without
    requiring callers to treat the current runtime cursor as the only node entry
    surface.
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

    @property
    def parent_node_id(self) -> str | None:
        return getattr(self.raw_node, "parent_node_id", None)

    def text_content(self) -> str | None:
        text_getter = getattr(self.raw_node, "text_content", None)
        return text_getter() if callable(text_getter) else None

    def relations(self) -> tuple[NodeRelationRef, ...]:
        relation_getter = getattr(self.raw_node, "relations", None)
        if callable(relation_getter):
            return tuple(relation_getter())
        return ()

    def context(self, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        return self.session.get_context(node_id=self.node_id, before=before, after=after)

    def structure(self) -> NodeStructureSlice:
        return self.session.get_structure(node_id=self.node_id)

    def list_internal_links(self) -> tuple[InternalLinkHit, ...]:
        return self.session.list_internal_links(node_id=self.node_id)

    def follow_internal_link(self, relation_id: str) -> NodeRef | None:
        return self.session.follow_internal_link(relation_id, node_id=self.node_id)

    def parent(self) -> NodeRef | None:
        parent_id = self.session._get_parent_id(self.node_id)
        if parent_id is None:
            return None
        return self.session.node(parent_id)

    def children(self) -> tuple[NodeRef, ...]:
        return tuple(self.session.node(child_id) for child_id in self.session._get_child_ids(self.node_id))

    def siblings(self) -> tuple[NodeRef, ...]:
        return tuple(self.session.node(sibling_id) for sibling_id in self.session._get_sibling_ids(self.node_id))

    def ancestry(self, *, include_self: bool = False) -> tuple[NodeRef, ...]:
        return tuple(
            self.session.node(ancestor_id)
            for ancestor_id in self.session._get_ancestry(self.node_id, include_self=include_self)
        )

    def highlight(self, *, level: str, reason: str | None = None) -> RuntimeEventEnvelope:
        return self.session.record_highlight(node_id=self.node_id, level=level, reason=reason)

    def warning(
        self,
        *,
        kind: str,
        severity: str,
        message: str,
        evidence: tuple[str, ...] = (),
    ) -> RuntimeEventEnvelope:
        return self.session.record_warning(
            node_id=self.node_id,
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
            node_id=self.node_id,
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


# Backward-compatibility alias for the pre-NodeRef public name.
RuntimeNodeView = NodeRef


@dataclass(slots=True)
class Locator:
    """Thin helper that resolves into one or more ``NodeRef`` objects.

    A ``Locator`` is intentionally not a second runtime object hierarchy. It is
    only a reusable query helper around ``NodeRef`` resolution.
    """

    session: RuntimeSession
    resolver: Callable[[], tuple[NodeRef, ...]]

    def all(self) -> tuple[NodeRef, ...]:
        return self.resolver()

    def first(self) -> NodeRef | None:
        results = self.all()
        return None if not results else results[0]

    def one(self) -> NodeRef:
        results = self.all()
        if len(results) != 1:
            raise LookupError(f"locator resolved {len(results)} nodes, expected exactly 1")
        return results[0]


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

    def workspace_registry_ready(self) -> bool:
        return self._workspace_registry is not None

    def workspace_compiler_info(self) -> dict[str, Any] | None:
        return describe_workspace_compiler(self._workspace_compiler)

    def workspace_compile_ready(self) -> bool:
        compiler_info = self.workspace_compiler_info()
        if compiler_info is None:
            return False
        return bool(compiler_info.get("available", True))

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

    def node(self, node_id: str) -> NodeRef:
        """Return a runtime node reference for an explicit node id."""

        return NodeRef(session=self, raw_node=self._get_node(node_id))

    def text(
        self,
        query: str,
        *,
        limit: int = 10,
        scope: str = "document",
        node_kinds: tuple[str, ...] | None = None,
    ) -> Locator:
        """Return a locator that resolves text search hits into node refs."""

        return Locator(
            session=self,
            resolver=lambda: tuple(
                self.node(hit.node_id)
                for hit in self.search_text(
                    query,
                    limit=limit,
                    scope=scope,
                    node_kinds=node_kinds,
                )
            ),
        )

    def heading(
        self,
        query: str,
        *,
        limit: int = 10,
        scope: str = "document",
    ) -> Locator:
        """Return a locator that resolves heading search hits into node refs."""

        return Locator(
            session=self,
            resolver=lambda: tuple(
                self.node(hit.node_id)
                for hit in self.search_headings(
                    query,
                    limit=limit,
                    scope=scope,
                )
            ),
        )

    def current_node(self) -> NodeRef | None:
        node_id = self._model.step.node_id
        if node_id is None:
            return None
        return self.node(node_id)

    def get_context(self, *, node_id: str | None = None, before: int = 1, after: int = 1) -> NodeContextSlice:
        focus_node_id = node_id or self._model.step.node_id
        if focus_node_id is None:
            return NodeContextSlice(focus_node_id="", before_node_ids=(), after_node_ids=())

        reading_order = self._get_reading_order()
        context_node_id = focus_node_id
        if context_node_id not in reading_order:
            resolved_focus_id = self._resolve_focusable_node_id(context_node_id)
            if resolved_focus_id is not None:
                context_node_id = resolved_focus_id

        get_context = getattr(self._document, "get_context", None)
        if callable(get_context):
            return get_context(context_node_id, before=before, after=after)

        index = reading_order.index(context_node_id)
        return NodeContextSlice(
            focus_node_id=context_node_id,
            before_node_ids=tuple(reading_order[max(0, index - before) : index]),
            after_node_ids=tuple(reading_order[index + 1 : index + 1 + after]),
        )

    def get_structure(self, *, node_id: str | None = None) -> NodeStructureSlice:
        focus_node_id = node_id or self._model.step.node_id
        if focus_node_id is None:
            return NodeStructureSlice(focus_node_id="")

        root_id = getattr(self._document, "root_id", None)
        parent_id = self._get_parent_id(focus_node_id)
        child_ids = self._get_child_ids(focus_node_id)
        sibling_ids = self._get_sibling_ids(focus_node_id)
        ancestry_ids = self._get_ancestry(focus_node_id)
        section_path_ids, section_path_titles = self._section_path_for_node(focus_node_id)
        return NodeStructureSlice(
            focus_node_id=focus_node_id,
            root_id=root_id if isinstance(root_id, str) else None,
            parent_node_id=parent_id,
            child_node_ids=child_ids,
            sibling_node_ids=sibling_ids,
            ancestry_node_ids=ancestry_ids,
            section_path_node_ids=section_path_ids,
            section_path_titles=section_path_titles,
        )

    def search_text(
        self,
        query: str,
        *,
        limit: int = 10,
        scope: str = "document",
        node_kinds: tuple[str, ...] | None = None,
    ) -> tuple[TextSearchHit, ...]:
        """Search runtime-visible IR-backed content by keyword.

        This is a runtime query surface. The runtime may internally reuse helper
        methods exposed by the backing document object, but the public contract
        remains owned by ``RuntimeSession`` rather than the document layer.
        """

        query = query.strip()
        if not query or limit < 1:
            return ()

        candidate_node_ids = self._candidate_node_ids_for_scope(scope)
        normalized_kinds = tuple(dict.fromkeys(node_kinds or ()))

        backend_search_text = getattr(self._document, "search_text", None)
        if callable(backend_search_text):
            try:
                return tuple(
                    backend_search_text(
                        query,
                        limit=limit,
                        scope=scope,
                        node_ids=candidate_node_ids,
                        node_kinds=normalized_kinds or None,
                    )
                )
            except TypeError:
                if scope == "document" and not normalized_kinds:
                    return tuple(backend_search_text(query, limit=limit))

        needle = query.casefold()
        allowed = set(candidate_node_ids)
        allowed_kinds = set(normalized_kinds) if normalized_kinds else None
        hits: list[TextSearchHit] = []
        for node_id in self._get_reading_order():
            if node_id not in allowed:
                continue
            node = self._get_node(node_id)
            kind = getattr(node, "kind", "unknown")
            if allowed_kinds is not None and kind not in allowed_kinds:
                continue
            text = self._node_text(node)
            haystack = (text or "").casefold()
            if not haystack or needle not in haystack:
                continue
            section_path_ids, section_path_titles = self._section_path_for_node(node_id)
            hits.append(
                TextSearchHit(
                    node_id=getattr(node, "node_id"),
                    node_kind=kind,
                    page_number=getattr(node, "page_number", 1),
                    text_preview=(text or "")[:240],
                    match_count=haystack.count(needle),
                    section_path_node_ids=section_path_ids,
                    section_path_titles=section_path_titles,
                    scope=scope,
                )
            )
            if len(hits) >= limit:
                break
        return tuple(hits)

    def search_headings(
        self,
        query: str,
        *,
        limit: int = 10,
        scope: str = "document",
    ) -> tuple[TextSearchHit, ...]:
        return self.search_text(query, limit=limit, scope=scope, node_kinds=tuple(_STRUCTURAL_KINDS))

    def list_internal_links(self, *, node_id: str | None = None) -> tuple[InternalLinkHit, ...]:
        focus_node_id = node_id or self._model.step.node_id
        if focus_node_id is None:
            return ()

        node = self._get_node(focus_node_id)
        relation_getter = getattr(node, "relations", None)
        relations = tuple(relation_getter()) if callable(relation_getter) else ()
        hits: list[InternalLinkHit] = []
        for relation in relations:
            if relation.kind != "internal_link_to":
                continue
            target_node = self._get_node(relation.target_id)
            hits.append(
                InternalLinkHit(
                    relation_id=relation.relation_id,
                    source_node_id=focus_node_id,
                    target_node_id=relation.target_id,
                    target_kind=getattr(target_node, "kind", "unknown"),
                    target_page_number=getattr(target_node, "page_number", 1),
                    target_text_preview=(self._node_text(target_node) or "")[:240],
                    score=relation.score,
                )
            )
        return tuple(hits)

    def jump_to_node(self, node_id: str) -> NodeRef | None:
        """Compatibility helper that updates the runtime-selected node."""

        self._permissions.ensure_allowed("jump")
        resolved_focus_id = self._resolve_focusable_node_id(node_id)
        if resolved_focus_id is None:
            raise KeyError(f"node '{node_id}' cannot be focused by the runtime")
        if self._model.step.node_id == resolved_focus_id:
            return self.current_node()

        target = self._select_node(resolved_focus_id)
        self.emit_event(
            EventName(EventFamily.NODE, "jumped"),
            {
                "requested_node_id": node_id,
                "resolved_node_id": resolved_focus_id,
                "target_node_id": resolved_focus_id,
            },
        )
        self.emit_event(EventName(EventFamily.NODE, "entered"))
        return target

    def follow_internal_link(self, relation_id: str, *, node_id: str | None = None) -> NodeRef | None:
        focus_node_id = node_id or self._model.step.node_id
        if focus_node_id is None:
            raise KeyError("no current node is active")

        for link in self.list_internal_links(node_id=focus_node_id):
            if link.relation_id != relation_id:
                continue
            target = self.jump_to_node(link.target_node_id)
            self.emit_event(
                EventName(EventFamily.NODE, "internal_link_followed"),
                {
                    "relation_id": relation_id,
                    "source_node_id": focus_node_id,
                    "target_node_id": link.target_node_id,
                },
            )
            return target
        raise KeyError(f"internal link '{relation_id}' was not found for node '{focus_node_id}'")

    def record_highlight(
        self,
        *,
        node_id: str | None = None,
        level: str,
        reason: str | None = None,
    ) -> RuntimeEventEnvelope:
        self._permissions.ensure_allowed("highlight")
        target_node_id = node_id or self._model.step.node_id
        if target_node_id is None:
            raise KeyError("no node is available for highlight")
        if self._model.step.node_id == target_node_id:
            self._model.step.highlight_count += 1
        payload: dict[str, Any] = {"level": level, "target_node_id": target_node_id}
        if reason is not None:
            payload["reason"] = reason
        return self.emit_event(EventName(EventFamily.HIGHLIGHT, "applied"), payload)

    def record_warning(
        self,
        *,
        node_id: str | None = None,
        kind: str,
        severity: str,
        message: str,
        evidence: tuple[str, ...] = (),
    ) -> RuntimeEventEnvelope:
        self._permissions.ensure_allowed("warning")
        target_node_id = node_id or self._model.step.node_id
        if target_node_id is None:
            raise KeyError("no node is available for warning")
        if self._model.step.node_id == target_node_id:
            self._model.step.warning_count += 1
        payload = {
            "kind": kind,
            "severity": severity,
            "message": message,
            "evidence": list(evidence),
            "target_node_id": target_node_id,
        }
        return self.emit_event(
            EventName(EventFamily.WARNING, "raised"),
            payload,
        )

    def open_workspace(
        self,
        *,
        node_id: str | None = None,
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
        resolved_sandbox_profile: str | None = None

        target_node = self.current_node() if node_id is None else self.node(node_id)

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
            resolved_sandbox_profile = resolved_profile.sandbox_profile
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
        self.record_workspace_opened(workspace_id=workspace_id, task=task, node_id=node_id)

        workspace = WorkspaceSession(
            WorkspaceSessionModel(
                workspace_id=workspace_id,
                task=task,
                capability_name=capability or self._model.capability_name,
                workspace_profile=workspace_profile,
                template_id=resolved_template_id,
                template_source=None if resolved_template is None else resolved_template.source,
                body_kind=resolved_body_kind,
                compiler_profile=resolved_compiler_profile,
                sandbox_profile=resolved_sandbox_profile,
                compile_required_before_submit=compile_required_before_submit,
                patch_scope=patch_scope,
                locked_sections=locked_sections,
                model_summary=model_summary,
                editable_region=resolved_editable_region or EditableRegion(),
                current_body=(
                    initial_body
                    if initial_body is not None
                    else (
                        target_node.text_content()
                        if target_node and target_node.text_content() is not None
                        else (resolved_template.default_body() if resolved_template is not None else "")
                    )
                ),
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
                "target_node_id": target_node.node_id if target_node is not None else None,
            },
            workspace_id=workspace_id,
        )
        return workspace

    def workspace(self, workspace_id: str) -> WorkspaceSession:
        return self._workspaces[workspace_id]

    def record_workspace_opened(
        self,
        *,
        workspace_id: str,
        task: str,
        node_id: str | None = None,
    ) -> RuntimeEventEnvelope:
        self._permissions.ensure_allowed("open_workspace")
        target_node_id = node_id or self._model.step.node_id
        if target_node_id is None:
            raise KeyError("no node is available for workspace open")
        max_workspaces = self._guardrail_policy.max_workspaces_per_step
        if (
            target_node_id == self._model.step.node_id
            and max_workspaces is not None
            and self._model.step.workspace_open_count >= max_workspaces
        ):
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

        if target_node_id == self._model.step.node_id:
            self._model.step.workspace_open_count += 1
            self._model.step.workspace_opened = True
        payload = {"workspace_id": workspace_id, "task": task, "target_node_id": target_node_id}
        return self.emit_event(
            EventName(EventFamily.WORKSPACE, "opened"),
            payload,
            workspace_id=workspace_id,
        )

    def advance(self) -> NodeRef | None:
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
        self._select_node(next_node_id, index=next_index)
        self.emit_event(EventName(EventFamily.NODE, "entered"))
        return self.current_node()

    def _initialize_step(self) -> None:
        reading_order = self._get_reading_order()
        if reading_order and self._model.step.node_id is None:
            self._select_node(reading_order[0], index=0)

    def _candidate_node_ids_for_scope(self, scope: str) -> tuple[str, ...]:
        if scope == "document":
            root_id = getattr(self._document, "root_id", None)
            subtree_getter = getattr(self._document, "get_subtree_node_ids", None)
            if isinstance(root_id, str) and callable(subtree_getter):
                subtree_ids = tuple(subtree_getter(root_id, include_self=False))
                if subtree_ids:
                    return subtree_ids
            return self._get_reading_order()

        current = self.current_node()
        if current is None:
            return ()

        if scope == "current_page":
            try:
                page = self._document.get_page(current.page_number)
                return tuple(page.node_ids)
            except Exception:
                return (current.node_id,)

        if scope == "current_subtree":
            subtree_getter = getattr(self._document, "get_subtree_node_ids", None)
            if callable(subtree_getter):
                return tuple(subtree_getter(current.node_id, include_self=True))
            return (current.node_id,)

        raise ValueError(f"unsupported search scope: {scope!r}")

    def _resolve_focusable_node_id(self, requested_node_id: str) -> str | None:
        reading_order = self._get_reading_order()
        if requested_node_id in reading_order:
            return requested_node_id

        subtree_getter = getattr(self._document, "get_subtree_node_ids", None)
        if callable(subtree_getter):
            subtree_ids = tuple(subtree_getter(requested_node_id, include_self=False))
            for node_id in reading_order:
                if node_id in subtree_ids:
                    return node_id
        return None

    def _section_path_for_node(self, node_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        section_ids: list[str] = []
        section_titles: list[str] = []
        for candidate_id in self._get_ancestry(node_id, include_self=True):
            if candidate_id == getattr(self._document, "root_id", None):
                continue
            try:
                candidate = self._get_node(candidate_id)
            except Exception:
                continue
            kind = getattr(candidate, "kind", "unknown")
            if kind not in _STRUCTURAL_KINDS:
                continue
            section_ids.append(candidate_id)
            title = self._node_text(candidate)
            if title:
                section_titles.append(title[:160])
        return tuple(section_ids), tuple(section_titles)

    def _get_parent_id(self, node_id: str) -> str | None:
        getter = getattr(self._document, "get_parent_id", None)
        if callable(getter):
            return getter(node_id)
        node = self._get_node(node_id)
        return getattr(node, "parent_node_id", None)

    def _get_child_ids(self, node_id: str) -> tuple[str, ...]:
        getter = getattr(self._document, "get_child_ids", None)
        if callable(getter):
            return tuple(getter(node_id))
        return ()

    def _get_sibling_ids(self, node_id: str) -> tuple[str, ...]:
        getter = getattr(self._document, "get_sibling_ids", None)
        if callable(getter):
            return tuple(getter(node_id))
        parent_id = self._get_parent_id(node_id)
        if parent_id is None:
            return ()
        return tuple(candidate for candidate in self._get_child_ids(parent_id) if candidate != node_id)

    def _get_ancestry(self, node_id: str, *, include_self: bool = False) -> tuple[str, ...]:
        getter = getattr(self._document, "get_ancestry", None)
        if callable(getter):
            return tuple(getter(node_id, include_self=include_self))

        ancestry: list[str] = []
        current = node_id if include_self else self._get_parent_id(node_id)
        while current is not None:
            ancestry.append(current)
            current = self._get_parent_id(current)
        ancestry.reverse()
        return tuple(ancestry)

    def _get_reading_order(self) -> tuple[str, ...]:
        reading_order = getattr(self._document, "reading_order", None)
        if callable(reading_order):
            reading_order = reading_order()
        if reading_order is None and hasattr(self._document, "get_reading_order"):
            reading_order = self._document.get_reading_order()
        if reading_order is None:
            return ()
        return tuple(reading_order)

    def _select_node(self, node_id: str, *, index: int | None = None) -> NodeRef:
        resolved_index = self._get_reading_order().index(node_id) if index is None else index
        self._model.step.enter_node(index=resolved_index, node_id=node_id)
        self._model.status = RuntimeSessionStatus.ACTIVE
        return self.node(node_id)

    def _get_node(self, node_id: str) -> object:
        getter = getattr(self._document, "get_node", None)
        if callable(getter):
            return getter(node_id)
        selector = getattr(self._document, "select", None)
        if callable(selector):
            return selector(node_id)
        raise AttributeError("document does not expose get_node/select lookup")

    def _node_text(self, node: object) -> str | None:
        text_getter = getattr(node, "text_content", None)
        return text_getter() if callable(text_getter) else None

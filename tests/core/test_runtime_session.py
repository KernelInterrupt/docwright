from dataclasses import dataclass

import pytest

from docwright.core.guardrails import (
    GuardrailCode,
    GuardrailViolationError,
    RuntimeGuardrailPolicy,
    RuntimePermissions,
)
from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus
from docwright.core.session import Locator, NodeRef, RuntimeNodeView, RuntimeSession
from docwright.document.interfaces import NodeContextSlice, NodeRelationRef, TextSearchHit
from docwright.workspace.profiles import WorkspaceProfile
from docwright.workspace.registry import WorkspaceProfileRegistry
from docwright.workspace.templates import EditableRegionSpec, WorkspaceTemplate


@dataclass(slots=True)
class DummyNode:
    node_id: str
    kind: str
    page_number: int = 1
    parent_node_id: str | None = None
    text: str | None = None
    relation_refs: tuple[NodeRelationRef, ...] = ()

    def text_content(self) -> str | None:
        return self.text or f"text for {self.node_id}"

    def relations(self) -> tuple[NodeRelationRef, ...]:
        return self.relation_refs


@dataclass(slots=True)
class DummyPage:
    page_number: int
    node_ids: tuple[str, ...]

    def get_node(self, node_id: str) -> DummyNode:
        raise KeyError(node_id)



def make_workspace_registry() -> WorkspaceProfileRegistry:
    registry = WorkspaceProfileRegistry()
    registry.register_template(
        WorkspaceTemplate(
            template_id="default_annotation_tex",
            task="annotation",
            body_kind="latex_body",
            source="\n".join(
                [
                    r"\documentclass{article}",
                    "% DOCWRIGHT:BODY_START",
                    "% DOCWRIGHT:BODY_END",
                ]
            ),
            editable_regions=(
                EditableRegionSpec(
                    name="body",
                    mode="marker_range",
                    start_marker="% DOCWRIGHT:BODY_START",
                    end_marker="% DOCWRIGHT:BODY_END",
                ),
            ),
            compiler_profile="tectonic",
        )
    )
    registry.register_profile(
        WorkspaceProfile(
            profile_name="latex_annotation",
            task="annotation",
            template_id="default_annotation_tex",
            body_kind="latex_body",
            compiler_profile="tectonic",
            locked_sections=("preamble", "document_structure"),
            model_summary="Edit only the annotation body.",
            sandbox_profile="local_process",
        )
    )
    return registry


class DummyDocument:
    def __init__(self) -> None:
        self.root_id = "root"
        self.reading_order = ("node-1", "node-2")
        self._nodes = {
            "root": DummyNode(node_id="root", kind="document", parent_node_id=None, text="Manual"),
            "sec-1": DummyNode(node_id="sec-1", kind="section", page_number=1, parent_node_id="root", text="Device A"),
            "node-1": DummyNode(
                node_id="node-1",
                kind="paragraph",
                page_number=1,
                parent_node_id="sec-1",
                text="text for node-1",
                relation_refs=(NodeRelationRef(relation_id="rel-link-1", kind="internal_link_to", target_id="sec-2"),),
            ),
            "sec-2": DummyNode(node_id="sec-2", kind="section", page_number=2, parent_node_id="root", text="Device B"),
            "node-2": DummyNode(
                node_id="node-2",
                kind="figure",
                page_number=2,
                parent_node_id="sec-2",
                text="text for node-2",
                relation_refs=(NodeRelationRef(relation_id="rel-1", kind="supports", target_id="node-1"),),
            ),
        }
        self._children = {
            None: ("root",),
            "root": ("sec-1", "sec-2"),
            "sec-1": ("node-1",),
            "sec-2": ("node-2",),
        }
        self._page_index = {1: ("sec-1", "node-1"), 2: ("sec-2", "node-2")}

    def get_node(self, node_id: str) -> DummyNode:
        return self._nodes[node_id]

    def get_page(self, page_number: int) -> DummyPage:
        return DummyPage(page_number=page_number, node_ids=self._page_index[page_number])

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        index = self.reading_order.index(node_id)
        return NodeContextSlice(
            focus_node_id=node_id,
            before_node_ids=tuple(self.reading_order[max(0, index - before) : index]),
            after_node_ids=tuple(self.reading_order[index + 1 : index + 1 + after]),
        )

    def get_parent_id(self, node_id: str) -> str | None:
        return self._nodes[node_id].parent_node_id

    def get_child_ids(self, node_id: str) -> tuple[str, ...]:
        return self._children.get(node_id, ())

    def get_sibling_ids(self, node_id: str) -> tuple[str, ...]:
        parent_id = self.get_parent_id(node_id)
        return tuple(candidate for candidate in self._children.get(parent_id, ()) if candidate != node_id)

    def get_ancestry(self, node_id: str, *, include_self: bool = False) -> tuple[str, ...]:
        ancestry: list[str] = []
        current = node_id if include_self else self.get_parent_id(node_id)
        while current is not None:
            ancestry.append(current)
            current = self.get_parent_id(current)
        ancestry.reverse()
        return tuple(ancestry)

    def get_subtree_node_ids(self, node_id: str, *, include_self: bool = True) -> tuple[str, ...]:
        ordered: list[str] = []

        def visit(candidate: str) -> None:
            if candidate in self._nodes:
                ordered.append(candidate)
            for child in self.get_child_ids(candidate):
                visit(child)

        if include_self:
            visit(node_id)
        else:
            for child in self.get_child_ids(node_id):
                visit(child)
        reading_order_index = {candidate: index for index, candidate in enumerate(self.reading_order)}
        ordered.sort(key=lambda candidate: reading_order_index.get(candidate, len(reading_order_index)))
        return tuple(dict.fromkeys(ordered))

    def search_text(
        self,
        query: str,
        *,
        limit: int = 10,
        scope: str = "document",
        node_ids: tuple[str, ...] | None = None,
        node_kinds: tuple[str, ...] | None = None,
    ) -> tuple[TextSearchHit, ...]:
        needle = query.casefold()
        allowed = set(node_ids) if node_ids is not None else set(self._nodes)
        allowed_kinds = set(node_kinds) if node_kinds else None
        hits: list[TextSearchHit] = []
        for node_id, node in self._nodes.items():
            if node_id not in allowed:
                continue
            if allowed_kinds is not None and node.kind not in allowed_kinds:
                continue
            text = node.text_content() or ""
            haystack = text.casefold()
            if needle not in haystack:
                continue
            section_path_ids = tuple(candidate for candidate in self.get_ancestry(node_id, include_self=True) if self._nodes.get(candidate) and self._nodes[candidate].kind == "section")
            section_path_titles = tuple(self._nodes[candidate].text_content() or "" for candidate in section_path_ids)
            hits.append(
                TextSearchHit(
                    node_id=node_id,
                    node_kind=node.kind,
                    page_number=node.page_number,
                    text_preview=text[:240],
                    match_count=haystack.count(needle),
                    section_path_node_ids=section_path_ids,
                    section_path_titles=section_path_titles,
                    scope=scope,
                )
            )
            if len(hits) >= limit:
                break
        return tuple(hits)


def test_runtime_session_initializes_core_owned_state_and_start_event() -> None:
    model = RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1")

    session = RuntimeSession(model, document=DummyDocument())

    assert session.model is model
    assert session.document.__class__ is DummyDocument
    assert session.model.status is RuntimeSessionStatus.ACTIVE
    assert [event.as_protocol_event().event_name for event in session.events()] == [
        "runtime.started",
        "node.entered",
    ]


def test_runtime_session_uses_explicit_permissions_and_policy() -> None:
    permissions = RuntimePermissions(allow_advance=False)
    policy = RuntimeGuardrailPolicy(require_highlight_before_advance=True, max_workspaces_per_step=1)
    model = RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1")

    session = RuntimeSession(model, document=DummyDocument(), permissions=permissions, guardrail_policy=policy)

    assert session.permissions is permissions
    assert session.guardrail_policy is policy


def test_runtime_session_emits_contextual_events() -> None:
    model = RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1")
    session = RuntimeSession(model, document=DummyDocument())

    event = session.emit_event("node.entered", {"kind": "paragraph"})
    protocol_event = event.as_protocol_event()

    assert protocol_event.event_name == "node.entered"
    assert protocol_event.payload["step_index"] == 0
    assert protocol_event.payload["node_id"] == "node-1"
    assert protocol_event.payload["kind"] == "paragraph"


def test_runtime_session_current_node_returns_runtime_node_view() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    node = session.current_node()

    assert isinstance(node, RuntimeNodeView)
    assert node is not None
    assert node.node_id == "node-1"
    assert node.kind == "paragraph"
    assert node.page_number == 1
    assert node.parent_node_id == "sec-1"
    assert node.text_content() == "text for node-1"


def test_runtime_session_can_return_explicit_node_refs_outside_current_node() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    node = session.node("sec-2")

    assert isinstance(node, NodeRef)
    assert isinstance(node, RuntimeNodeView)
    assert node.node_id == "sec-2"
    assert node.text_content() == "Device B"
    assert node.context().focus_node_id == "node-2"
    assert node.structure().child_node_ids == ("node-2",)
    assert [child.node_id for child in node.children()] == ["node-2"]
    assert [ancestor.node_id for ancestor in node.ancestry(include_self=True)] == ["root", "sec-2"]
    assert node.list_internal_links() == ()


def test_runtime_session_locator_helpers_resolve_into_node_refs() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    heading_locator = session.heading("Device B")
    text_locator = session.text("text for node", limit=5)

    assert isinstance(heading_locator, Locator)
    assert isinstance(text_locator, Locator)
    assert heading_locator.first() is not None
    assert heading_locator.first().node_id == "sec-2"
    assert heading_locator.one().node_id == "sec-2"
    assert [node.node_id for node in text_locator.all()] == ["node-1", "node-2"]
    assert all(isinstance(node, NodeRef) for node in text_locator.all())


def test_runtime_session_get_context_uses_document_context_surface() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    context = session.get_context(before=1, after=1)

    assert context == NodeContextSlice(
        focus_node_id="node-1",
        before_node_ids=(),
        after_node_ids=("node-2",),
    )


def test_runtime_session_get_structure_returns_parent_children_siblings_and_ancestry() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    structure = session.get_structure()

    assert structure.focus_node_id == "node-1"
    assert structure.root_id == "root"
    assert structure.parent_node_id == "sec-1"
    assert structure.child_node_ids == ()
    assert structure.sibling_node_ids == ()
    assert structure.ancestry_node_ids == ("root", "sec-1")
    assert structure.section_path_node_ids == ("sec-1",)
    assert structure.section_path_titles == ("Device A",)


def test_runtime_node_view_supports_relations_warning_and_workspace_actions() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        workspace_registry=make_workspace_registry(),
    )
    node = session.current_node()
    assert node is not None

    warning_event = node.warning(
        kind="risk",
        severity="medium",
        message="Needs review",
        evidence=("node-1",),
    )
    workspace = node.open_workspace(
        task="annotation",
        workspace_profile="latex_annotation",
        template_id="default_annotation_tex",
        body_kind="latex_body",
        compiler_profile="tectonic",
    )

    assert session.model.step.warning_count == 1
    assert warning_event.as_protocol_event().event_name == "warning.raised"
    assert workspace.workspace_id in {item.workspace_id for item in session.workspaces()}
    assert workspace.model.workspace_profile == "latex_annotation"
    assert workspace.model.template_id == "default_annotation_tex"
    assert workspace.model.body_kind == "latex_body"
    assert workspace.model.compiler_profile == "tectonic"
    assert workspace.read_body() == "text for node-1"


def test_runtime_session_record_highlight_updates_step_and_emits_event() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    event = session.record_highlight(level="important", reason="key claim")

    assert session.model.step.highlight_count == 1
    assert event.as_protocol_event().event_name == "highlight.applied"
    assert event.as_protocol_event().payload["reason"] == "key claim"
    assert event.as_protocol_event().payload["target_node_id"] == "node-1"


def test_node_ref_actions_can_target_non_current_nodes_explicitly() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        workspace_registry=make_workspace_registry(),
    )

    node = session.node("node-2")
    highlight_event = node.highlight(level="important", reason="explicit target")
    warning_event = node.warning(
        kind="cross_reference",
        severity="medium",
        message="inspect this figure",
    )
    workspace = node.open_workspace(task="annotation", workspace_profile="latex_annotation")

    assert session.model.step.node_id == "node-1"
    assert session.model.step.highlight_count == 0
    assert highlight_event.as_protocol_event().payload["target_node_id"] == "node-2"
    assert warning_event.as_protocol_event().payload["target_node_id"] == "node-2"
    assert workspace.read_body() == "text for node-2"


def test_node_ref_can_follow_internal_links_without_using_current_node_lookup() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    source = session.node("node-1")
    links = source.list_internal_links()
    target = source.follow_internal_link("rel-link-1")

    assert links[0].target_node_id == "sec-2"
    assert target is not None
    assert target.node_id == "node-2"
    assert session.model.step.node_id == "node-2"
    assert session.events()[-1].as_protocol_event().event_name == "node.internal_link_followed"


def test_runtime_session_record_workspace_opened_updates_step_and_emits_event() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    event = session.record_workspace_opened(workspace_id="ws-1", task="annotation")

    assert session.model.step.workspace_opened is True
    assert session.model.step.workspace_open_count == 1
    assert event.as_protocol_event().event_name == "workspace.opened"
    assert event.as_protocol_event().payload["target_node_id"] == "node-1"


def test_runtime_session_advance_moves_to_next_node_and_resets_step_state() -> None:
    model = RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1")
    session = RuntimeSession(model, document=DummyDocument())
    model.step.highlight_count = 2
    model.step.warning_count = 1
    model.step.workspace_opened = True
    model.step.workspace_open_count = 1

    node = session.advance()

    assert node is not None
    assert node.node_id == "node-2"
    assert node.kind == "figure"
    assert node.relations()[0].relation_id == "rel-1"
    assert model.step.index == 1
    assert model.step.node_id == "node-2"
    assert model.step.highlight_count == 0
    assert model.step.warning_count == 0
    assert model.step.workspace_opened is False
    assert model.step.workspace_open_count == 0
    assert session.events()[-1].as_protocol_event().event_name == "node.entered"


def test_runtime_session_jump_to_node_repositions_focus_without_using_advance_guardrail() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        guardrail_policy=RuntimeGuardrailPolicy(require_highlight_before_advance=True),
    )

    node = session.jump_to_node("sec-2")

    assert node is not None
    assert node.node_id == "node-2"
    assert session.model.step.index == 1
    assert [event.as_protocol_event().event_name for event in session.events()][-2:] == ["node.jumped", "node.entered"]
    assert session.events()[-2].as_protocol_event().payload["target_node_id"] == "node-2"


def test_runtime_session_advance_requires_highlight_when_policy_enabled() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        guardrail_policy=RuntimeGuardrailPolicy(require_highlight_before_advance=True),
    )

    with pytest.raises(GuardrailViolationError) as exc_info:
        session.advance()

    assert exc_info.value.violation.code is GuardrailCode.HIGHLIGHT_REQUIRED_BEFORE_ADVANCE


def test_runtime_session_highlight_allows_advance_when_policy_enabled() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        guardrail_policy=RuntimeGuardrailPolicy(require_highlight_before_advance=True),
    )
    session.record_highlight(level="important")

    node = session.advance()

    assert node is not None
    assert node.node_id == "node-2"


def test_runtime_session_enforces_one_workspace_per_step_when_configured() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        guardrail_policy=RuntimeGuardrailPolicy(max_workspaces_per_step=1),
    )
    session.record_workspace_opened(workspace_id="ws-1", task="annotation")

    with pytest.raises(GuardrailViolationError) as exc_info:
        session.record_workspace_opened(workspace_id="ws-2", task="annotation")

    assert exc_info.value.violation.code is GuardrailCode.WORKSPACE_LIMIT_REACHED


def test_runtime_session_workspace_limit_resets_after_advance() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        guardrail_policy=RuntimeGuardrailPolicy(max_workspaces_per_step=1),
    )
    session.record_workspace_opened(workspace_id="ws-1", task="annotation")
    session.advance()

    session.record_workspace_opened(workspace_id="ws-2", task="annotation")

    assert session.model.step.workspace_open_count == 1
    assert session.model.step.node_id == "node-2"


def test_runtime_session_advance_completes_at_end_of_reading_order() -> None:
    model = RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1")
    session = RuntimeSession(model, document=DummyDocument())

    session.advance()
    result = session.advance()

    assert result is None
    assert model.status is RuntimeSessionStatus.COMPLETED
    assert session.events()[-1].as_protocol_event().event_name == "runtime.completed"


def test_runtime_session_respects_advance_permission() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        permissions=RuntimePermissions(allow_advance=False),
    )

    with pytest.raises(GuardrailViolationError) as exc_info:
        session.advance()

    assert exc_info.value.violation.code is GuardrailCode.ACTION_NOT_PERMITTED


def test_runtime_session_respects_jump_permission() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        permissions=RuntimePermissions(allow_jump=False),
    )

    with pytest.raises(GuardrailViolationError) as exc_info:
        session.jump_to_node("sec-2")

    assert exc_info.value.violation.code is GuardrailCode.ACTION_NOT_PERMITTED


def test_runtime_session_open_workspace_resolves_profile_defaults_from_registry() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        workspace_registry=make_workspace_registry(),
    )
    node = session.current_node()
    assert node is not None

    workspace = node.open_workspace(task="annotation", workspace_profile="latex_annotation")

    assert workspace.model.workspace_profile == "latex_annotation"
    assert workspace.model.template_id == "default_annotation_tex"
    assert workspace.model.body_kind == "latex_body"
    assert workspace.model.compiler_profile == "tectonic"
    assert workspace.model.editable_region.name == "body"
    assert workspace.model.editable_region.start_marker == "% DOCWRIGHT:BODY_START"
    assert workspace.model.editable_region.end_marker == "% DOCWRIGHT:BODY_END"
    assert workspace.model.locked_sections == ("preamble", "document_structure")
    assert workspace.model.patch_scope == "editable_region_only"
    assert workspace.model.model_summary == "Edit only the annotation body."
    assert workspace.model.sandbox_profile == "local_process"
    assert "text for node-1" in workspace.describe()["assembled_source"]


def test_runtime_session_open_workspace_rejects_profile_without_registry() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    with pytest.raises(ValueError, match="workspace_profile requires"):
        session.open_workspace(task="annotation", workspace_profile="latex_annotation")


def test_runtime_session_open_workspace_rejects_task_profile_mismatch() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        workspace_registry=make_workspace_registry(),
    )

    with pytest.raises(ValueError, match="requires task"):
        session.open_workspace(task="review", workspace_profile="latex_annotation")


def test_runtime_session_search_text_supports_scope_and_structure_metadata() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    hits = session.search_text("text for node", limit=5, scope="current_page")

    assert [hit.node_id for hit in hits] == ["node-1"]
    assert hits[0].node_kind == "paragraph"
    assert hits[0].match_count == 1
    assert hits[0].section_path_node_ids == ("sec-1",)
    assert hits[0].scope == "current_page"


def test_runtime_session_search_headings_and_internal_link_navigation() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    heading_hits = session.search_headings("Device B", limit=5)
    link_hits = session.list_internal_links()
    followed = session.follow_internal_link("rel-link-1")

    assert [hit.node_id for hit in heading_hits] == ["sec-2"]
    assert link_hits[0].target_node_id == "sec-2"
    assert followed is not None
    assert followed.node_id == "node-2"
    assert session.events()[-1].as_protocol_event().event_name == "node.internal_link_followed"

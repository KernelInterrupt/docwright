from dataclasses import dataclass

import pytest

from docwright.core.guardrails import (
    GuardrailCode,
    GuardrailViolationError,
    RuntimeGuardrailPolicy,
    RuntimePermissions,
)
from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus
from docwright.core.session import RuntimeNodeView, RuntimeSession
from docwright.document.interfaces import NodeContextSlice, NodeRelationRef


@dataclass(slots=True)
class DummyNode:
    node_id: str
    kind: str
    page_number: int = 1
    relation_refs: tuple[NodeRelationRef, ...] = ()

    def text_content(self) -> str | None:
        return f"text for {self.node_id}"

    def relations(self) -> tuple[NodeRelationRef, ...]:
        return self.relation_refs


class DummyDocument:
    def __init__(self) -> None:
        self.reading_order = ("node-1", "node-2")
        self._nodes = {
            "node-1": DummyNode(node_id="node-1", kind="paragraph"),
            "node-2": DummyNode(
                node_id="node-2",
                kind="figure",
                relation_refs=(NodeRelationRef(relation_id="rel-1", kind="supports", target_id="node-1"),),
            ),
        }

    def get_node(self, node_id: str) -> DummyNode:
        return self._nodes[node_id]

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        index = self.reading_order.index(node_id)
        return NodeContextSlice(
            focus_node_id=node_id,
            before_node_ids=tuple(self.reading_order[max(0, index - before) : index]),
            after_node_ids=tuple(self.reading_order[index + 1 : index + 1 + after]),
        )


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
    assert node.text_content() == "text for node-1"


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


def test_runtime_node_view_supports_relations_warning_and_workspace_actions() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )
    node = session.current_node()
    assert node is not None

    warning_event = node.warning(
        kind="risk",
        severity="medium",
        message="Needs review",
        evidence=("node-1",),
    )
    workspace = node.open_workspace(task="annotation")

    assert session.model.step.warning_count == 1
    assert warning_event.as_protocol_event().event_name == "warning.raised"
    assert workspace.workspace_id in {item.workspace_id for item in session.workspaces()}
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


def test_runtime_session_record_workspace_opened_updates_step_and_emits_event() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
    )

    event = session.record_workspace_opened(workspace_id="ws-1", task="annotation")

    assert session.model.step.workspace_opened is True
    assert session.model.step.workspace_open_count == 1
    assert event.as_protocol_event().event_name == "workspace.opened"


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

from dataclasses import dataclass

import pytest

from docwright.core.guardrails import (
    GuardrailCode,
    GuardrailViolationError,
    RuntimeGuardrailPolicy,
    RuntimePermissions,
)
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession


@dataclass(slots=True)
class DummyNode:
    node_id: str


class DummyDocument:
    def __init__(self) -> None:
        self.reading_order = ("node-1", "node-2", "node-3")
        self._nodes = {node_id: DummyNode(node_id=node_id) for node_id in self.reading_order}

    def get_node(self, node_id: str) -> DummyNode:
        return self._nodes[node_id]


def make_session(
    *,
    permissions: RuntimePermissions | None = None,
    policy: RuntimeGuardrailPolicy | None = None,
) -> RuntimeSession:
    return RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=DummyDocument(),
        permissions=permissions,
        guardrail_policy=policy,
    )


def test_runtime_permissions_enforce_action_access() -> None:
    session = make_session(
        permissions=RuntimePermissions(
            allow_highlight=False,
            allow_open_workspace=False,
            allow_advance=False,
        )
    )

    with pytest.raises(GuardrailViolationError) as highlight_exc:
        session.record_highlight(level="important")
    with pytest.raises(GuardrailViolationError) as workspace_exc:
        session.record_workspace_opened(workspace_id="ws-1", task="annotation")
    with pytest.raises(GuardrailViolationError) as advance_exc:
        session.advance()

    assert highlight_exc.value.violation.code is GuardrailCode.ACTION_NOT_PERMITTED
    assert workspace_exc.value.violation.code is GuardrailCode.ACTION_NOT_PERMITTED
    assert advance_exc.value.violation.code is GuardrailCode.ACTION_NOT_PERMITTED


def test_runtime_guardrail_policy_enforces_step_rules_across_progression() -> None:
    session = make_session(
        policy=RuntimeGuardrailPolicy(
            require_highlight_before_advance=True,
            max_workspaces_per_step=1,
        )
    )

    with pytest.raises(GuardrailViolationError) as first_advance_exc:
        session.advance()
    assert first_advance_exc.value.violation.code is GuardrailCode.HIGHLIGHT_REQUIRED_BEFORE_ADVANCE

    session.record_highlight(level="important")
    session.record_workspace_opened(workspace_id="ws-1", task="annotation")

    with pytest.raises(GuardrailViolationError) as second_workspace_exc:
        session.record_workspace_opened(workspace_id="ws-2", task="annotation")
    assert second_workspace_exc.value.violation.code is GuardrailCode.WORKSPACE_LIMIT_REACHED

    session.advance()

    session.record_highlight(level="important")
    session.record_workspace_opened(workspace_id="ws-3", task="annotation")

    assert session.model.step.node_id == "node-2"
    assert session.model.step.workspace_open_count == 1

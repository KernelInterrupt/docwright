import pytest

from docwright.core.guardrails import GuardrailCode, GuardrailViolationError, RuntimeGuardrailPolicy
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


def make_session() -> RuntimeSession:
    return RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph"),
                InMemoryNode(node_id="node-2", kind="paragraph"),
            ],
        ),
        guardrail_policy=RuntimeGuardrailPolicy(
            require_highlight_before_advance=True,
            max_workspaces_per_step=1,
        ),
    )


def test_runtime_guardrails_e2e_block_and_then_allow_progression() -> None:
    session = make_session()

    with pytest.raises(GuardrailViolationError) as advance_exc:
        session.advance()
    assert advance_exc.value.violation.code is GuardrailCode.HIGHLIGHT_REQUIRED_BEFORE_ADVANCE

    session.record_highlight(level="important")
    session.record_workspace_opened(workspace_id="ws-1", task="annotation")

    with pytest.raises(GuardrailViolationError) as workspace_exc:
        session.record_workspace_opened(workspace_id="ws-2", task="annotation")
    assert workspace_exc.value.violation.code is GuardrailCode.WORKSPACE_LIMIT_REACHED

    session.advance()

    assert session.model.step.node_id == "node-2"

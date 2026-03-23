from datetime import UTC, datetime

from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus, RuntimeStepState


def test_runtime_step_state_defaults_are_policy_neutral() -> None:
    step = RuntimeStepState()

    assert step.index == 0
    assert step.node_id is None
    assert step.highlight_count == 0
    assert step.warning_count == 0
    assert step.workspace_opened is False
    assert step.workspace_open_count == 0


def test_runtime_step_state_enter_node_resets_per_step_state() -> None:
    step = RuntimeStepState(
        index=4,
        node_id="node-old",
        highlight_count=1,
        warning_count=2,
        workspace_opened=True,
        workspace_open_count=3,
    )

    step.enter_node(index=5, node_id="node-new")

    assert step.index == 5
    assert step.node_id == "node-new"
    assert step.highlight_count == 0
    assert step.warning_count == 0
    assert step.workspace_opened is False
    assert step.workspace_open_count == 0


def test_runtime_session_model_uses_core_owned_identifiers() -> None:
    session = RuntimeSessionModel(
        session_id="session-1",
        run_id="run-1",
        document_id="doc-1",
        capability_name="guided_reading",
        adapter_name="codex",
    )

    assert session.status is RuntimeSessionStatus.INITIALIZED
    assert session.step == RuntimeStepState()
    assert session.metadata == {}
    assert session.created_at.tzinfo is UTC
    assert session.updated_at.tzinfo is UTC


def test_runtime_session_touch_updates_timestamp() -> None:
    session = RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1")
    new_time = datetime(2026, 3, 24, 12, 0, tzinfo=UTC)

    session.touch(at=new_time)

    assert session.updated_at == new_time

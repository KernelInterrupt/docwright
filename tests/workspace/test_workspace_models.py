from docwright.workspace.models import (
    CompileError,
    CompileResult,
    EditableRegion,
    WorkspaceSessionModel,
    WorkspaceState,
)


def test_workspace_session_defaults_are_workspace_scoped() -> None:
    session = WorkspaceSessionModel(workspace_id="ws-1", task="annotation")

    assert session.state is WorkspaceState.INITIALIZED
    assert session.editable_region == EditableRegion()
    assert session.current_body == ""
    assert session.current_compile_result is None
    assert session.history == []
    assert session.is_terminal is False


def test_workspace_session_record_appends_history_entry() -> None:
    session = WorkspaceSessionModel(workspace_id="ws-1", task="annotation")

    entry = session.record("workspace.opened", node_id="node-1")

    assert entry.action == "workspace.opened"
    assert entry.details == {"node_id": "node-1"}
    assert session.history == [entry]


def test_workspace_session_set_state_uses_explicit_enum() -> None:
    session = WorkspaceSessionModel(workspace_id="ws-1", task="annotation")

    session.set_state(WorkspaceState.EDITING)

    assert session.state is WorkspaceState.EDITING


def test_compile_result_captures_backend_output_and_errors() -> None:
    error = CompileError(
        code="latex.undefined_control_sequence",
        message="Undefined control sequence",
        line=14,
        snippet=r"\\baddcommand",
        terminal=True,
    )
    result = CompileResult(
        ok=False,
        backend_name="fake-latex",
        rendered_content=None,
        errors=(error,),
    )

    assert result.ok is False
    assert result.backend_name == "fake-latex"
    assert result.rendered_content is None
    assert result.errors == (error,)

from dataclasses import dataclass

import pytest

from docwright.workspace.models import CompileError, CompileResult, WorkspaceSessionModel, WorkspaceState
from docwright.workspace.session import WorkspaceGuardrailError, WorkspaceSession


@dataclass(slots=True)
class StubCompiler:
    result: CompileResult

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        return self.result


def test_workspace_session_tracks_model_identity_and_open_event() -> None:
    model = WorkspaceSessionModel(workspace_id="ws-1", task="annotation")

    session = WorkspaceSession(model)

    assert session.model is model
    assert session.workspace_id == "ws-1"
    assert session.task == "annotation"
    assert model.history[0].action == "workspace.opened"


def test_workspace_session_returns_structured_compile_errors() -> None:
    model = WorkspaceSessionModel(
        workspace_id="ws-1",
        task="annotation",
        current_compile_result=CompileResult(
            ok=False,
            backend_name="fake-latex",
            errors=(CompileError(code="bad", message="Bad compile"),),
        ),
    )

    session = WorkspaceSession(model)

    assert session.get_compile_errors() == (CompileError(code="bad", message="Bad compile"),)


def test_read_body_emits_history_without_mutating_state() -> None:
    model = WorkspaceSessionModel(workspace_id="ws-1", task="annotation", current_body="draft")
    session = WorkspaceSession(model)

    body = session.read_body()

    assert body == "draft"
    assert model.state is WorkspaceState.INITIALIZED
    assert model.history[-1].action == "workspace.body_read"


def test_write_body_updates_body_state_and_invalidates_compile_result() -> None:
    model = WorkspaceSessionModel(
        workspace_id="ws-1",
        task="annotation",
        current_compile_result=CompileResult(ok=True, backend_name="fake"),
    )
    session = WorkspaceSession(model)

    session.write_body("updated")

    assert model.current_body == "updated"
    assert model.current_compile_result is None
    assert model.state is WorkspaceState.EDITING
    assert model.history[-1].action == "workspace.body_written"


def test_patch_body_replaces_first_match_and_marks_editing() -> None:
    model = WorkspaceSessionModel(workspace_id="ws-1", task="annotation", current_body="alpha beta beta")
    session = WorkspaceSession(model)

    session.patch_body("beta", "gamma")

    assert model.current_body == "alpha gamma beta"
    assert model.state is WorkspaceState.EDITING
    assert model.history[-1].action == "workspace.body_patched"


def test_patch_body_rejects_missing_target() -> None:
    session = WorkspaceSession(WorkspaceSessionModel(workspace_id="ws-1", task="annotation"))

    with pytest.raises(ValueError, match="not found"):
        session.patch_body("missing", "replacement")


def test_compile_success_updates_state_and_history() -> None:
    model = WorkspaceSessionModel(workspace_id="ws-1", task="annotation", current_body="draft")
    compiler = StubCompiler(result=CompileResult(ok=True, backend_name="fake", rendered_content="pdf"))
    session = WorkspaceSession(model, compiler=compiler)

    result = session.compile()

    assert result.ok is True
    assert model.current_compile_result == result
    assert model.state is WorkspaceState.COMPILED
    assert [entry.action for entry in model.history[-2:]] == [
        "workspace.compile_started",
        "workspace.compiled",
    ]


def test_compile_failure_updates_state_and_exposes_errors() -> None:
    error = CompileError(code="bad", message="Bad compile", terminal=True)
    model = WorkspaceSessionModel(workspace_id="ws-1", task="annotation", current_body="draft")
    compiler = StubCompiler(result=CompileResult(ok=False, backend_name="fake", errors=(error,)))
    session = WorkspaceSession(model, compiler=compiler)

    result = session.compile()

    assert result.ok is False
    assert model.state is WorkspaceState.COMPILE_FAILED
    assert session.get_compile_errors() == (error,)
    assert model.history[-1].action == "workspace.compile_failed"


def test_compile_requires_configured_compiler() -> None:
    session = WorkspaceSession(WorkspaceSessionModel(workspace_id="ws-1", task="annotation"))

    with pytest.raises(WorkspaceGuardrailError, match="not configured"):
        session.compile()


def test_compile_rejects_submitted_workspace() -> None:
    model = WorkspaceSessionModel(workspace_id="ws-1", task="annotation")
    model.set_state(WorkspaceState.SUBMITTED)
    session = WorkspaceSession(model, compiler=StubCompiler(result=CompileResult(ok=True, backend_name="fake")))

    with pytest.raises(WorkspaceGuardrailError, match="submitted"):
        session.compile()


def test_submit_requires_successful_compile() -> None:
    session = WorkspaceSession(WorkspaceSessionModel(workspace_id="ws-1", task="annotation"))

    with pytest.raises(WorkspaceGuardrailError, match="successful compile"):
        session.submit()


def test_submit_success_freezes_workspace() -> None:
    model = WorkspaceSessionModel(workspace_id="ws-1", task="annotation", current_body="draft")
    session = WorkspaceSession(
        model,
        compiler=StubCompiler(result=CompileResult(ok=True, backend_name="fake", rendered_content="pdf")),
    )
    compiled = session.compile()

    submitted = session.submit()

    assert submitted == compiled
    assert model.state is WorkspaceState.SUBMITTED
    assert model.submitted_at is not None
    assert model.history[-1].action == "workspace.submitted"

    with pytest.raises(WorkspaceGuardrailError, match="cannot mutate"):
        session.write_body("after submit")

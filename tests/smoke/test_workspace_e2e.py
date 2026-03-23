from dataclasses import dataclass, field

from docwright.workspace.models import CompileError, CompileResult, WorkspaceSessionModel, WorkspaceState
from docwright.workspace.session import WorkspaceSession


@dataclass(slots=True)
class SequenceCompiler:
    results: list[CompileResult] = field(default_factory=list)

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        return self.results.pop(0)


def test_workspace_e2e_lifecycle_reaches_submission() -> None:
    session = WorkspaceSession(
        WorkspaceSessionModel(workspace_id="ws-1", task="annotation"),
        compiler=SequenceCompiler(
            results=[
                CompileResult(
                    ok=False,
                    backend_name="fake-latex",
                    errors=(CompileError(code="bad", message="Bad compile", terminal=True),),
                ),
                CompileResult(ok=True, backend_name="fake-latex", rendered_content="compiled"),
            ]
        ),
    )

    session.write_body("draft v1")
    failed = session.compile()
    session.patch_body("v1", "v2")
    compiled = session.compile()
    submitted = session.submit()

    assert failed.ok is False
    assert compiled.ok is True
    assert submitted == compiled
    assert session.model.state is WorkspaceState.SUBMITTED
    assert [entry.action for entry in session.model.history] == [
        "workspace.opened",
        "workspace.body_written",
        "workspace.compile_started",
        "workspace.compile_failed",
        "workspace.body_patched",
        "workspace.compile_started",
        "workspace.compiled",
        "workspace.submitted",
    ]

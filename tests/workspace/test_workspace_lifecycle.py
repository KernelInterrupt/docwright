from dataclasses import dataclass, field

import pytest

from docwright.workspace.models import CompileError, CompileResult, WorkspaceSessionModel, WorkspaceState
from docwright.workspace.session import WorkspaceGuardrailError, WorkspaceSession


@dataclass(slots=True)
class SequenceCompiler:
    results: list[CompileResult] = field(default_factory=list)

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        if not self.results:
            raise AssertionError("compiler called more times than expected")
        return self.results.pop(0)


def test_workspace_full_lifecycle_from_edit_to_submit() -> None:
    compiler = SequenceCompiler(
        results=[
            CompileResult(
                ok=False,
                backend_name="fake-latex",
                errors=(
                    CompileError(
                        code="latex.undefined_control_sequence",
                        message="Undefined control sequence",
                        line=3,
                        snippet=r"\\baddcommand",
                        terminal=True,
                    ),
                ),
            ),
            CompileResult(ok=True, backend_name="fake-latex", rendered_content="compiled-pdf"),
        ]
    )
    session = WorkspaceSession(
        WorkspaceSessionModel(workspace_id="ws-1", task="annotation"),
        compiler=compiler,
    )

    session.write_body("draft v1")
    first_result = session.compile()

    assert first_result.ok is False
    assert session.model.state is WorkspaceState.COMPILE_FAILED
    assert session.get_compile_errors()[0].code == "latex.undefined_control_sequence"

    session.patch_body("v1", "v2")
    second_result = session.compile()
    submitted = session.submit()

    assert second_result.ok is True
    assert submitted == second_result
    assert session.model.state is WorkspaceState.SUBMITTED
    assert session.model.submitted_at is not None
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

    with pytest.raises(WorkspaceGuardrailError, match="cannot mutate"):
        session.patch_body("v2", "v3")

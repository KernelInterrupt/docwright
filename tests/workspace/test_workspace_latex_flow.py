from dataclasses import dataclass, field
from typing import Any

from docwright.workspace.latex import LatexCompilerProfile, LatexWorkspaceCompiler
from docwright.workspace.models import EditableRegion, WorkspaceSessionModel, WorkspaceState
from docwright.workspace.sandbox import SandboxRunResult
from docwright.workspace.session import WorkspaceSession


@dataclass(slots=True)
class SequenceSandbox:
    results: list[SandboxRunResult] = field(default_factory=list)
    requests: list[Any] = field(default_factory=list)

    def describe(self) -> dict[str, object]:
        return {"name": "sequence_sandbox", "available": True}

    def run(self, request):
        self.requests.append(request)
        if not self.results:
            raise AssertionError("sandbox called more times than expected")
        return self.results.pop(0)


def make_session(compiler: LatexWorkspaceCompiler) -> WorkspaceSession:
    return WorkspaceSession(
        WorkspaceSessionModel(
            workspace_id="ws-1",
            task="annotation",
            template_id="default_annotation_tex",
            template_source="\n".join(
                [
                    r"\documentclass{article}",
                    "% DOCWRIGHT:BODY_START",
                    "% DOCWRIGHT:BODY_END",
                ]
            ),
            editable_region=EditableRegion(
                name="body",
                mode="marker_range",
                start_marker="% DOCWRIGHT:BODY_START",
                end_marker="% DOCWRIGHT:BODY_END",
            ),
            current_body="\nfirst draft\n",
        ),
        compiler=compiler,
    )


def test_workspace_session_latex_flow_recovers_from_failure_then_submits() -> None:
    sandbox = SequenceSandbox(
        results=[
            SandboxRunResult(
                backend_name="sequence_sandbox",
                command=("fake-tex", "main.tex"),
                workspace_dir="/tmp/ws-1",
                returncode=1,
                stdout="! Undefined control sequence.\nl.5 \\badcommand",
                stderr="",
            ),
            SandboxRunResult(
                backend_name="sequence_sandbox",
                command=("fake-tex", "main.tex"),
                workspace_dir="/tmp/ws-1",
                returncode=0,
                stdout="compiled",
                stderr="",
            ),
        ]
    )
    compiler = LatexWorkspaceCompiler(
        sandbox=sandbox,
        profile=LatexCompilerProfile(name="fake", command=("fake-tex",), artifact_paths=()),
    )
    session = make_session(compiler)

    failed = session.compile()
    session.patch_body("first", "second")
    compiled = session.compile()
    submitted = session.submit()

    assert failed.ok is False
    assert compiled.ok is True
    assert submitted == compiled
    assert session.model.state is WorkspaceState.SUBMITTED
    assert len(sandbox.requests) == 2
    assert "first draft" in sandbox.requests[0].files[0].content
    assert "second draft" in sandbox.requests[1].files[0].content

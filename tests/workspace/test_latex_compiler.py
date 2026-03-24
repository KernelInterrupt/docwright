from pathlib import Path
from dataclasses import dataclass
from typing import Any

from docwright.workspace.latex import LatexCompilerProfile, LatexWorkspaceCompiler
from docwright.workspace.models import CompileArtifact, EditableRegion, WorkspaceSessionModel
from docwright.workspace.sandbox import LocalProcessSandboxBackend, SandboxArtifact, SandboxRunResult


@dataclass(slots=True)
class FakeSandbox:
    result: SandboxRunResult
    last_request: Any | None = None

    def describe(self) -> dict[str, object]:
        return {"name": "fake_sandbox", "available": True}

    def run(self, request):
        self.last_request = request
        return self.result


def make_workspace() -> WorkspaceSessionModel:
    return WorkspaceSessionModel(
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
        current_body="\nHello annotation.\n",
    )


def test_latex_workspace_compiler_returns_structured_success() -> None:
    sandbox = FakeSandbox(
        result=SandboxRunResult(
            backend_name="fake_sandbox",
            command=("fake-tex", "main.tex"),
            workspace_dir="/tmp/ws",
            returncode=0,
            stdout="compiled",
            stderr="",
            artifacts=(
                SandboxArtifact(path="main.pdf", absolute_path="/tmp/ws/main.pdf", media_type="application/pdf"),
            ),
        )
    )
    compiler = LatexWorkspaceCompiler(
        sandbox=sandbox,
        profile=LatexCompilerProfile(name="fake", command=("fake-tex",), artifact_paths=("main.pdf",)),
    )

    result = compiler.compile(make_workspace())

    assert result.ok is True
    assert result.backend_name == "latex:fake"
    assert "Hello annotation" in result.assembled_source
    assert result.rendered_content == "/tmp/ws/main.pdf"
    assert result.artifacts == (
        CompileArtifact(
            name="main.pdf",
            path="/tmp/ws/main.pdf",
            media_type="application/pdf",
            description="sandbox artifact main.pdf",
        ),
    )
    assert sandbox.last_request.command.argv == ("fake-tex", "main.tex")
    assert "Hello annotation" in sandbox.last_request.files[0].content


def test_latex_workspace_compiler_returns_structured_failure() -> None:
    sandbox = FakeSandbox(
        result=SandboxRunResult(
            backend_name="fake_sandbox",
            command=("fake-tex", "main.tex"),
            workspace_dir="/tmp/ws",
            returncode=1,
            stdout="! Undefined control sequence.\nl.7 \\badcommand",
            stderr="",
        )
    )
    compiler = LatexWorkspaceCompiler(
        sandbox=sandbox,
        profile=LatexCompilerProfile(name="fake", command=("fake-tex",), artifact_paths=()),
    )

    result = compiler.compile(make_workspace())

    assert result.ok is False
    assert result.errors[0].code == "latex.compile_error"
    assert result.errors[0].line == 7
    assert result.errors[0].snippet == "l.7 \\badcommand"


def test_latex_workspace_compiler_describe_exposes_profile_and_sandbox() -> None:
    sandbox = FakeSandbox(
        result=SandboxRunResult(
            backend_name="fake_sandbox",
            command=("fake-tex", "main.tex"),
            workspace_dir="/tmp/ws",
            returncode=0,
            stdout="",
            stderr="",
        )
    )
    compiler = LatexWorkspaceCompiler(
        sandbox=sandbox,
        profile=LatexCompilerProfile(name="fake", command=("fake-tex",), artifact_paths=("main.pdf",)),
    )

    described = compiler.describe()

    assert described.name == "latex_workspace"
    assert described.profile == "fake"
    assert described.sandbox_backend == "fake_sandbox"


def test_latex_workspace_compiler_can_run_through_local_process_sandbox(tmp_path: Path) -> None:
    compiler = LatexWorkspaceCompiler(
        sandbox=LocalProcessSandboxBackend(base_dir=tmp_path),
        profile=LatexCompilerProfile(
            name="python_fake_latex",
            command=(
                "python",
                "-c",
                "from pathlib import Path; Path('main.pdf').write_bytes(b'%PDF-1.4 fake'); Path('main.log').write_text('ok'); print('compiled')",
            ),
            artifact_paths=("main.pdf", "main.log"),
        ),
    )

    result = compiler.compile(make_workspace())

    assert result.ok is True
    assert result.stdout.strip() == "compiled"
    assert any(artifact.path.endswith("main.pdf") for artifact in result.artifacts)

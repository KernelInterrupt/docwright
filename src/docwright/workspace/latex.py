"""Annotation-first LaTeX compiler support for workspace sessions."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from docwright.workspace.compiler import WorkspaceCompilerDescriptor
from docwright.workspace.models import CompileArtifact, CompileError, CompileResult, EditableRegion, WorkspaceSessionModel
from docwright.workspace.sandbox import SandboxBackend, SandboxCommand, SandboxInputFile, SandboxPolicy, SandboxRunRequest, SandboxRunResult
from docwright.workspace.templates import EditableRegionSpec


@dataclass(slots=True, frozen=True)
class LatexCompilerProfile:
    """Concrete LaTeX command profile used by ``LatexWorkspaceCompiler``."""

    name: str
    command: tuple[str, ...]
    main_filename: str = "main.tex"
    artifact_paths: tuple[str, ...] = ("main.pdf", "main.log")
    description: str = ""

    def argv(self) -> tuple[str, ...]:
        return (*self.command, self.main_filename)


DEFAULT_LATEX_COMPILER_PROFILES: dict[str, LatexCompilerProfile] = {
    "tectonic": LatexCompilerProfile(
        name="tectonic",
        command=("tectonic", "--keep-logs", "--keep-intermediates"),
        artifact_paths=("main.pdf", "main.log"),
        description="Compile with Tectonic using one self-contained document entrypoint.",
    ),
    "pdflatex": LatexCompilerProfile(
        name="pdflatex",
        command=("pdflatex", "-interaction=nonstopmode", "-halt-on-error"),
        artifact_paths=("main.pdf", "main.log"),
        description="Compile with pdflatex in nonstop mode and stop on fatal errors.",
    ),
}


class LatexWorkspaceCompiler:
    """Compile annotation-first LaTeX workspaces through a sandbox backend."""

    def __init__(
        self,
        *,
        sandbox: SandboxBackend,
        profile: LatexCompilerProfile | str = "tectonic",
        sandbox_policy: SandboxPolicy | None = None,
    ):
        self._sandbox = sandbox
        self._profile = resolve_latex_profile(profile)
        self._sandbox_policy = sandbox_policy or SandboxPolicy()

    def describe(self) -> WorkspaceCompilerDescriptor:
        sandbox_name = None
        sandbox_available = True
        describe = getattr(self._sandbox, "describe", None)
        if callable(describe):
            info = describe()
            if isinstance(info, dict):
                sandbox_name = str(info.get("name")) if info.get("name") is not None else None
                sandbox_available = bool(info.get("available", True))
        command_name = self._profile.command[0]
        command_path = shutil.which(command_name)
        command_lookup_required = sandbox_name in {None, "local_process", "bubblewrap"}
        return WorkspaceCompilerDescriptor(
            name="latex_workspace",
            profile=self._profile.name,
            sandbox_backend=sandbox_name,
            available=sandbox_available and (command_path is not None or not command_lookup_required),
            details={
                "main_filename": self._profile.main_filename,
                "artifact_paths": list(self._profile.artifact_paths),
                "description": self._profile.description,
                "command": list(self._profile.command),
                "command_name": command_name,
                "command_path": command_path,
                "command_lookup_required": command_lookup_required,
                "sandbox_available": sandbox_available,
            },
        )

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        assembled_source = assemble_latex_source(workspace)
        run_result = self._sandbox.run(
            SandboxRunRequest(
                command=SandboxCommand(argv=self._profile.argv()),
                files=(SandboxInputFile(path=self._profile.main_filename, content=assembled_source),),
                artifact_paths=self._profile.artifact_paths,
                policy=self._sandbox_policy,
            )
        )
        return self._result_from_run(workspace, assembled_source, run_result)

    def _result_from_run(
        self,
        workspace: WorkspaceSessionModel,
        assembled_source: str,
        run_result: SandboxRunResult,
    ) -> CompileResult:
        artifacts = tuple(
            CompileArtifact(
                name=Path(artifact.path).name,
                path=artifact.absolute_path,
                media_type=artifact.media_type,
                description=f"sandbox artifact {artifact.path}",
            )
            for artifact in run_result.artifacts
        )
        primary_output = next((artifact.path for artifact in artifacts if artifact.path.endswith(".pdf")), None)

        if run_result.command_not_found:
            return CompileResult(
                ok=False,
                backend_name=f"latex:{self._profile.name}",
                assembled_source=assembled_source,
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                artifacts=artifacts,
                errors=(
                    CompileError(
                        code="latex.command_not_found",
                        message=f"LaTeX command not found for profile {self._profile.name!r}",
                        terminal=True,
                    ),
                ),
            )
        if run_result.timed_out:
            return CompileResult(
                ok=False,
                backend_name=f"latex:{self._profile.name}",
                assembled_source=assembled_source,
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                artifacts=artifacts,
                errors=(CompileError(code="latex.timeout", message="LaTeX compile timed out", terminal=True),),
            )
        if run_result.returncode != 0:
            return CompileResult(
                ok=False,
                backend_name=f"latex:{self._profile.name}",
                assembled_source=assembled_source,
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                artifacts=artifacts,
                errors=parse_latex_errors(run_result.stdout, run_result.stderr),
            )
        return CompileResult(
            ok=True,
            backend_name=f"latex:{self._profile.name}",
            rendered_content=primary_output,
            assembled_source=assembled_source,
            stdout=run_result.stdout,
            stderr=run_result.stderr,
            artifacts=artifacts,
        )


def resolve_latex_profile(profile: LatexCompilerProfile | str) -> LatexCompilerProfile:
    if isinstance(profile, LatexCompilerProfile):
        return profile
    try:
        return DEFAULT_LATEX_COMPILER_PROFILES[profile]
    except KeyError as exc:
        raise KeyError(f"unknown latex compiler profile: {profile}") from exc


def assemble_latex_source(workspace: WorkspaceSessionModel) -> str:
    template_source = workspace.template_source
    if template_source is None:
        return workspace.current_body
    region = EditableRegionSpec(
        name=workspace.editable_region.name,
        mode=workspace.editable_region.mode,
        start_marker=workspace.editable_region.start_marker,
        end_marker=workspace.editable_region.end_marker,
    )
    return region.render(template_source, workspace.current_body)


def parse_latex_errors(stdout: str, stderr: str) -> tuple[CompileError, ...]:
    combined = "\n".join(part for part in (stdout, stderr) if part)
    errors: list[CompileError] = []

    for block in _error_blocks(combined):
        line_match = re.search(r"l\.(\d+)", block)
        line_number = None if line_match is None else int(line_match.group(1))
        snippet = None
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) >= 2:
            snippet = lines[1].strip()
        message = lines[0].lstrip("! ") if lines else "LaTeX compilation failed"
        errors.append(
            CompileError(
                code="latex.compile_error",
                message=message,
                line=line_number,
                snippet=snippet,
                terminal=True,
            )
        )

    if errors:
        return tuple(errors)
    if combined.strip():
        return (CompileError(code="latex.compile_error", message=combined.strip(), terminal=True),)
    return (CompileError(code="latex.compile_error", message="LaTeX compilation failed", terminal=True),)


def _error_blocks(text: str) -> Iterable[str]:
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("!"):
            if current:
                yield "\n".join(current)
                current = []
            current.append(line)
            continue
        if current:
            current.append(line)
            if re.match(r"^l\.\d+", line.strip()):
                yield "\n".join(current)
                current = []
    if current:
        yield "\n".join(current)

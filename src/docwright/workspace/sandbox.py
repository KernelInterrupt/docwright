"""Sandbox backend contracts for workspace compilation."""

from __future__ import annotations

import mimetypes
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class SandboxPolicy:
    """Execution policy for one sandboxed compiler run."""

    timeout_seconds: float = 20.0
    allow_network: bool = False
    env: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SandboxInputFile:
    """File materialized into the sandbox before a command runs."""

    path: str
    content: str | bytes
    executable: bool = False


@dataclass(slots=True, frozen=True)
class SandboxCommand:
    """Concrete command to run inside a sandbox workspace."""

    argv: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class SandboxArtifact:
    """Artifact collected from a sandbox run."""

    path: str
    absolute_path: str
    media_type: str | None = None
    size_bytes: int | None = None


@dataclass(slots=True, frozen=True)
class SandboxRunRequest:
    """One sandbox execution request."""

    command: SandboxCommand
    files: tuple[SandboxInputFile, ...] = ()
    artifact_paths: tuple[str, ...] = ()
    policy: SandboxPolicy = SandboxPolicy()


@dataclass(slots=True, frozen=True)
class SandboxRunResult:
    """Structured result of one sandbox execution."""

    backend_name: str
    command: tuple[str, ...]
    workspace_dir: str
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    command_not_found: bool = False
    artifacts: tuple[SandboxArtifact, ...] = ()


@runtime_checkable
class SandboxBackend(Protocol):
    """Execution-isolation backend used by workspace compilers."""

    def run(self, request: SandboxRunRequest) -> SandboxRunResult:
        """Materialize files, execute a command, and collect artifacts."""


class LocalProcessSandboxBackend:
    """Simple local-process backend for deterministic workspace compilation."""

    def __init__(self, *, base_dir: str | os.PathLike[str] | None = None):
        self._base_dir = Path(base_dir) if base_dir is not None else None

    def describe(self) -> dict[str, object]:
        return {
            "name": "local_process",
            "base_dir": None if self._base_dir is None else str(self._base_dir),
            "available": True,
        }

    def run(self, request: SandboxRunRequest) -> SandboxRunResult:
        workspace_dir = Path(
            tempfile.mkdtemp(prefix="docwright-sandbox-", dir=None if self._base_dir is None else self._base_dir)
        )
        for sandbox_file in request.files:
            target = workspace_dir / sandbox_file.path
            target.parent.mkdir(parents=True, exist_ok=True)
            content = sandbox_file.content
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
            if sandbox_file.executable:
                target.chmod(target.stat().st_mode | 0o111)

        env = os.environ.copy()
        env.update(request.policy.env)

        try:
            completed = subprocess.run(
                request.command.argv,
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=request.policy.timeout_seconds,
                env=env,
                check=False,
            )
        except FileNotFoundError as exc:
            return SandboxRunResult(
                backend_name="local_process",
                command=request.command.argv,
                workspace_dir=str(workspace_dir),
                returncode=None,
                stdout="",
                stderr=str(exc),
                command_not_found=True,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxRunResult(
                backend_name="local_process",
                command=request.command.argv,
                workspace_dir=str(workspace_dir),
                returncode=None,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                timed_out=True,
            )

        return SandboxRunResult(
            backend_name="local_process",
            command=request.command.argv,
            workspace_dir=str(workspace_dir),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            artifacts=self._collect_artifacts(workspace_dir, request.artifact_paths),
        )

    def _collect_artifacts(self, workspace_dir: Path, artifact_paths: tuple[str, ...]) -> tuple[SandboxArtifact, ...]:
        artifacts: list[SandboxArtifact] = []
        for relative_path in artifact_paths:
            path = workspace_dir / relative_path
            if not path.exists():
                continue
            media_type, _ = mimetypes.guess_type(path.name)
            artifacts.append(
                SandboxArtifact(
                    path=relative_path,
                    absolute_path=str(path),
                    media_type=media_type,
                    size_bytes=path.stat().st_size,
                )
            )
        return tuple(artifacts)

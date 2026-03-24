"""Sandbox backend contracts for workspace compilation."""

from __future__ import annotations

import mimetypes
import os
import shutil
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
            "isolation_level": "local_process",
            "base_dir": None if self._base_dir is None else str(self._base_dir),
            "available": True,
        }

    def run(self, request: SandboxRunRequest) -> SandboxRunResult:
        workspace_dir = _materialize_workspace(request.files, base_dir=self._base_dir)
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
            artifacts=_collect_artifacts(workspace_dir, request.artifact_paths),
        )


class BubblewrapSandboxBackend:
    """Strongly constrained sandbox backend powered by bubblewrap.

    This backend aims to prevent access to ambient host directories by exposing
    only an isolated writable workspace root plus a small read-only set of
    runtime/toolchain directories.
    """

    DEFAULT_RO_BIND_ROOTS = (
        "/usr",
        "/bin",
        "/lib",
        "/lib64",
        "/sbin",
        "/etc",
        "/opt",
    )

    def __init__(
        self,
        *,
        bwrap_executable: str = "bwrap",
        base_dir: str | os.PathLike[str] | None = None,
        ro_bind_roots: tuple[str, ...] | None = None,
    ):
        self._bwrap_executable = bwrap_executable
        self._base_dir = Path(base_dir) if base_dir is not None else None
        self._ro_bind_roots = tuple(
            root for root in (self.DEFAULT_RO_BIND_ROOTS if ro_bind_roots is None else ro_bind_roots) if Path(root).exists()
        )

    def describe(self) -> dict[str, object]:
        return {
            "name": "bubblewrap",
            "isolation_level": "strong",
            "available": shutil.which(self._bwrap_executable) is not None,
            "bwrap_executable": self._bwrap_executable,
            "ro_bind_roots": list(self._ro_bind_roots),
            "network_default": "disabled",
        }

    def run(self, request: SandboxRunRequest) -> SandboxRunResult:
        workspace_dir = _materialize_workspace(request.files, base_dir=self._base_dir)
        bwrap_path = shutil.which(self._bwrap_executable)
        if bwrap_path is None:
            return SandboxRunResult(
                backend_name="bubblewrap",
                command=request.command.argv,
                workspace_dir=str(workspace_dir),
                returncode=None,
                stdout="",
                stderr=f"bubblewrap executable not found: {self._bwrap_executable}",
                command_not_found=True,
            )

        command = self._build_bwrap_command(bwrap_path, workspace_dir, request)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=request.policy.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxRunResult(
                backend_name="bubblewrap",
                command=request.command.argv,
                workspace_dir=str(workspace_dir),
                returncode=None,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                timed_out=True,
            )

        stderr_text = completed.stderr.lower()
        return SandboxRunResult(
            backend_name="bubblewrap",
            command=request.command.argv,
            workspace_dir=str(workspace_dir),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            artifacts=_collect_artifacts(workspace_dir, request.artifact_paths),
            command_not_found=(completed.returncode in {1, 127} and "no such file or directory" in stderr_text),
        )

    def _build_bwrap_command(
        self,
        bwrap_path: str,
        workspace_dir: Path,
        request: SandboxRunRequest,
    ) -> list[str]:
        command = [
            bwrap_path,
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/var",
            "--tmpfs",
            "/run",
            "--dir",
            "/workspace",
            "--bind",
            str(workspace_dir),
            "/workspace",
            "--chdir",
            "/workspace",
            "--setenv",
            "PATH",
            "/usr/bin:/bin:/usr/sbin:/sbin",
        ]
        if request.policy.allow_network:
            command.append("--share-net")
        for root in self._ro_bind_roots:
            command.extend(["--ro-bind", root, root])
        for key, value in sorted(request.policy.env.items()):
            command.extend(["--setenv", key, value])
        command.append("--")
        command.extend(request.command.argv)
        return command


def _materialize_workspace(
    files: tuple[SandboxInputFile, ...],
    *,
    base_dir: Path | None,
) -> Path:
    workspace_dir = Path(tempfile.mkdtemp(prefix="docwright-sandbox-", dir=None if base_dir is None else base_dir))
    for sandbox_file in files:
        target = _resolve_workspace_path(workspace_dir, sandbox_file.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = sandbox_file.content
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        if sandbox_file.executable:
            target.chmod(target.stat().st_mode | 0o111)
    return workspace_dir


def _collect_artifacts(workspace_dir: Path, artifact_paths: tuple[str, ...]) -> tuple[SandboxArtifact, ...]:
    artifacts: list[SandboxArtifact] = []
    for relative_path in artifact_paths:
        try:
            path = _resolve_workspace_path(workspace_dir, relative_path)
        except ValueError:
            continue
        if not path.exists():
            continue
        if path.is_symlink():
            resolved = path.resolve()
            try:
                resolved.relative_to(workspace_dir.resolve())
            except ValueError:
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


def _resolve_workspace_path(workspace_dir: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"sandbox path must be relative: {relative_path}")
    resolved = (workspace_dir / candidate).resolve()
    try:
        resolved.relative_to(workspace_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"sandbox path escapes workspace root: {relative_path}") from exc
    return resolved

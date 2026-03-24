"""Compiler boundary for workspace sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from docwright.workspace.models import CompileResult, WorkspaceSessionModel


@runtime_checkable
class WorkspaceCompiler(Protocol):
    """Backend interface for validating/rendering workspace content."""

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        """Compile the current workspace content into a structured result."""


@dataclass(slots=True, frozen=True)
class WorkspaceCompilerDescriptor:
    """Host-visible description of a concrete workspace compiler backend."""

    name: str
    profile: str | None = None
    sandbox_backend: str | None = None
    available: bool = True
    details: dict[str, Any] | None = None


def describe_workspace_compiler(compiler: WorkspaceCompiler | None) -> dict[str, Any] | None:
    """Return host-visible compiler metadata when a backend is configured."""

    if compiler is None:
        return None
    describe = getattr(compiler, 'describe', None)
    if callable(describe):
        descriptor = describe()
        if isinstance(descriptor, WorkspaceCompilerDescriptor):
            return {
                'name': descriptor.name,
                'profile': descriptor.profile,
                'sandbox_backend': descriptor.sandbox_backend,
                'available': descriptor.available,
                'details': {} if descriptor.details is None else dict(descriptor.details),
            }
        if isinstance(descriptor, dict):
            return dict(descriptor)
    return {
        'name': compiler.__class__.__name__,
        'profile': None,
        'sandbox_backend': None,
        'available': True,
        'details': {},
    }

"""Compiler boundary for workspace sessions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from docwright.workspace.models import CompileResult, WorkspaceSessionModel


@runtime_checkable
class WorkspaceCompiler(Protocol):
    """Backend interface for validating/rendering workspace content."""

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        """Compile the current workspace content into a structured result."""

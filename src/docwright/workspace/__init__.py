"""Workspace session layer for DocWright Core."""

from docwright.workspace.models import CompileError, CompileResult, EditableRegion, WorkspaceSessionModel, WorkspaceState
from docwright.workspace.profiles import WorkspaceProfile
from docwright.workspace.registry import WorkspaceProfileRegistry, WorkspaceRegistryError
from docwright.workspace.templates import EditableRegionSpec, WorkspaceTemplate

__all__ = [
    "CompileError",
    "CompileResult",
    "EditableRegion",
    "EditableRegionSpec",
    "WorkspaceProfile",
    "WorkspaceProfileRegistry",
    "WorkspaceRegistryError",
    "WorkspaceSessionModel",
    "WorkspaceState",
    "WorkspaceTemplate",
]

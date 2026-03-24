"""Workspace session layer for DocWright Core."""

from docwright.workspace.models import CompileArtifact, CompileError, CompileResult, EditableRegion, WorkspaceSessionModel, WorkspaceState
from docwright.workspace.profiles import WorkspaceProfile
from docwright.workspace.registry import WorkspaceProfileRegistry, WorkspaceRegistryError
from docwright.workspace.templates import EditableRegionSpec, WorkspaceTemplate
from docwright.workspace.builtins import (
    DEFAULT_LATEX_ANNOTATION_PROFILE,
    DEFAULT_LATEX_ANNOTATION_TEMPLATE,
    build_default_workspace_registry,
    build_local_latex_workspace_compiler,
)
from docwright.workspace.latex import LatexCompilerProfile, LatexWorkspaceCompiler
from docwright.workspace.sandbox import LocalProcessSandboxBackend, SandboxCommand, SandboxInputFile, SandboxPolicy, SandboxRunRequest, SandboxRunResult

__all__ = [
    "CompileArtifact",
    "build_local_latex_workspace_compiler",
    "build_default_workspace_registry",
    "DEFAULT_LATEX_ANNOTATION_TEMPLATE",
    "DEFAULT_LATEX_ANNOTATION_PROFILE",
    "CompileError",
    "CompileResult",
    "EditableRegion",
    "EditableRegionSpec",
    "WorkspaceProfile",
    "WorkspaceProfileRegistry",
    "WorkspaceRegistryError",
    "WorkspaceSessionModel",
    "WorkspaceState",
    "LatexCompilerProfile",
    "LatexWorkspaceCompiler",
    "LocalProcessSandboxBackend",
    "SandboxCommand",
    "SandboxInputFile",
    "SandboxPolicy",
    "SandboxRunRequest",
    "SandboxRunResult",
    "WorkspaceTemplate",
]

"""Built-in annotation-first workspace assets."""

from __future__ import annotations

from pathlib import Path

from docwright.workspace.latex import LatexWorkspaceCompiler
from docwright.workspace.profiles import WorkspaceProfile
from docwright.workspace.registry import WorkspaceProfileRegistry
from docwright.workspace.sandbox import BubblewrapSandboxBackend, LocalProcessSandboxBackend, SandboxPolicy
from docwright.workspace.templates import EditableRegionSpec, WorkspaceTemplate

DOCWRIGHT_BODY_START = "% DOCWRIGHT:BODY_START"
DOCWRIGHT_BODY_END = "% DOCWRIGHT:BODY_END"

DEFAULT_LATEX_ANNOTATION_TEMPLATE = WorkspaceTemplate(
    template_id="default_annotation_tex",
    task="annotation",
    body_kind="latex_body",
    source="\n".join(
        [
            r"\documentclass{article}",
            r"\usepackage[margin=1in]{geometry}",
            r"\usepackage{hyperref}",
            r"\begin{document}",
            DOCWRIGHT_BODY_START,
            DOCWRIGHT_BODY_END,
            r"\end{document}",
        ]
    ),
    editable_regions=(
        EditableRegionSpec(
            name="body",
            mode="marker_range",
            start_marker=DOCWRIGHT_BODY_START,
            end_marker=DOCWRIGHT_BODY_END,
        ),
    ),
    compiler_profile="tectonic",
)

DEFAULT_LATEX_ANNOTATION_PROFILE = WorkspaceProfile(
    profile_name="latex_annotation",
    task="annotation",
    template_id=DEFAULT_LATEX_ANNOTATION_TEMPLATE.template_id,
    body_kind="latex_body",
    compiler_profile="tectonic",
    sandbox_profile="local_process",
    locked_sections=("preamble", "document_structure"),
    model_summary=(
        "Edit only the annotation body between the DocWright body markers; keep the LaTeX shell locked."
    ),
)


def build_default_workspace_registry() -> WorkspaceProfileRegistry:
    """Return the built-in annotation-first workspace registry."""

    registry = WorkspaceProfileRegistry()
    registry.register_template(DEFAULT_LATEX_ANNOTATION_TEMPLATE)
    registry.register_profile(DEFAULT_LATEX_ANNOTATION_PROFILE)
    return registry


def build_local_latex_workspace_compiler(
    *,
    profile: str = "tectonic",
    base_dir: str | None = None,
    sandbox_policy: SandboxPolicy | None = None,
) -> LatexWorkspaceCompiler:
    """Create a local-process LaTeX workspace compiler for development/integration."""

    return LatexWorkspaceCompiler(
        sandbox=LocalProcessSandboxBackend(base_dir=Path(base_dir) if base_dir is not None else None),
        profile=profile,
        sandbox_policy=sandbox_policy,
    )


def build_bubblewrap_latex_workspace_compiler(
    *,
    profile: str = "tectonic",
    base_dir: str | None = None,
    sandbox_policy: SandboxPolicy | None = None,
) -> LatexWorkspaceCompiler:
    """Create a bubblewrap-backed LaTeX workspace compiler for stronger isolation."""

    return LatexWorkspaceCompiler(
        sandbox=BubblewrapSandboxBackend(base_dir=Path(base_dir) if base_dir is not None else None),
        profile=profile,
        sandbox_policy=sandbox_policy,
    )

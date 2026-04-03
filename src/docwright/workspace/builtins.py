"""Built-in annotation-first workspace assets."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil

from docwright.workspace.latex import DEFAULT_LATEX_COMPILER_PROFILES, LatexWorkspaceCompiler
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
    sandbox_profile="bubblewrap",
    locked_sections=("preamble", "document_structure"),
    model_summary=(
        "Edit only the annotation body between the DocWright body markers; keep the LaTeX shell locked."
    ),
)


def select_default_latex_compiler_profile(
    preferred_profiles: tuple[str, ...] = ("tectonic", "pdflatex"),
) -> str | None:
    """Return the first installed LaTeX compiler profile from the preferred list."""

    for profile_name in preferred_profiles:
        profile = DEFAULT_LATEX_COMPILER_PROFILES.get(profile_name)
        if profile is None:
            continue
        if shutil.which(profile.command[0]) is not None:
            return profile_name
    return None


def select_default_workspace_sandbox_profile() -> str:
    """Return the preferred built-in sandbox profile for workspace compilation."""

    return "bubblewrap" if shutil.which("bwrap") is not None else "local_process"


def build_default_workspace_registry(
    *,
    compiler_profile: str | None = "tectonic",
    sandbox_profile: str | None = "bubblewrap",
) -> WorkspaceProfileRegistry:
    """Return the built-in annotation-first workspace registry."""

    registry = WorkspaceProfileRegistry()
    registry.register_template(
        replace(
            DEFAULT_LATEX_ANNOTATION_TEMPLATE,
            compiler_profile=compiler_profile,
        )
    )
    registry.register_profile(
        replace(
            DEFAULT_LATEX_ANNOTATION_PROFILE,
            compiler_profile=compiler_profile,
            sandbox_profile=sandbox_profile,
        )
    )
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


def build_default_latex_workspace_compiler(
    *,
    profile: str | None = None,
    base_dir: str | None = None,
    sandbox_policy: SandboxPolicy | None = None,
) -> LatexWorkspaceCompiler:
    """Create the preferred built-in LaTeX compiler.

    Current priority:
    1. bubblewrap-backed strong sandbox when `bwrap` is available
    2. local-process fallback otherwise
    """

    resolved_profile = profile or select_default_latex_compiler_profile()
    if resolved_profile is None:
        resolved_profile = "tectonic"

    if shutil.which("bwrap") is not None:
        return build_bubblewrap_latex_workspace_compiler(
            profile=resolved_profile,
            base_dir=base_dir,
            sandbox_policy=sandbox_policy,
        )
    return build_local_latex_workspace_compiler(
        profile=resolved_profile,
        base_dir=base_dir,
        sandbox_policy=sandbox_policy,
    )

"""Declarative workspace profile contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class WorkspaceProfile:
    """Declarative description of a workspace configuration."""

    profile_name: str
    task: str
    template_id: str
    body_kind: str
    compile_required_before_submit: bool = True
    patch_scope: str = "editable_region_only"
    locked_sections: tuple[str, ...] = ()
    model_summary: str = ""
    compiler_profile: str | None = None
    sandbox_profile: str | None = None

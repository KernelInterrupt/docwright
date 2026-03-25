"""Reference workspace-editing skill bundle."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.skills.base import SkillBundle, SkillDescriptor


@dataclass(slots=True)
class WorkspaceEditingSkill(SkillBundle):
    """Reusable controlled workspace-editing ability package."""

    descriptor: SkillDescriptor = field(
        default_factory=lambda: SkillDescriptor(
            name="workspace_editing",
            description="Open and edit controlled workspace sessions.",
        )
    )

    def tool_names(self) -> tuple[str, ...]:
        return ("open_workspace", "describe_workspace", "read_source", "read_body", "write_body", "patch_body", "compile", "submit")

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "open_workspace": "Open a controlled editing workspace anchored to the current node and return its workspace_id.",
            "describe_workspace": "Return workspace rules, readiness, editable-region metadata, and the current workspace_id.",
            "read_source": "Read the assembled workspace source, including the locked template shell around the editable region.",
            "read_body": "Read only the editable workspace body before making changes.",
            "write_body": "Replace the editable workspace body with new content that stays inside the allowed editable region.",
            "patch_body": "Apply one targeted string replacement inside the editable workspace body only.",
            "compile": "Compile the current workspace body and return structured success or error details plus the workspace_id.",
            "submit": "Submit the workspace only after the workspace is ready for submission.",
        }

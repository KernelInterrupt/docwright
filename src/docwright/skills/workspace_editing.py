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
        return ("open_workspace", "describe_workspace", "read_body", "write_body", "patch_body", "compile", "submit")

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "open_workspace": "Open a controlled editing workspace anchored to the current node.",
            "describe_workspace": "Return the workspace rules, readiness, and editable-region metadata.",
            "read_body": "Read the editable workspace body before making changes.",
            "write_body": "Replace the editable workspace body with new content.",
            "patch_body": "Apply a targeted string replacement inside the editable workspace body.",
            "compile": "Compile the workspace body and return structured success or error details.",
            "submit": "Submit the workspace after a successful compile completes.",
        }

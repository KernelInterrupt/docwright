"""Reference warning skill bundle."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.skills.base import SkillBundle, SkillDescriptor


@dataclass(slots=True)
class WarningSkill(SkillBundle):
    """Reusable warning-emission ability package."""

    descriptor: SkillDescriptor = field(
        default_factory=lambda: SkillDescriptor(
            name="warnings",
            description="Raise structured warnings on the current node.",
        )
    )

    def tool_names(self) -> tuple[str, ...]:
        return ("warning",)

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "warning": "Raise a structured warning on the current node with severity, message, and supporting evidence node IDs or snippets.",
        }

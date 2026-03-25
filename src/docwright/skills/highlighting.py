"""Reference highlighting skill bundle."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.skills.base import SkillBundle, SkillDescriptor


@dataclass(slots=True)
class HighlightingSkill(SkillBundle):
    """Reusable highlighting ability package."""

    descriptor: SkillDescriptor = field(
        default_factory=lambda: SkillDescriptor(
            name="highlighting",
            description="Highlight the current document node.",
        )
    )

    def tool_names(self) -> tuple[str, ...]:
        return ("highlight",)

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "highlight": "Mark the current node with a structured highlight level and optional reason before advancing when the active capability requires it.",
        }

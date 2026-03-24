"""Reference navigation skill bundle."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.skills.base import SkillBundle, SkillDescriptor


@dataclass(slots=True)
class NavigationSkill(SkillBundle):
    """Reusable navigation/query ability package."""

    descriptor: SkillDescriptor = field(
        default_factory=lambda: SkillDescriptor(
            name="navigation",
            description="Query current context and advance through the document.",
        )
    )

    def tool_names(self) -> tuple[str, ...]:
        return ("current_node", "get_context", "search_text", "advance")

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "current_node": "Inspect the current DocWright node before taking any action.",
            "get_context": "Read nearby node IDs around the current node to understand local context.",
            "search_text": "Search runtime-visible document text by keyword before navigating manually.",
            "advance": "Move to the next node in reading order after satisfying runtime guardrails.",
        }

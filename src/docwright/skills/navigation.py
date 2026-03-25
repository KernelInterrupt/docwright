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
            description="Query current context, inspect structure, search, jump, and advance through the document.",
        )
    )

    def tool_names(self) -> tuple[str, ...]:
        return (
            "current_node",
            "get_context",
            "search_text",
            "advance",
            "get_structure",
            "search_headings",
            "jump_to_node",
            "list_internal_links",
            "follow_internal_link",
        )

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "current_node": "Inspect the current DocWright node. This is usually the first call in each step.",
            "get_context": "Read nearby reading-order node IDs around the current node for local context.",
            "search_text": "Search runtime-visible document text by keyword, optionally within a narrower scope or selected node kinds.",
            "advance": "Move to the next node in reading order only after the current step is complete and runtime guardrails are satisfied.",
            "get_structure": "Inspect parent/children/siblings/ancestry metadata for the current node without changing runtime focus.",
            "search_headings": "Search structural heading/section nodes when the task is to locate a relevant part of the document rather than scan sequentially.",
            "jump_to_node": "Reposition runtime focus to a target node or section so later reads/searches continue from there.",
            "list_internal_links": "List outgoing internal PDF-style links from the current node when the IR preserved hyperlink relations.",
            "follow_internal_link": "Follow one preserved internal-link relation and update runtime focus to the resolved target node.",
        }

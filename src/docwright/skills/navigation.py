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
            description="Query explicit nodes, inspect structure, search, follow relations, and use compatibility navigation helpers when needed.",
        )
    )

    def tool_names(self) -> tuple[str, ...]:
        return (
            "get_node",
            "get_context",
            "search_text",
            "get_structure",
            "search_headings",
            "jump_to_node",
            "list_internal_links",
            "follow_internal_link",
            "current_node",
            "advance",
        )

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "get_node": "Resolve an explicit DocWright node by stable node_id and return its node reference payload.",
            "current_node": "Inspect the legacy current DocWright node compatibility cursor when older flows still depend on it.",
            "get_context": "Read nearby reading-order node IDs around an explicit node or the legacy current node for local context.",
            "search_text": "Search runtime-visible document text by keyword, optionally within a narrower scope or selected node kinds.",
            "advance": "Legacy sequential-reading helper that moves to the next node in reading order after runtime guardrails are satisfied.",
            "get_structure": "Inspect parent/children/siblings/ancestry metadata for an explicit node or the legacy current node.",
            "search_headings": "Search structural heading/section nodes when the task is to locate a relevant part of the document rather than scan sequentially.",
            "jump_to_node": "Compatibility helper that repositions the legacy runtime focus to a target node or section.",
            "list_internal_links": "List outgoing internal PDF-style links from an explicit node or the legacy current node when the IR preserved hyperlink relations.",
            "follow_internal_link": "Follow one preserved internal-link relation and return the resolved target node, updating legacy focus only for compatibility.",
        }

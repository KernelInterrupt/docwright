"""Guided-reading capability profile."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources

from docwright.capabilities.base import CapabilityDescriptor, CapabilityProfile
from docwright.core.guardrails import RuntimeGuardrailPolicy
from docwright.skills.base import SkillBundle
from docwright.skills.highlighting import HighlightingSkill
from docwright.skills.navigation import NavigationSkill
from docwright.skills.warnings import WarningSkill
from docwright.skills.workspace_editing import WorkspaceEditingSkill


GUIDED_READING_NAME = "guided_reading"
GUIDED_READING_STRATEGY_RESOURCE = "guided_reading_strategy.md"


def load_guided_reading_strategy() -> str:
    """Load guided-reading strategy text from capability resources."""

    return resources.files("docwright.capabilities.resources").joinpath(
        GUIDED_READING_STRATEGY_RESOURCE
    ).read_text(encoding="utf-8")


@dataclass(slots=True)
class GuidedReadingCapability(CapabilityProfile):
    """First concrete capability profile hosted by DocWright Core."""

    skills: tuple[SkillBundle, ...] = field(
        default_factory=lambda: (
            NavigationSkill(),
            HighlightingSkill(),
            WarningSkill(),
            WorkspaceEditingSkill(),
        )
    )
    descriptor: CapabilityDescriptor = field(
        default_factory=lambda: CapabilityDescriptor(
            name=GUIDED_READING_NAME,
            description="Guided document-reading strategy over explicit node targets.",
            metadata={"mode": "guided_reading"},
        )
    )

    def guardrail_policy(self) -> RuntimeGuardrailPolicy:
        return RuntimeGuardrailPolicy(
            require_highlight_before_advance=True,
            max_workspaces_per_step=1,
        )

    def skill_bundles(self) -> tuple[SkillBundle, ...]:
        return self.skills

"""Manual-task capability profile."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.capabilities.base import CapabilityDescriptor, CapabilityProfile
from docwright.core.guardrails import RuntimeGuardrailPolicy
from docwright.skills.base import SkillBundle
from docwright.skills.highlighting import HighlightingSkill
from docwright.skills.navigation import NavigationSkill
from docwright.skills.warnings import WarningSkill
from docwright.skills.workspace_editing import WorkspaceEditingSkill


MANUAL_TASK_NAME = "manual_task"


@dataclass(slots=True)
class ManualTaskCapability(CapabilityProfile):
    """Capability profile for manual, less constrained document tasks."""

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
            name=MANUAL_TASK_NAME,
            description="Manual node-targeted document task mode with relaxed runtime guardrails.",
            metadata={"mode": "manual_task"},
        )
    )

    def guardrail_policy(self) -> RuntimeGuardrailPolicy:
        return RuntimeGuardrailPolicy(
            require_highlight_before_advance=False,
            max_workspaces_per_step=1,
        )

    def skill_bundles(self) -> tuple[SkillBundle, ...]:
        return self.skills

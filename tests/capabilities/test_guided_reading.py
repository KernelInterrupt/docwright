from dataclasses import dataclass

from docwright.capabilities.guided_reading import (
    GUIDED_READING_NAME,
    GuidedReadingCapability,
    load_guided_reading_strategy,
)
from docwright.skills.base import SkillDescriptor


@dataclass(slots=True)
class FakeSkill:
    descriptor: SkillDescriptor

    def tool_names(self) -> tuple[str, ...]:
        return ("highlight",)

    def tool_descriptions(self) -> dict[str, str]:
        return {"highlight": "Mark the current node."}


def test_guided_reading_capability_sets_runtime_guardrails() -> None:
    capability = GuidedReadingCapability()
    policy = capability.guardrail_policy()

    assert capability.descriptor.name == GUIDED_READING_NAME
    assert policy.require_highlight_before_advance is True
    assert policy.max_workspaces_per_step == 1


def test_guided_reading_capability_provides_reference_skill_bundles_by_default() -> None:
    capability = GuidedReadingCapability()

    assert [skill.descriptor.name for skill in capability.skill_bundles()] == [
        "navigation",
        "highlighting",
        "warnings",
        "workspace_editing",
    ]


def test_guided_reading_capability_keeps_skill_bundles_overridable() -> None:
    skill = FakeSkill(descriptor=SkillDescriptor(name="highlighting"))
    capability = GuidedReadingCapability(skills=(skill,))

    assert capability.skill_bundles() == (skill,)


def test_guided_reading_strategy_text_lives_in_capability_resources() -> None:
    strategy_text = load_guided_reading_strategy()

    assert "highlight before advancing" in strategy_text.lower()
    assert "one workspace per step" in strategy_text.lower()

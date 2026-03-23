from dataclasses import dataclass, field

from docwright.capabilities.base import CapabilityDescriptor, CapabilityProfile
from docwright.core.guardrails import RuntimeGuardrailPolicy
from docwright.skills.base import SkillBundle, SkillDescriptor


@dataclass(slots=True)
class FakeSkill:
    descriptor: SkillDescriptor

    def tool_names(self) -> tuple[str, ...]:
        return ("highlight",)

    def tool_descriptions(self) -> dict[str, str]:
        return {"highlight": "Mark the current node."}


@dataclass(slots=True)
class FakeCapability:
    descriptor: CapabilityDescriptor
    skills: tuple[FakeSkill, ...] = field(default_factory=tuple)

    def guardrail_policy(self) -> RuntimeGuardrailPolicy:
        return RuntimeGuardrailPolicy(require_highlight_before_advance=True)

    def skill_bundles(self) -> tuple[SkillBundle, ...]:
        return self.skills


def test_capability_descriptor_tracks_task_mode_metadata() -> None:
    descriptor = CapabilityDescriptor(
        name="guided_reading",
        description="Structured reading mode",
        metadata={"requires_highlight_before_advance": True},
    )

    assert descriptor.name == "guided_reading"
    assert descriptor.description == "Structured reading mode"
    assert descriptor.metadata == {"requires_highlight_before_advance": True}


def test_capability_profile_protocol_selects_policy_and_skills() -> None:
    capability = FakeCapability(
        descriptor=CapabilityDescriptor(name="guided_reading"),
        skills=(FakeSkill(descriptor=SkillDescriptor(name="highlighting")),),
    )

    assert isinstance(capability, CapabilityProfile)
    assert capability.guardrail_policy().require_highlight_before_advance is True
    assert capability.skill_bundles() == capability.skills

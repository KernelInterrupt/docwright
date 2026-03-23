from dataclasses import dataclass

from docwright.skills.base import SkillBundle, SkillDescriptor


@dataclass(slots=True)
class FakeSkill:
    descriptor: SkillDescriptor

    def tool_names(self) -> tuple[str, ...]:
        return ("highlight", "warning")

    def tool_descriptions(self) -> dict[str, str]:
        return {
            "highlight": "Mark the current node.",
            "warning": "Raise a warning.",
        }


def test_skill_descriptor_tracks_reusable_bundle_metadata() -> None:
    descriptor = SkillDescriptor(
        name="workspace_editing",
        description="Controlled editing operations",
        metadata={"supports_patch": True},
    )

    assert descriptor.name == "workspace_editing"
    assert descriptor.description == "Controlled editing operations"
    assert descriptor.metadata == {"supports_patch": True}


def test_skill_bundle_protocol_exposes_tool_names_and_descriptions() -> None:
    skill = FakeSkill(descriptor=SkillDescriptor(name="highlighting"))

    assert isinstance(skill, SkillBundle)
    assert skill.tool_names() == ("highlight", "warning")
    assert skill.tool_descriptions() == {
        "highlight": "Mark the current node.",
        "warning": "Raise a warning.",
    }

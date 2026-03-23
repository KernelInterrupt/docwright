"""Skill / tool-bundle boundary primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class SkillDescriptor:
    """Describes a reusable ability package."""

    name: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SkillBundle(Protocol):
    """Reusable skill/tool bundle interface."""

    @property
    def descriptor(self) -> SkillDescriptor:
        """Static description of the bundle."""

    def tool_names(self) -> tuple[str, ...]:
        """Return the tool/action names exposed by this bundle."""

    def tool_descriptions(self) -> dict[str, str]:
        """Return optional tool-specific descriptions for exported runtimes."""

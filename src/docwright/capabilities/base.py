"""Capability-profile boundary primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from docwright.core.guardrails import RuntimeGuardrailPolicy

if TYPE_CHECKING:
    from docwright.skills.base import SkillBundle


@dataclass(slots=True, frozen=True)
class CapabilityDescriptor:
    """Describes a task-mode selection without embedding runtime glue."""

    name: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class CapabilityProfile(Protocol):
    """Core-facing capability profile interface."""

    @property
    def descriptor(self) -> CapabilityDescriptor:
        """Static description of the task mode."""

    def guardrail_policy(self) -> RuntimeGuardrailPolicy:
        """Return the runtime rules activated by this capability."""

    def skill_bundles(self) -> tuple[SkillBundle, ...]:
        """Return reusable skill bundles exposed by this capability."""

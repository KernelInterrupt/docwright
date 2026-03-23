"""Agent-adapter boundary primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession


@dataclass(slots=True, frozen=True)
class AdapterDescriptor:
    """Describes an external runtime integration without embedding policy."""

    name: str
    transport: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AgentAdapter(Protocol):
    """Core-facing agent adapter interface."""

    @property
    def descriptor(self) -> AdapterDescriptor:
        """Static description of the adapter runtime surface."""

    async def run_step(
        self,
        session: RuntimeSession,
        capability: CapabilityProfile | None = None,
    ) -> None:
        """Execute a single adapter-driven step against a Core runtime session."""

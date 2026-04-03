"""Host-local companion boundary.

This module is intentionally separate from Core runtime/session logic. A local
companion may decide how to boot a host environment, but it must not become the
central runtime loop or a required Core dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class CompanionLaunchPlan:
    """Host-local launch/orchestration plan outside the Core runtime."""

    runtime_name: str
    command: tuple[str, ...] = ()
    working_directory: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class CompanionRuntime(Protocol):
    """Optional host-local companion contract.

    Implementations may launch, supervise, or coordinate a local host runtime,
    but they should only return host-local state and plans. They must not own
    DocWright Core session progression.
    """

    def build_launch_plan(self) -> CompanionLaunchPlan:
        """Return the host-local launch plan for the companion runtime."""

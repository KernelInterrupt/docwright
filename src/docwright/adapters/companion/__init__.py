"""Host-local companion/orchestration helpers.

These helpers live outside Core runtime state and outside transport-neutral
adapter contracts. They exist only for host-side launch/orchestration concerns.
"""

from docwright.adapters.companion.base import CompanionLaunchPlan, CompanionRuntime

__all__ = ["CompanionLaunchPlan", "CompanionRuntime"]

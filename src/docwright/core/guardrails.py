"""Runtime permission and guardrail models."""

from __future__ import annotations

from dataclasses import dataclass, field
from docwright._compat import StrEnum
from typing import Any


class GuardrailCode(StrEnum):
    """Stable identifiers for runtime guardrail failures."""

    ACTION_NOT_PERMITTED = "action_not_permitted"
    HIGHLIGHT_REQUIRED_BEFORE_ADVANCE = "highlight_required_before_advance"
    WORKSPACE_LIMIT_REACHED = "workspace_limit_reached"


@dataclass(slots=True, frozen=True)
class GuardrailViolation:
    """Structured description of a rejected runtime action."""

    code: GuardrailCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class GuardrailViolationError(RuntimeError):
    """Exception wrapper for a structured guardrail violation."""

    def __init__(self, violation: GuardrailViolation):
        super().__init__(violation.message)
        self.violation = violation


@dataclass(slots=True, frozen=True)
class RuntimePermissions:
    """Action-level permissions available to a runtime session."""

    allow_highlight: bool = True
    allow_warning: bool = True
    allow_open_workspace: bool = True
    allow_advance: bool = True

    def ensure_allowed(self, action: str) -> None:
        allowed = {
            "highlight": self.allow_highlight,
            "warning": self.allow_warning,
            "open_workspace": self.allow_open_workspace,
            "advance": self.allow_advance,
        }.get(action)
        if allowed is False:
            raise GuardrailViolationError(
                GuardrailViolation(
                    code=GuardrailCode.ACTION_NOT_PERMITTED,
                    message=f"action '{action}' is not permitted",
                    details={"action": action},
                )
            )


@dataclass(slots=True, frozen=True)
class RuntimeGuardrailPolicy:
    """Capability-selectable runtime rules enforced by Core."""

    require_highlight_before_advance: bool = False
    max_workspaces_per_step: int | None = None

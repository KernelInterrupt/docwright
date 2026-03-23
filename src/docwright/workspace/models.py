"""Workspace-layer state containers.

The workspace subsystem owns controlled editing-session state. This module keeps
that state separate from Core runtime state so workspace evolution does not leak
into adapters, capabilities, or document interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from docwright._compat import StrEnum
from typing import Any


class WorkspaceState(StrEnum):
    """Lifecycle states for a workspace session."""

    INITIALIZED = "initialized"
    EDITING = "editing"
    COMPILED = "compiled"
    COMPILE_FAILED = "compile_failed"
    SUBMITTED = "submitted"


@dataclass(slots=True, frozen=True)
class CompileError:
    """Structured compile-time error surfaced by a workspace backend."""

    code: str
    message: str
    line: int | None = None
    snippet: str | None = None
    terminal: bool = False


@dataclass(slots=True, frozen=True)
class CompileResult:
    """Structured result of a workspace compilation attempt."""

    ok: bool
    backend_name: str
    rendered_content: str | None = None
    errors: tuple[CompileError, ...] = ()


@dataclass(slots=True, frozen=True)
class EditableRegion:
    """Describes the portion of the workspace that may be mutated."""

    name: str = "body"
    start_marker: str | None = None
    end_marker: str | None = None


@dataclass(slots=True, frozen=True)
class WorkspaceHistoryEntry:
    """Immutable audit entry for a workspace action."""

    action: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkspaceSessionModel:
    """Serializable workspace session state.

    The workspace model stays owned by the workspace layer, while Core keeps
    only runtime/session state. Later checklist items add lifecycle guardrails
    and richer mutation semantics.
    """

    workspace_id: str
    task: str
    capability_name: str | None = None
    state: WorkspaceState = WorkspaceState.INITIALIZED
    editable_region: EditableRegion = field(default_factory=EditableRegion)
    current_body: str = ""
    current_compile_result: CompileResult | None = None
    history: list[WorkspaceHistoryEntry] = field(default_factory=list)
    submitted_at: datetime | None = None

    @property
    def is_terminal(self) -> bool:
        """Whether the workspace can no longer be mutated under normal flow."""

        return self.state is WorkspaceState.SUBMITTED

    def set_state(self, state: WorkspaceState) -> None:
        """Update the current lifecycle state.

        Transition validation is handled by later guardrail-focused checklist
        items so the state model itself remains reusable.
        """

        self.state = state

    def record(self, action: str, **details: Any) -> WorkspaceHistoryEntry:
        """Append a history entry and return it."""

        entry = WorkspaceHistoryEntry(action=action, details=dict(details))
        self.history.append(entry)
        return entry

"""Transport-neutral command schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CommandName(StrEnum):
    """Core command names exposed to transports/adapters."""

    HIGHLIGHT = "highlight"
    WARNING = "warning"
    OPEN_WORKSPACE = "open_workspace"
    ADVANCE = "advance"


@dataclass(slots=True, frozen=True)
class HighlightCommand:
    command_id: str
    level: str
    reason: str | None = None
    command_name: CommandName = field(init=False, default=CommandName.HIGHLIGHT)


@dataclass(slots=True, frozen=True)
class WarningCommand:
    command_id: str
    kind: str
    severity: str
    message: str
    evidence: tuple[str, ...] = ()
    command_name: CommandName = field(init=False, default=CommandName.WARNING)


@dataclass(slots=True, frozen=True)
class OpenWorkspaceCommand:
    command_id: str
    task: str
    capability: str | None = None
    language: str | None = None
    command_name: CommandName = field(init=False, default=CommandName.OPEN_WORKSPACE)


@dataclass(slots=True, frozen=True)
class AdvanceCommand:
    command_id: str
    command_name: CommandName = field(init=False, default=CommandName.ADVANCE)

"""Core runtime models.

This module holds architecture-level state containers for the DocWright Core
runtime. It intentionally stays policy-neutral: adapter, capability, skill,
and workspace-specific behavior lives in their own layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from docwright._compat import StrEnum
from typing import Any


class RuntimeSessionStatus(StrEnum):
    """Lifecycle status for a runtime session."""

    INITIALIZED = "initialized"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class RuntimeStepState:
    """Mutable state for the current runtime-visible document step."""

    index: int = 0
    node_id: str | None = None
    highlight_count: int = 0
    warning_count: int = 0
    workspace_opened: bool = False
    workspace_open_count: int = 0

    def enter_node(self, *, index: int, node_id: str | None) -> None:
        """Move runtime state to a new node step and reset per-step counters."""

        self.index = index
        self.node_id = node_id
        self.highlight_count = 0
        self.warning_count = 0
        self.workspace_opened = False
        self.workspace_open_count = 0


@dataclass(slots=True)
class RuntimeSessionModel:
    """Serializable session-level state owned by DocWright Core.

    The model deliberately stores stable identifiers and lightweight metadata,
    leaving adapter execution, capability policy, and document traversal
    mechanics to their respective layers.
    """

    session_id: str
    run_id: str
    document_id: str
    capability_name: str | None = None
    adapter_name: str | None = None
    status: RuntimeSessionStatus = RuntimeSessionStatus.INITIALIZED
    step: RuntimeStepState = field(default_factory=RuntimeStepState)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self, *, at: datetime | None = None) -> None:
        """Update the last-modified timestamp."""

        self.updated_at = at or datetime.now(timezone.utc)

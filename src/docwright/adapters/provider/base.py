"""Provider compatibility boundary for future SDK-specific integrations.

This layer exists so provider-specific request/response quirks can be expressed
without leaking those shapes into Core, protocol primitives, or the
transport-neutral Codex bridge types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True, frozen=True)
class ProviderMessage:
    """Provider-local message item for SDK/request compatibility layers."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ProviderToolCall:
    """Provider-local tool call item for SDK/request compatibility layers."""

    call_id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ProviderToolResult:
    """Provider-local tool result item for SDK/request compatibility layers."""

    call_id: str
    name: str
    output: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ProviderTurnEnvelope:
    """Provider-local turn envelope for adapter-scoped compatibility code."""

    messages: tuple[ProviderMessage, ...] = ()
    tool_calls: tuple[ProviderToolCall, ...] = ()
    tool_results: tuple[ProviderToolResult, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

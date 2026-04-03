"""Optional MCP-facing wrapper over the existing Codex/runtime bridge.

This module intentionally does not define a second runtime path. It only
re-expresses the existing exported step contract and tool execution helpers in a
shape that an MCP host can consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.adapters.transport.codex_exports import (
    serialize_codex_contract,
    serialize_codex_tool_result,
)
from docwright.adapters.transport.codex_host import CodexHostBridge

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession


@dataclass(slots=True, frozen=True)
class McpTool:
    """Minimal MCP-visible tool description derived from the Codex contract."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(slots=True)
class DocWrightMcpBridge:
    """Thin MCP wrapper over ``CodexHostBridge``.

    The stable runtime integration remains the direct-library bridge. This class
    only adapts that contract to an MCP-style host surface.
    """

    bridge: CodexHostBridge

    @classmethod
    def from_session(
        cls,
        session: RuntimeSession,
        *,
        capability: CapabilityProfile | None = None,
    ) -> "DocWrightMcpBridge":
        return cls(bridge=CodexHostBridge(session=session, capability=capability))

    def describe_server(self) -> dict[str, Any]:
        contract = self.bridge.export_step()
        return {
            "server_name": "docwright",
            "transport": "mcp_wrapper",
            "instructions": contract.instructions,
            "metadata": dict(contract.metadata),
            "tools": [self._serialize_mcp_tool(tool) for tool in contract.tools],
        }

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None, *, call_id: str = "mcp-call") -> dict[str, Any]:
        result = self.bridge.execute_tool_call(
            CodexToolCall(call_id=call_id, name=name, arguments={} if arguments is None else dict(arguments))
        )
        return serialize_codex_tool_result(result)

    def export_step(self) -> dict[str, Any]:
        return serialize_codex_contract(self.bridge.export_step())

    def _serialize_mcp_tool(self, tool: Any) -> dict[str, Any]:
        return {
            "name": getattr(tool, "name"),
            "description": getattr(tool, "description"),
            "input_schema": dict(getattr(tool, "input_schema")),
        }


__all__ = ["DocWrightMcpBridge", "McpTool"]

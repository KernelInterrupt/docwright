"""Serialization helpers for Codex bridge exports and transcript fixtures."""

from __future__ import annotations

from typing import Any

from docwright.adapters.agent.codex_types import CodexRuntimeContract, CodexToolCall, CodexToolResult
from docwright.protocol.schemas import serialize_schema


def serialize_codex_contract(contract: CodexRuntimeContract) -> dict[str, Any]:
    """Convert a Codex runtime contract into a transport-safe payload."""

    payload = serialize_schema(contract)
    assert isinstance(payload, dict)
    return payload


def serialize_codex_tool_call(call: CodexToolCall) -> dict[str, Any]:
    """Convert a Codex tool call into a transport-safe payload."""

    payload = serialize_schema(call)
    assert isinstance(payload, dict)
    return payload


def serialize_codex_tool_result(result: CodexToolResult) -> dict[str, Any]:
    """Convert a Codex tool result into a transport-safe payload."""

    payload = serialize_schema(result)
    assert isinstance(payload, dict)
    return payload


def build_codex_transcript_fixture(
    *,
    contract: CodexRuntimeContract,
    tool_calls: tuple[CodexToolCall, ...] = (),
    tool_results: tuple[CodexToolResult, ...] = (),
    output_text: str = "",
    stop_reason: str | None = None,
) -> dict[str, Any]:
    """Build a stable JSON-safe transcript payload for external-host fixtures."""

    return {
        "contract": serialize_codex_contract(contract),
        "tool_calls": [serialize_codex_tool_call(call) for call in tool_calls],
        "tool_results": [serialize_codex_tool_result(result) for result in tool_results],
        "output": {
            "output_text": output_text,
            "stop_reason": stop_reason,
        },
    }

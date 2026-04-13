"""Official Attention-based smoke/demo path for Codex-style hosts.

This module intentionally uses the canonical integration contract:

- load the prepared Attention IR fixture as a DocumentHandle
- construct ``DocWrightCodexEntry.from_document(...)``
- export one step contract
- execute a small set of explicit-target/runtime inspection tool calls
"""

from __future__ import annotations

from typing import Any

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.codex.entry import DocWrightCodexEntry
from docwright.codex.samples.attention_fixture import FIXTURE_PATH
from docwright.document import load_in_memory_document_from_ir_path
from docwright.protocol.schemas import serialize_schema


def run_attention_fixture_smoke() -> dict[str, Any]:
    """Run the official Attention fixture smoke path through the installed API."""

    document = load_in_memory_document_from_ir_path(FIXTURE_PATH)
    entry = DocWrightCodexEntry.from_document(
        document,
        capability=ManualTaskCapability(),
        session_id="attention-smoke-session",
        run_id="attention-smoke-run",
    )
    contract = entry.export_step()
    tool_results = entry.execute_tool_calls(
        (
            CodexToolCall(call_id="call-1", name="get_node", arguments={"node_id": "para_0001"}),
            CodexToolCall(call_id="call-2", name="get_context", arguments={"node_id": "para_0001", "before": 1, "after": 1}),
            CodexToolCall(call_id="call-3", name="search_text", arguments={"query": "attention", "limit": 3}),
            CodexToolCall(call_id="call-4", name="jump_to_node", arguments={"node_id": "sec_0001"}),
        )
    )
    return {
        "fixture_path": str(FIXTURE_PATH),
        "contract": serialize_schema(contract),
        "tool_results": [serialize_schema(result) for result in tool_results],
        "usage": serialize_schema(entry.usage_snapshot()),
    }


__all__ = ["run_attention_fixture_smoke"]

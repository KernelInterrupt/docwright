from pathlib import Path

import pytest

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.codex.entry import DocWrightCodexEntry
from docwright.document import document_backend_available


PDF_FIXTURE = (Path(__file__).resolve().parents[2] / ".." / "docwright-example" / "assets" / "attention_is_all_you_need.pdf").resolve()

pytestmark = pytest.mark.skipif(
    not document_backend_available() or not PDF_FIXTURE.exists(),
    reason="real PDF acceptance requires the optional document backend and local PDF fixture",
)


def test_real_pdf_acceptance_supports_explicit_node_targeting_and_legacy_traversal() -> None:
    entry = DocWrightCodexEntry.from_pdf(
        str(PDF_FIXTURE),
        goal="acceptance smoke",
        capability=ManualTaskCapability(),
        session_id="real-pdf-acceptance",
        run_id="real-pdf-acceptance-run",
    )

    contract = entry.export_step()
    current_node_id = contract.metadata["current_node_id"]

    current = entry.execute_tool_call(
        CodexToolCall(call_id="1", name="get_node", arguments={"node_id": current_node_id})
    )
    search = entry.execute_tool_call(
        CodexToolCall(call_id="2", name="search_text", arguments={"query": "attention", "limit": 3})
    )

    assert current.output["node"]["ref"]["node_id"] == current_node_id
    assert len(search.output["hits"]) >= 1

    target_node_id = search.output["hits"][0]["node_id"]
    jumped = entry.execute_tool_call(
        CodexToolCall(call_id="3", name="jump_to_node", arguments={"node_id": target_node_id})
    )
    assert jumped.output["node"]["node_id"] == target_node_id

    advances = 0
    while not entry.is_terminal() and advances < 32:
        entry.execute_tool_call(CodexToolCall(call_id=f"adv-{advances}", name="advance"))
        advances += 1

    assert advances >= 1
    assert entry.is_terminal() is True

from pathlib import Path

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.codex.entry import DocWrightCodexEntry
from docwright.document import load_in_memory_document_from_ir_path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "document_ir" / "navigation_with_links.document_ir.json"


def test_navigation_fixture_supports_search_jump_and_internal_link_tools() -> None:
    document = load_in_memory_document_from_ir_path(FIXTURE)
    entry = DocWrightCodexEntry.from_document(
        document,
        capability=ManualTaskCapability(),
        session_id="navigation-session",
        run_id="navigation-run",
    )

    contract = entry.export_step()
    tool_names = [tool.name for tool in contract.tools]

    assert tool_names[:4] == ["get_node", "get_context", "search_text", "get_structure"]
    assert "get_structure" in tool_names
    assert "search_headings" in tool_names
    assert "jump_to_node" in tool_names
    assert "list_internal_links" in tool_names
    assert "follow_internal_link" in tool_names
    assert "current_node" in tool_names
    assert "advance" in tool_names

    headings = entry.execute_tool_call(
        CodexToolCall(call_id="1", name="search_headings", arguments={"query": "Device B", "limit": 5})
    )
    structure = entry.execute_tool_call(CodexToolCall(call_id="2", name="get_structure", arguments={}))
    links = entry.execute_tool_call(CodexToolCall(call_id="3", name="list_internal_links", arguments={"node_id": "para_intro"}))
    jumped = entry.execute_tool_call(
        CodexToolCall(call_id="4", name="jump_to_node", arguments={"node_id": "sec_device_b"})
    )

    fresh_entry = DocWrightCodexEntry.from_document(
        document,
        capability=ManualTaskCapability(),
        session_id="navigation-session-2",
        run_id="navigation-run-2",
    )
    followed = fresh_entry.execute_tool_call(
        CodexToolCall(call_id="5", name="follow_internal_link", arguments={"relation_id": "rel_link_0001", "node_id": "para_intro"})
    )

    assert headings.output["hits"][0]["node_id"] == "sec_device_b"
    assert structure.output["structure"]["section_path_node_ids"] == ["sec_intro"]
    assert links.output["links"][0]["target_node_id"] == "sec_device_b"
    assert jumped.output["node"]["node_id"] == "sec_device_b"
    assert followed.output["node"]["node_id"] == "sec_device_b"

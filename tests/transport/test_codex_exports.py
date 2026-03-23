import json
from pathlib import Path

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.adapters.transport.codex_exports import (
    build_codex_transcript_fixture,
    serialize_codex_contract,
)
from docwright.adapters.transport.codex_library import CodexLibraryBridge
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "codex"


def make_session() -> RuntimeSession:
    return RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
                InMemoryNode(node_id="node-3", kind="paragraph", text="gamma"),
            ],
        ),
        guardrail_policy=ManualTaskCapability().guardrail_policy(),
    )


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_guided_reading_contract_fixture_matches_live_export() -> None:
    bridge = CodexLibraryBridge(session=make_session(), capability=GuidedReadingCapability())

    contract = serialize_codex_contract(bridge.export_step())

    assert contract == load_fixture("guided_reading_step_contract.json")


def test_manual_task_transcript_fixture_matches_live_bridge_flow() -> None:
    bridge = CodexLibraryBridge(session=make_session(), capability=ManualTaskCapability())
    contract = bridge.export_step()
    tool_calls = (
        CodexToolCall(call_id="call-1", name="current_node"),
        CodexToolCall(call_id="call-2", name="get_context", arguments={"before": 1, "after": 1}),
        CodexToolCall(call_id="call-3", name="advance"),
    )
    tool_results = bridge.execute_tool_calls(tool_calls)
    transcript = build_codex_transcript_fixture(
        contract=contract,
        tool_calls=tool_calls,
        tool_results=tool_results,
        output_text="Step complete.",
        stop_reason="done",
    )

    assert transcript == load_fixture("manual_task_navigation_transcript.json")

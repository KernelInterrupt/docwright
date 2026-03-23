import pytest

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.adapters.transport.codex_entry import DocWrightCodexEntry
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.core.guardrails import GuardrailViolationError
from docwright.document.handles import InMemoryDocument, InMemoryNode


def make_document() -> InMemoryDocument:
    return InMemoryDocument.from_nodes(
        document_id="doc-1",
        nodes=[
            InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
            InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
        ],
    )


def test_codex_entry_builds_runtime_session_and_bridge_from_document() -> None:
    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=ManualTaskCapability(),
        session_id="session-x",
        run_id="run-x",
    )

    contract = entry.export_step()

    assert entry.session.model.document_id == "doc-1"
    assert entry.session.model.session_id == "session-x"
    assert entry.session.model.run_id == "run-x"
    assert entry.session.model.capability_name == "manual_task"
    assert entry.session.model.adapter_name == "codex"
    assert contract.metadata["session_id"] == "session-x"
    assert contract.metadata["capability"] == "manual_task"


def test_codex_entry_uses_capability_guardrails_by_default() -> None:
    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=GuidedReadingCapability(),
    )

    with pytest.raises(GuardrailViolationError):
        entry.execute_tool_call(CodexToolCall(call_id="1", name="advance"))


def test_codex_entry_delegates_usage_snapshot() -> None:
    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=ManualTaskCapability(),
    )

    entry.export_step()
    entry.stream_output_delta(text_delta="abc")
    usage = entry.usage_snapshot()

    assert usage.step_exports == 1
    assert usage.output_deltas == 1
    assert usage.output_delta_chars == 3

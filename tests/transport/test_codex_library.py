from dataclasses import dataclass, field

import pytest

from docwright.adapters.agent.codex import CodexAdapter
from docwright.adapters.agent.codex_types import (
    CodexBridgeEvent,
    CodexToolCall,
    CodexTraceRecord,
)
from docwright.adapters.transport.codex_library import CodexLibraryBridge
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.core.guardrails import GuardrailViolationError
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


@dataclass(slots=True)
class EventCollector:
    events: list[CodexBridgeEvent] = field(default_factory=list)

    def on_bridge_event(self, event: CodexBridgeEvent) -> None:
        self.events.append(event)


@dataclass(slots=True)
class TraceCollector:
    records: list[CodexTraceRecord] = field(default_factory=list)

    def record_trace(self, record: CodexTraceRecord) -> None:
        self.records.append(record)


def make_session() -> RuntimeSession:
    return RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
            ],
        ),
        guardrail_policy=ManualTaskCapability().guardrail_policy(),
    )


def test_codex_library_bridge_exports_current_step_and_tool_names() -> None:
    bridge = CodexLibraryBridge(session=make_session(), capability=GuidedReadingCapability())

    contract = bridge.export_step()

    assert "Current node: node-1" in contract.turn_prompt
    assert contract.metadata["session_id"] == "session-1"
    assert bridge.available_tool_names()[:3] == ("current_node", "get_context", "advance")


def test_codex_library_bridge_executes_tools_and_refreshes_step_contract() -> None:
    bridge = CodexLibraryBridge(session=make_session(), capability=ManualTaskCapability())

    results = bridge.execute_tool_calls(
        (
            CodexToolCall(call_id="1", name="current_node"),
            CodexToolCall(call_id="2", name="advance"),
        )
    )
    refreshed = bridge.export_step()

    assert results[0].output["node"]["node_id"] == "node-1"
    assert results[1].output["node"]["node_id"] == "node-2"
    assert "Current node: node-2" in refreshed.turn_prompt


def test_codex_library_bridge_records_output_and_terminal_state() -> None:
    bridge = CodexLibraryBridge(session=make_session(), capability=ManualTaskCapability())

    bridge.execute_tool_call(CodexToolCall(call_id="1", name="advance"))
    bridge.execute_tool_call(CodexToolCall(call_id="2", name="advance"))
    bridge.record_output(output_text="Finished.", stop_reason="done")

    assert bridge.is_terminal() is True
    assert bridge.session.events()[-1].as_protocol_event().event_name == "adapter.codex_output"


def test_codex_library_bridge_emits_streaming_and_runtime_hooks() -> None:
    collector = EventCollector()
    adapter = CodexAdapter(observers=(collector,))
    bridge = CodexLibraryBridge(
        session=make_session(),
        capability=ManualTaskCapability(),
        adapter=adapter,
    )

    bridge.export_step()
    bridge.stream_output_delta(text_delta="Thinking...")
    bridge.execute_tool_call(CodexToolCall(call_id="1", name="advance"))
    bridge.record_output(output_text="Done.", stop_reason="done")

    kinds = [event.kind for event in collector.events]
    assert kinds == [
        "step_exported",
        "output_delta",
        "tool_call_started",
        "tool_call_completed",
        "runtime_events_emitted",
        "output_recorded",
        "runtime_events_emitted",
    ]
    assert collector.events[0].payload["contract"]["metadata"]["adapter"] == "codex"
    assert collector.events[1].payload["text_delta"] == "Thinking..."
    assert collector.events[4].payload["events"][-1]["name"] == "node.entered"
    assert collector.events[6].payload["events"][-1]["name"] == "adapter.codex_output"


def test_codex_library_bridge_emits_failed_tool_hook_and_reraises() -> None:
    collector = EventCollector()
    adapter = CodexAdapter(observers=(collector,))
    guarded_session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
            ],
        ),
        guardrail_policy=GuidedReadingCapability().guardrail_policy(),
    )
    bridge = CodexLibraryBridge(
        session=guarded_session,
        capability=GuidedReadingCapability(),
        adapter=adapter,
    )

    with pytest.raises(GuardrailViolationError):
        bridge.execute_tool_call(CodexToolCall(call_id="1", name="advance"))

    kinds = [event.kind for event in collector.events]
    assert kinds == ["tool_call_started", "tool_call_failed"]
    assert collector.events[-1].payload["error"]["type"] == "GuardrailViolationError"


def test_codex_library_bridge_tracks_usage_and_trace_records() -> None:
    traces = TraceCollector()
    adapter = CodexAdapter(trace_sinks=(traces,))
    bridge = CodexLibraryBridge(
        session=make_session(),
        capability=ManualTaskCapability(),
        adapter=adapter,
    )

    bridge.export_step()
    bridge.stream_output_delta(text_delta="abc")
    bridge.execute_tool_call(CodexToolCall(call_id="1", name="advance"))
    bridge.record_output(output_text="Done", stop_reason="done")

    usage = bridge.usage_snapshot()
    assert usage.step_exports == 1
    assert usage.tool_calls_started == 1
    assert usage.tool_calls_completed == 1
    assert usage.tool_call_failures == 0
    assert usage.runtime_event_batches == 2
    assert usage.runtime_events_emitted == 2
    assert usage.output_deltas == 1
    assert usage.output_delta_chars == 3
    assert usage.outputs_recorded == 1
    assert usage.output_chars_recorded == 4

    assert [record.sequence for record in traces.records] == [1, 2, 3, 4, 5, 6, 7]
    assert [record.kind for record in traces.records] == [
        "step_exported",
        "output_delta",
        "tool_call_started",
        "tool_call_completed",
        "runtime_events_emitted",
        "output_recorded",
        "runtime_events_emitted",
    ]
    assert traces.records[0].adapter_name == "codex"
    assert traces.records[0].session_id == "session-1"
    assert traces.records[0].run_id == "run-1"
    assert traces.records[1].payload["text_delta"] == "abc"

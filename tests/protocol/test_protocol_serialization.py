from docwright.adapters.agent.base import AdapterDescriptor
from docwright.adapters.transport.headless import HeadlessRunner
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.protocol.commands import HighlightCommand, OpenWorkspaceCommand
from docwright.protocol.events import EventFamily, EventName, ProtocolEvent, RunEventSchema, SessionEventSchema
from docwright.protocol.schemas import serialize_schema


class FakeAdapter:
    descriptor = AdapterDescriptor(name="serialize-adapter")

    async def run_step(self, session: RuntimeSession, capability: GuidedReadingCapability | None = None) -> None:
        if capability is not None:
            session.record_highlight(level="important")
        session.advance()


def test_command_and_event_schemas_serialize_to_transport_payloads() -> None:
    command_payload = serialize_schema(
        OpenWorkspaceCommand(
            command_id="cmd-1",
            task="annotation",
            capability="guided_reading",
            language="latex",
        )
    )
    event_payload = serialize_schema(
        ProtocolEvent(
            event_id="evt-1",
            name=EventName(EventFamily.RUNTIME, "started"),
            payload={
                "run": RunEventSchema(run_id="run-1", document_id="doc-1"),
                "session": SessionEventSchema(
                    run_id="run-1",
                    session_id="session-1",
                    document_id="doc-1",
                    status="active",
                    step_index=0,
                    node_id="node-1",
                ),
            },
            correlation_id="run-1",
        )
    )

    assert command_payload == {
        "command_id": "cmd-1",
        "task": "annotation",
        "capability": "guided_reading",
        "language": "latex",
        "command_name": "open_workspace",
    }
    assert event_payload["name"] == "runtime.started"
    assert event_payload["payload"]["run"]["run_id"] == "run-1"
    assert event_payload["payload"]["session"]["node_id"] == "node-1"


def test_headless_runner_events_can_be_serialized_without_transport_specific_logic() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph"),
                InMemoryNode(node_id="node-2", kind="paragraph"),
            ],
        ),
        guardrail_policy=GuidedReadingCapability().guardrail_policy(),
    )
    runner = HeadlessRunner(adapter=FakeAdapter(), capability=GuidedReadingCapability())

    events = runner.run_once(session)
    serialized_events = [serialize_schema(event) for event in events]

    assert serialized_events[0]["name"] == "runtime.started"
    assert serialized_events[-2]["name"] == "highlight.applied"
    assert serialized_events[-1]["name"] == "node.entered"
    assert all("occurred_at" in event for event in serialized_events)

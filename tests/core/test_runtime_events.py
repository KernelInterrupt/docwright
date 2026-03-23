from docwright.core.events import RuntimeEventContext, RuntimeEventEnvelope
from docwright.protocol.events import EventFamily, EventName


def test_runtime_event_context_serializes_runtime_identifiers() -> None:
    context = RuntimeEventContext(
        run_id="run-1",
        session_id="session-1",
        step_index=2,
        node_id="node-9",
        workspace_id="ws-3",
    )

    assert context.as_payload() == {
        "run_id": "run-1",
        "session_id": "session-1",
        "step_index": 2,
        "node_id": "node-9",
        "workspace_id": "ws-3",
    }


def test_runtime_event_envelope_converts_to_protocol_event() -> None:
    envelope = RuntimeEventEnvelope(
        name=EventName(EventFamily.WORKSPACE, "opened"),
        context=RuntimeEventContext(run_id="run-1", session_id="session-1", workspace_id="ws-3"),
        payload={"task": "annotation"},
        event_id="evt-123",
    )

    protocol_event = envelope.as_protocol_event()

    assert protocol_event.event_id == "evt-123"
    assert protocol_event.event_name == "workspace.opened"
    assert protocol_event.correlation_id == "run-1"
    assert protocol_event.payload == {
        "run_id": "run-1",
        "session_id": "session-1",
        "workspace_id": "ws-3",
        "task": "annotation",
    }

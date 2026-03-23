from docwright.protocol.events import (
    EventFamily,
    EventName,
    ProtocolEvent,
    RunEventSchema,
    SessionEventSchema,
)


def test_event_name_serializes_family_and_action() -> None:
    name = EventName(EventFamily.WORKSPACE, "opened")

    assert str(name) == "workspace.opened"


def test_run_and_session_event_schemas_capture_transport_payloads() -> None:
    run_schema = RunEventSchema(
        run_id="run-1",
        document_id="doc-1",
        adapter_name="codex",
        capability_name="guided_reading",
    )
    session_schema = SessionEventSchema(
        run_id="run-1",
        session_id="session-1",
        document_id="doc-1",
        status="active",
        step_index=2,
        node_id="node-3",
        workspace_id="ws-1",
    )

    assert run_schema.adapter_name == "codex"
    assert run_schema.capability_name == "guided_reading"
    assert session_schema.step_index == 2
    assert session_schema.workspace_id == "ws-1"


def test_protocol_event_as_dict_is_transport_neutral() -> None:
    event = ProtocolEvent(
        event_id="evt-1",
        name=EventName(EventFamily.RUNTIME, "started"),
        payload={"session_id": "session-1"},
        correlation_id="run-1",
    )

    payload = event.as_dict()

    assert payload["event_id"] == "evt-1"
    assert payload["name"] == "runtime.started"
    assert payload["payload"] == {"session_id": "session-1"}
    assert payload["correlation_id"] == "run-1"
    assert isinstance(payload["occurred_at"], str)

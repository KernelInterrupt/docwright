from docwright.protocol.commands import HighlightCommand
from docwright.protocol.events import EventFamily, EventName, ProtocolEvent, RunEventSchema
from docwright.protocol.schemas import serialize_schema


def test_serialize_schema_handles_protocol_dataclasses_and_events() -> None:
    command = HighlightCommand(command_id="cmd-1", level="important", reason="key claim")
    run_schema = RunEventSchema(run_id="run-1", document_id="doc-1", adapter_name="codex")
    event = ProtocolEvent(
        event_id="evt-1",
        name=EventName(EventFamily.RUNTIME, "started"),
        payload={"run": run_schema},
        correlation_id="run-1",
    )

    assert serialize_schema(command) == {
        "command_id": "cmd-1",
        "level": "important",
        "reason": "key claim",
        "command_name": "highlight",
    }
    assert serialize_schema(run_schema) == {
        "run_id": "run-1",
        "document_id": "doc-1",
        "adapter_name": "codex",
        "capability_name": None,
    }
    assert serialize_schema(event)["name"] == "runtime.started"

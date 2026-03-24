from docwright.protocol.render import RenderToolCall, RenderTrace
from docwright.protocol.schemas import serialize_schema


def test_render_protocol_serializes_tool_call_operations() -> None:
    payload = serialize_schema(
        RenderTrace(
            adapter="codex",
            session_id="session-1",
            run_id="run-1",
            operations=(
                RenderToolCall(
                    sequence=1,
                    call_id="call-1",
                    tool_name="current_node",
                    arguments={},
                    status="completed",
                    output={"node_id": "node-1"},
                ),
            ),
        )
    )

    assert payload == {
        "adapter": "codex",
        "session_id": "session-1",
        "run_id": "run-1",
        "operations": [
            {
                "sequence": 1,
                "call_id": "call-1",
                "tool_name": "current_node",
                "arguments": {},
                "status": "completed",
                "output": {"node_id": "node-1"},
                "error": None,
            }
        ],
    }

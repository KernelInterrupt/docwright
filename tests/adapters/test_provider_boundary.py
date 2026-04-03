from docwright.adapters.agent.codex_types import CodexToolCall, CodexToolResult
from docwright.adapters.provider.base import (
    ProviderMessage,
    ProviderToolCall,
    ProviderToolResult,
    ProviderTurnEnvelope,
)
from docwright.protocol.schemas import serialize_schema


def test_provider_boundary_types_are_adapter_scoped_and_serializable() -> None:
    envelope = ProviderTurnEnvelope(
        messages=(ProviderMessage(role="user", content="read the paper"),),
        tool_calls=(ProviderToolCall(call_id="c1", name="current_node"),),
        tool_results=(ProviderToolResult(call_id="c1", name="current_node", output={"node_id": "n1"}),),
        metadata={"provider": "responses_like"},
    )

    payload = serialize_schema(envelope)

    assert payload["messages"][0]["role"] == "user"
    assert payload["tool_calls"][0]["name"] == "current_node"
    assert payload["tool_results"][0]["output"]["node_id"] == "n1"
    assert payload["metadata"]["provider"] == "responses_like"


def test_provider_boundary_stays_distinct_from_transport_neutral_codex_types() -> None:
    provider_call = ProviderToolCall(call_id="c1", name="advance", arguments={"x": 1})
    codex_call = CodexToolCall(call_id="c1", name="advance", arguments={"x": 1})
    provider_result = ProviderToolResult(call_id="c1", name="advance", output={"status": "active"})
    codex_result = CodexToolResult(call_id="c1", name="advance", output={"status": "active"})

    assert provider_call is not codex_call
    assert provider_result is not codex_result
    assert serialize_schema(provider_call) == {
        "call_id": "c1",
        "name": "advance",
        "arguments": {"x": 1},
        "metadata": {},
    }

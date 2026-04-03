from docwright.adapters.transport.mcp import DocWrightMcpBridge
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


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


def test_mcp_bridge_reuses_existing_exported_step_contract() -> None:
    bridge = DocWrightMcpBridge.from_session(make_session(), capability=ManualTaskCapability())

    server = bridge.describe_server()

    assert server["server_name"] == "docwright"
    assert server["transport"] == "mcp_wrapper"
    assert server["metadata"]["adapter"] == "codex"
    assert server["tools"][0]["name"] == "current_node"
    assert any(tool["name"] == "open_workspace" for tool in server["tools"])


def test_mcp_bridge_executes_tools_through_existing_codex_host_bridge() -> None:
    bridge = DocWrightMcpBridge.from_session(make_session(), capability=ManualTaskCapability())

    current = bridge.call_tool("current_node", call_id="mcp-1")
    advanced = bridge.call_tool("advance", call_id="mcp-2")

    assert current["call_id"] == "mcp-1"
    assert current["output"]["node"]["node_id"] == "node-1"
    assert advanced["call_id"] == "mcp-2"
    assert advanced["output"]["node"]["node_id"] == "node-2"

from dataclasses import dataclass

from docwright.adapters.agent.codex_tools import CodexToolRegistry
from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.workspace.models import CompileResult, WorkspaceSessionModel


@dataclass(slots=True)
class FakeCompiler:
    result: CompileResult

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        return self.result


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
        guardrail_policy=GuidedReadingCapability().guardrail_policy(),
        workspace_compiler=FakeCompiler(result=CompileResult(ok=True, backend_name="fake", rendered_content="ok")),
    )


def test_tool_registry_filters_tools_from_active_skills() -> None:
    registry = CodexToolRegistry()
    tools = registry.tools_for(make_session(), GuidedReadingCapability())

    names = [tool.name for tool in tools]
    assert names == [
        "current_node",
        "get_context",
        "advance",
        "highlight",
        "warning",
        "open_workspace",
        "read_body",
        "write_body",
        "patch_body",
        "compile",
        "submit",
    ]
    descriptions = {tool.name: tool.description for tool in tools}
    assert descriptions["current_node"] == "Inspect the current DocWright node before taking any action."
    assert descriptions["highlight"] == "Mark the current node with a structured highlight level and optional reason."
    assert descriptions["compile"] == "Compile the workspace body and return structured success or error details."


def test_tool_registry_executes_runtime_and_workspace_tools() -> None:
    registry = CodexToolRegistry()
    session = make_session()
    capability = GuidedReadingCapability()

    current = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1", name="current_node"),
    )
    highlighted = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="2", name="highlight", arguments={"level": "important"}),
    )
    opened = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="3", name="open_workspace", arguments={"task": "annotation"}),
    )
    workspace_id = opened.output["workspace"]["workspace_id"]
    compiled = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="4", name="compile", arguments={"workspace_id": workspace_id}),
    )
    submitted = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="5", name="submit", arguments={"workspace_id": workspace_id}),
    )

    assert current.output["node"]["node_id"] == "node-1"
    assert highlighted.output["event"]["name"] == "highlight.applied"
    assert compiled.output["compile_result"]["ok"] is True
    assert submitted.output["workspace"]["state"] == "submitted"

from dataclasses import dataclass

from docwright.adapters.agent.codex_tools import CodexToolRegistry
from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.workspace.models import CompileResult, WorkspaceSessionModel
from docwright.workspace.profiles import WorkspaceProfile
from docwright.workspace.registry import WorkspaceProfileRegistry
from docwright.workspace.templates import EditableRegionSpec, WorkspaceTemplate


@dataclass(slots=True)
class FakeCompiler:
    result: CompileResult

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        return self.result


def make_workspace_registry() -> WorkspaceProfileRegistry:
    registry = WorkspaceProfileRegistry()
    registry.register_template(
        WorkspaceTemplate(
            template_id="default_annotation_tex",
            task="annotation",
            body_kind="latex_body",
            source="template shell",
            editable_regions=(
                EditableRegionSpec(
                    name="body",
                    mode="marker_range",
                    start_marker="% DOCWRIGHT:BODY_START",
                    end_marker="% DOCWRIGHT:BODY_END",
                ),
            ),
            compiler_profile="tectonic",
        )
    )
    registry.register_profile(
        WorkspaceProfile(
            profile_name="latex_annotation",
            task="annotation",
            template_id="default_annotation_tex",
            body_kind="latex_body",
            compiler_profile="tectonic",
            locked_sections=("preamble",),
            model_summary="Edit only the annotation body.",
        )
    )
    return registry


def make_session(*, workspace_registry: WorkspaceProfileRegistry | None = None) -> RuntimeSession:
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
        workspace_registry=workspace_registry,
    )


def test_tool_registry_filters_tools_from_active_skills() -> None:
    registry = CodexToolRegistry()
    tools = registry.tools_for(make_session(), GuidedReadingCapability())

    names = [tool.name for tool in tools]
    assert names == [
        "current_node",
        "get_context",
        "search_text",
        "advance",
        "highlight",
        "warning",
        "open_workspace",
        "describe_workspace",
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
    session = make_session(workspace_registry=make_workspace_registry())
    capability = GuidedReadingCapability()

    current = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1", name="current_node"),
    )
    searched = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1b", name="search_text", arguments={"query": "alpha", "limit": 5}),
    )
    highlighted = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="2", name="highlight", arguments={"level": "important"}),
    )
    opened = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(
            call_id="3",
            name="open_workspace",
            arguments={
                "task": "annotation",
                "workspace_profile": "latex_annotation",
                "template_id": "default_annotation_tex",
                "body_kind": "latex_body",
                "compiler_profile": "tectonic",
            },
        ),
    )
    workspace_id = opened.output["workspace"]["workspace_id"]
    described = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="3b", name="describe_workspace", arguments={"workspace_id": workspace_id}),
    )
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
    assert [hit["node_id"] for hit in searched.output["hits"]] == ["node-1"]
    assert highlighted.output["event"]["name"] == "highlight.applied"
    assert opened.output["workspace"]["workspace_profile"] == "latex_annotation"
    assert opened.output["workspace"]["template_id"] == "default_annotation_tex"
    assert opened.output["workspace"]["body_kind"] == "latex_body"
    assert opened.output["workspace"]["compiler_profile"] == "tectonic"
    assert opened.output["workspace"]["compile_ready"] is True
    assert described.output["workspace"]["workspace_id"] == workspace_id
    assert described.output["workspace"]["workspace_profile"] == "latex_annotation"
    assert compiled.output["compile_result"]["ok"] is True
    assert submitted.output["workspace"]["state"] == "submitted"


def test_tool_registry_open_workspace_uses_registry_profile_defaults() -> None:
    registry = CodexToolRegistry()
    session = make_session(workspace_registry=make_workspace_registry())

    opened = registry.execute_tool(
        session=session,
        capability=GuidedReadingCapability(),
        call=CodexToolCall(
            call_id="registry-1",
            name="open_workspace",
            arguments={"task": "annotation", "workspace_profile": "latex_annotation"},
        ),
    )

    workspace = opened.output["workspace"]
    assert workspace["template_id"] == "default_annotation_tex"
    assert workspace["body_kind"] == "latex_body"
    assert workspace["compiler_profile"] == "tectonic"
    assert workspace["locked_sections"] == ["preamble"]
    assert workspace["summary"] == "Edit only the annotation body."
    assert workspace["editable_region"]["start_marker"] == "% DOCWRIGHT:BODY_START"

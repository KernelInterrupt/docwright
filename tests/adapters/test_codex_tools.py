from dataclasses import dataclass

from docwright.adapters.agent.codex_tools import CodexToolRegistry
from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.document.interfaces import NodeRelationRef
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
            source="\n".join([r"\documentclass{article}", "% DOCWRIGHT:BODY_START", "% DOCWRIGHT:BODY_END"]),
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
            sandbox_profile="local_process",
        )
    )
    return registry



def make_session(*, workspace_registry: WorkspaceProfileRegistry | None = None) -> RuntimeSession:
    return RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            root_id="root",
            reading_order=("node-1", "node-2"),
            nodes=[
                InMemoryNode(node_id="sec-1", kind="section", text="Guide", parent_node_id="root"),
                InMemoryNode(
                    node_id="node-1",
                    kind="paragraph",
                    text="alpha",
                    parent_node_id="sec-1",
                    relation_refs=(NodeRelationRef(relation_id="rel-link-1", kind="internal_link_to", target_id="sec-2"),),
                ),
                InMemoryNode(node_id="sec-2", kind="section", text="Appendix", page_number=2, parent_node_id="root"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta", page_number=2, parent_node_id="sec-2"),
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
        "get_structure",
        "search_headings",
        "jump_to_node",
        "list_internal_links",
        "follow_internal_link",
        "highlight",
        "warning",
        "open_workspace",
        "describe_workspace",
        "read_source",
        "read_body",
        "write_body",
        "patch_body",
        "compile",
        "submit",
    ]
    descriptions = {tool.name: tool.description for tool in tools}
    assert descriptions["current_node"] == "Inspect the current DocWright node. This is usually the first call in each step."
    assert descriptions["get_structure"] == "Inspect parent/children/siblings/ancestry metadata for the current node without changing runtime focus."
    assert descriptions["follow_internal_link"] == "Follow one preserved internal-link relation and update runtime focus to the resolved target node."
    assert descriptions["compile"] == "Compile the current workspace body and return structured success or error details plus the workspace_id."


def test_tool_registry_executes_runtime_navigation_and_workspace_tools() -> None:
    registry = CodexToolRegistry()
    session = make_session(workspace_registry=make_workspace_registry())
    capability = GuidedReadingCapability()

    current = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1", name="current_node"),
    )
    structure = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1a", name="get_structure"),
    )
    searched = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1b", name="search_text", arguments={"query": "alpha", "limit": 5}),
    )
    heading_hits = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1c", name="search_headings", arguments={"query": "Appendix", "limit": 5}),
    )
    links = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1d", name="list_internal_links"),
    )
    jumped = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="1e", name="jump_to_node", arguments={"node_id": "sec-2"}),
    )
    followed = registry.execute_tool(
        session=make_session(workspace_registry=make_workspace_registry()),
        capability=capability,
        call=CodexToolCall(call_id="1f", name="follow_internal_link", arguments={"relation_id": "rel-link-1"}),
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
    source = registry.execute_tool(
        session=session,
        capability=capability,
        call=CodexToolCall(call_id="3c", name="read_source", arguments={"workspace_id": workspace_id}),
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
    assert structure.output["structure"]["parent_node_id"] == "sec-1"
    assert searched.output["hits"][0]["node_id"] == "node-1"
    assert searched.output["hits"][0]["node_kind"] == "paragraph"
    assert heading_hits.output["hits"][0]["node_id"] == "sec-2"
    assert links.output["links"][0]["target_node_id"] == "sec-2"
    assert jumped.output["node"]["node_id"] == "node-2"
    assert followed.output["node"]["node_id"] == "node-2"
    assert highlighted.output["event"]["name"] == "highlight.applied"
    assert opened.output["workspace_id"] == workspace_id
    assert opened.output["workspace"]["workspace_profile"] == "latex_annotation"
    assert opened.output["workspace"]["template_id"] == "default_annotation_tex"
    assert opened.output["workspace"]["body_kind"] == "latex_body"
    assert opened.output["workspace"]["compiler_profile"] == "tectonic"
    assert opened.output["workspace"]["compile_ready"] is True
    assert described.output["workspace_id"] == workspace_id
    assert described.output["workspace"]["workspace_id"] == workspace_id
    assert described.output["workspace"]["workspace_profile"] == "latex_annotation"
    assert source.output["workspace_id"] == workspace_id
    assert r"\documentclass{article}" in source.output["source"]
    assert compiled.output["compile_result"]["ok"] is True
    assert compiled.output["workspace_id"] == workspace_id
    assert submitted.output["workspace_id"] == workspace_id
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
    assert workspace["sandbox_profile"] == "local_process"

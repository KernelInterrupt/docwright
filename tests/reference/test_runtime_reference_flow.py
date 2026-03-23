from dataclasses import dataclass

from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.workspace.models import CompileResult, WorkspaceSessionModel


@dataclass(slots=True)
class FakeCompiler:
    result: CompileResult

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        return self.result


def test_reference_runtime_api_supports_query_action_workspace_and_progression() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
            ],
        ),
        workspace_compiler=FakeCompiler(result=CompileResult(ok=True, backend_name="fake", rendered_content="ok")),
    )

    node = session.current_node()
    assert node is not None
    assert node.node_id == "node-1"
    assert session.get_context(after=1).after_node_ids == ("node-2",)

    node.highlight(level="important", reason="key claim")
    node.warning(kind="risk", severity="low", message="needs follow-up", evidence=("node-1",))
    workspace = node.open_workspace(task="annotation")
    assert workspace.read_body() == "alpha"
    workspace.write_body("updated alpha")
    compiled = workspace.compile()
    submitted = workspace.submit()
    next_node = session.advance()
    completed = session.advance()

    assert compiled.ok is True
    assert submitted == compiled
    assert next_node is not None
    assert next_node.node_id == "node-2"
    assert completed is None
    assert session.model.status is RuntimeSessionStatus.COMPLETED
    assert [event.as_protocol_event().event_name for event in session.events()] == [
        "runtime.started",
        "node.entered",
        "highlight.applied",
        "warning.raised",
        "workspace.opened",
        "workspace.session_created",
        "node.entered",
        "runtime.completed",
    ]

from docwright.adapters.agent.base import AdapterDescriptor
from docwright.adapters.transport.headless import HeadlessRunner
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


class GuidedReadingAdapter:
    descriptor = AdapterDescriptor(name="guided-reading-adapter", transport="headless")

    async def run_step(self, session: RuntimeSession, capability: GuidedReadingCapability | None = None) -> None:
        if capability is None:
            raise AssertionError("guided reading capability is required")
        session.record_highlight(level="important", reason="guided reading")
        session.record_workspace_opened(workspace_id="ws-1", task="annotation")
        session.advance()


def test_guided_reading_runs_through_core_via_adapter_boundary() -> None:
    capability = GuidedReadingCapability()
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
            ],
        ),
        guardrail_policy=capability.guardrail_policy(),
    )
    runner = HeadlessRunner(adapter=GuidedReadingAdapter(), capability=capability)

    events = runner.run_once(session)

    assert session.model.step.node_id == "node-2"
    assert [event.event_name for event in events] == [
        "runtime.started",
        "node.entered",
        "highlight.applied",
        "workspace.opened",
        "node.entered",
    ]

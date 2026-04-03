from docwright.adapters.agent.base import AdapterDescriptor
from docwright.adapters.transport.headless import HeadlessRunner
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


class SmokeAdapter:
    descriptor = AdapterDescriptor(name="smoke-adapter")

    async def run_step(self, session: RuntimeSession, capability: GuidedReadingCapability | None = None) -> None:
        if capability is not None:
            session.record_highlight(level="important", reason="smoke")
        session.advance()


def test_headless_smoke_flow_runs_one_guided_step() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
            ],
        ),
        guardrail_policy=GuidedReadingCapability().guardrail_policy(),
    )

    runner = HeadlessRunner(adapter=SmokeAdapter(), capability=GuidedReadingCapability())
    events = runner.run_once(session)

    assert session.model.step.node_id == "node-2"
    assert [event.event_name for event in events][-2:] == [
        "highlight.applied",
        "node.entered",
    ]

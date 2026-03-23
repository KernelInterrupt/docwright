from dataclasses import dataclass

from docwright.adapters.agent.base import AdapterDescriptor
from docwright.adapters.transport.headless import HeadlessRunner
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


@dataclass(slots=True)
class FakeAdapter:
    descriptor: AdapterDescriptor

    async def run_step(self, session: RuntimeSession, capability: GuidedReadingCapability | None = None) -> None:
        if capability is not None and capability.guardrail_policy().require_highlight_before_advance:
            session.record_highlight(level="important")
        session.advance()


def test_headless_runner_executes_adapter_against_core_session() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph"),
                InMemoryNode(node_id="node-2", kind="paragraph"),
            ],
        ),
        guardrail_policy=GuidedReadingCapability().guardrail_policy(),
    )
    runner = HeadlessRunner(
        adapter=FakeAdapter(descriptor=AdapterDescriptor(name="headless-test")),
        capability=GuidedReadingCapability(),
    )

    events = runner.run_once(session)

    assert session.model.step.node_id == "node-2"
    assert [event.as_protocol_event().event_name for event in events][-2:] == [
        "highlight.applied",
        "node.entered",
    ]


def test_headless_runner_can_drive_session_until_completion() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph"),
                InMemoryNode(node_id="node-2", kind="paragraph"),
            ],
        ),
        guardrail_policy=GuidedReadingCapability().guardrail_policy(),
    )
    runner = HeadlessRunner(
        adapter=FakeAdapter(descriptor=AdapterDescriptor(name="headless-test")),
        capability=GuidedReadingCapability(),
    )

    events = runner.run_until_complete(session)

    assert session.model.status is RuntimeSessionStatus.COMPLETED
    assert [event.as_protocol_event().event_name for event in events][-1] == "runtime.completed"

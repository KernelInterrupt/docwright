import asyncio
from dataclasses import dataclass

from docwright.adapters.agent.base import AdapterDescriptor
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


@dataclass(slots=True)
class HighlightThenAdvanceAdapter:
    descriptor: AdapterDescriptor = AdapterDescriptor(name="test-adapter")

    async def run_step(self, session: RuntimeSession, capability: GuidedReadingCapability | None = None) -> None:
        if capability is not None and capability.guardrail_policy().require_highlight_before_advance:
            session.record_highlight(level="important", reason="adapter-driven")
        session.advance()


def test_adapter_and_capability_consume_core_session_state_instead_of_owning_it() -> None:
    document = InMemoryDocument.from_nodes(
        document_id="doc-1",
        nodes=[
            InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
            InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
        ],
    )
    capability = GuidedReadingCapability()
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=document,
        guardrail_policy=capability.guardrail_policy(),
    )
    adapter = HighlightThenAdvanceAdapter()

    asyncio.run(adapter.run_step(session, capability))

    assert session.model.step.index == 1
    assert session.model.step.node_id == "node-2"
    assert session.model.step.highlight_count == 0
    assert [event.as_protocol_event().event_name for event in session.events()] == [
        "runtime.started",
        "node.entered",
        "highlight.applied",
        "node.entered",
    ]

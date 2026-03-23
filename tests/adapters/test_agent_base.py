import asyncio
from dataclasses import dataclass

from docwright.adapters.agent.base import AdapterDescriptor, AgentAdapter
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


@dataclass(slots=True)
class FakeAdapter:
    descriptor: AdapterDescriptor
    ran: bool = False

    async def run_step(self, session: RuntimeSession, capability: object | None = None) -> None:
        self.ran = True
        session.emit_event("adapter.step_ran", {"adapter": self.descriptor.name})


def test_adapter_descriptor_keeps_runtime_metadata_outside_core() -> None:
    descriptor = AdapterDescriptor(
        name="codex",
        transport="tool-calling",
        metadata={"streaming": True},
    )

    assert descriptor.name == "codex"
    assert descriptor.transport == "tool-calling"
    assert descriptor.metadata == {"streaming": True}


def test_agent_adapter_protocol_supports_run_step_against_core_session() -> None:
    adapter = FakeAdapter(descriptor=AdapterDescriptor(name="codex"))
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[InMemoryNode(node_id="node-1", kind="paragraph")],
        ),
    )

    assert isinstance(adapter, AgentAdapter)

    asyncio.run(adapter.run_step(session))

    assert adapter.ran is True
    assert session.events()[-1].as_protocol_event().event_name == "adapter.step_ran"

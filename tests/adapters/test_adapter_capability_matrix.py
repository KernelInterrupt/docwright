import asyncio
from dataclasses import dataclass

from docwright.adapters.agent.base import AdapterDescriptor
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.core.models import RuntimeSessionModel, RuntimeSessionStatus
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


@dataclass(slots=True)
class GuidedAdapter:
    descriptor: AdapterDescriptor = AdapterDescriptor(name="guided-adapter")

    async def run_step(self, session: RuntimeSession, capability: GuidedReadingCapability | None = None) -> None:
        session.record_highlight(level="important", reason="guided")
        session.advance()


@dataclass(slots=True)
class ManualAdapter:
    descriptor: AdapterDescriptor = AdapterDescriptor(name="manual-adapter")

    async def run_step(self, session: RuntimeSession, capability: ManualTaskCapability | None = None) -> None:
        session.record_warning(kind="note", severity="low", message="manual review")
        session.advance()


def make_session(*, capability_name: str, policy) -> RuntimeSession:
    return RuntimeSession(
        RuntimeSessionModel(
            session_id=f"session-{capability_name}",
            run_id=f"run-{capability_name}",
            document_id="doc-1",
            capability_name=capability_name,
        ),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
            ],
        ),
        guardrail_policy=policy,
    )


def test_core_hosts_multiple_adapter_capability_combinations() -> None:
    guided_capability = GuidedReadingCapability()
    guided_session = make_session(
        capability_name=guided_capability.descriptor.name,
        policy=guided_capability.guardrail_policy(),
    )
    asyncio.run(GuidedAdapter().run_step(guided_session, guided_capability))

    manual_capability = ManualTaskCapability()
    manual_session = make_session(
        capability_name=manual_capability.descriptor.name,
        policy=manual_capability.guardrail_policy(),
    )
    asyncio.run(ManualAdapter().run_step(manual_session, manual_capability))

    assert guided_session.model.status is RuntimeSessionStatus.ACTIVE
    assert manual_session.model.status is RuntimeSessionStatus.ACTIVE
    assert [event.as_protocol_event().event_name for event in guided_session.events()][-2:] == [
        "highlight.applied",
        "node.entered",
    ]
    assert [event.as_protocol_event().event_name for event in manual_session.events()][-2:] == [
        "warning.raised",
        "node.entered",
    ]

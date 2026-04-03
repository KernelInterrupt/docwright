from dataclasses import dataclass

from docwright.adapters.companion.base import CompanionLaunchPlan, CompanionRuntime
from docwright.adapters.transport.headless import HeadlessRunner
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


@dataclass(slots=True)
class FakeCompanion:
    def build_launch_plan(self) -> CompanionLaunchPlan:
        return CompanionLaunchPlan(
            runtime_name="codex-local",
            command=("codex", "run"),
            working_directory="/tmp/demo",
            metadata={"mode": "local_companion"},
        )


class FakeAdapter:
    async def run_step(self, session: RuntimeSession, capability: ManualTaskCapability | None = None) -> None:
        session.record_highlight(level="important")
        session.advance()


def test_companion_boundary_is_host_local_and_not_the_core_runtime_loop() -> None:
    companion = FakeCompanion()
    plan = companion.build_launch_plan()

    assert isinstance(companion, CompanionRuntime)
    assert plan.runtime_name == "codex-local"
    assert plan.command == ("codex", "run")
    assert plan.metadata["mode"] == "local_companion"


def test_core_runtime_still_runs_without_any_companion_dependency() -> None:
    session = RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph"),
                InMemoryNode(node_id="node-2", kind="paragraph"),
            ],
        ),
        guardrail_policy=ManualTaskCapability().guardrail_policy(),
    )

    runner = HeadlessRunner(adapter=FakeAdapter(), capability=ManualTaskCapability())
    events = runner.run_once(session)

    assert session.model.step.node_id == "node-2"
    assert events[-1].event_name == "node.entered"

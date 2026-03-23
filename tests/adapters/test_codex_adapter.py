import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from docwright.adapters.agent.codex import CodexAdapter
from docwright.adapters.agent.codex_types import (
    CodexMessage,
    CodexToolCall,
    CodexToolResult,
    CodexTurnRequest,
    CodexTurnResponse,
)
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.guardrails import GuardrailViolationError
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.workspace.models import CompileResult, WorkspaceSessionModel


@dataclass(slots=True)
class FakeCompiler:
    result: CompileResult

    def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
        return self.result


@dataclass(slots=True)
class FakeCodexDriver:
    responses: list[CodexTurnResponse] = field(default_factory=list)
    requests: list[CodexTurnRequest] = field(default_factory=list)
    responder: Callable[[CodexTurnRequest], CodexTurnResponse] | None = None

    async def next_turn(self, request: CodexTurnRequest) -> CodexTurnResponse:
        self.requests.append(request)
        if self.responder is not None:
            return self.responder(request)
        if not self.responses:
            raise AssertionError("No fake Codex responses remaining")
        return self.responses.pop(0)


def make_session(*, with_compiler: bool = False) -> RuntimeSession:
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
        workspace_compiler=(
            FakeCompiler(result=CompileResult(ok=True, backend_name="fake", rendered_content="ok"))
            if with_compiler
            else None
        ),
    )


async def _run(adapter: CodexAdapter, session: RuntimeSession) -> None:
    await adapter.run_step(session, GuidedReadingCapability())


def test_codex_adapter_exports_step_contract(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("Prefer tools.", encoding="utf-8")
    adapter = CodexAdapter(agents_md_path=agents_path)
    session = make_session()

    contract = adapter.describe_step(session, GuidedReadingCapability())

    assert contract.metadata == {
        "session_id": "session-1",
        "run_id": "run-1",
        "capability": "guided_reading",
        "adapter": "codex",
    }
    assert "Prefer tools." in contract.instructions
    assert "Codex-side agent operating DocWright through tools" in contract.instructions
    assert "Current node: node-1" in contract.turn_prompt
    assert [tool.name for tool in contract.tools][:3] == ["current_node", "get_context", "advance"]


def test_codex_adapter_fake_driver_runs_loop_until_tool_calls_stop() -> None:
    driver = FakeCodexDriver(
        responses=[
            CodexTurnResponse(
                tool_calls=(
                    CodexToolCall(call_id="call-1", name="current_node"),
                    CodexToolCall(call_id="call-2", name="highlight", arguments={"level": "important"}),
                    CodexToolCall(call_id="call-3", name="advance"),
                ),
            ),
            CodexTurnResponse(output_text="Step complete.", stop_reason="done"),
        ]
    )
    adapter = CodexAdapter(driver=driver)
    session = make_session()

    asyncio.run(_run(adapter, session))

    assert len(driver.requests) == 2
    assert driver.requests[0].contract.metadata["adapter"] == "codex"
    assert isinstance(driver.requests[0].input_items[0], CodexMessage)
    assert isinstance(driver.requests[1].input_items[-1], CodexToolResult)
    assert session.model.step.node_id == "node-2"
    assert [event.as_protocol_event().event_name for event in session.events()][-2:] == [
        "node.entered",
        "adapter.codex_output",
    ]


def test_codex_adapter_smoke_proves_highlight_before_advance_guardrail() -> None:
    driver = FakeCodexDriver(
        responses=[
            CodexTurnResponse(
                tool_calls=(CodexToolCall(call_id="call-1", name="advance"),),
            )
        ]
    )
    adapter = CodexAdapter(driver=driver)
    session = make_session()

    with pytest.raises(GuardrailViolationError) as exc_info:
        asyncio.run(_run(adapter, session))

    assert exc_info.value.violation.code.value == "highlight_required_before_advance"


def test_codex_adapter_smoke_runs_workspace_lifecycle_through_bridge() -> None:
    state = {"iteration": 0}

    def responder(request: CodexTurnRequest) -> CodexTurnResponse:
        state["iteration"] += 1
        if state["iteration"] == 1:
            return CodexTurnResponse(
                tool_calls=(
                    CodexToolCall(call_id="call-1", name="highlight", arguments={"level": "important"}),
                    CodexToolCall(call_id="call-2", name="open_workspace", arguments={"task": "annotation"}),
                )
            )

        workspace_result = next(
            item
            for item in request.input_items
            if isinstance(item, CodexToolResult) and item.name == "open_workspace"
        )
        workspace_id = workspace_result.output["workspace"]["workspace_id"]

        if state["iteration"] == 2:
            return CodexTurnResponse(
                tool_calls=(
                    CodexToolCall(
                        call_id="call-3",
                        name="write_body",
                        arguments={"workspace_id": workspace_id, "content": "annotated alpha"},
                    ),
                    CodexToolCall(
                        call_id="call-4",
                        name="compile",
                        arguments={"workspace_id": workspace_id},
                    ),
                    CodexToolCall(
                        call_id="call-5",
                        name="submit",
                        arguments={"workspace_id": workspace_id},
                    ),
                    CodexToolCall(call_id="call-6", name="advance"),
                )
            )

        return CodexTurnResponse(output_text="Workspace step complete.", stop_reason="done")

    driver = FakeCodexDriver(responder=responder)
    adapter = CodexAdapter(driver=driver)
    session = make_session(with_compiler=True)

    asyncio.run(_run(adapter, session))

    assert len(driver.requests) == 3
    workspace = session.workspaces()[0]
    assert workspace.model.current_body == "annotated alpha"
    assert workspace.model.state.value == "submitted"
    assert workspace.model.history[-1].action == "workspace.submitted"
    assert session.model.step.node_id == "node-2"

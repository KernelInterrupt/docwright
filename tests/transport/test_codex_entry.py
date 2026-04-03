import pytest

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.codex.entry import DocWrightCodexEntry
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.core.guardrails import GuardrailViolationError
from docwright.document.facade import MissingDocumentBackendError
from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.workspace.models import CompileResult, WorkspaceSessionModel
from docwright.workspace.registry import WorkspaceProfileRegistry


def make_document() -> InMemoryDocument:
    return InMemoryDocument.from_nodes(
        document_id="doc-1",
        nodes=[
            InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
            InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
        ],
    )


def test_codex_entry_builds_runtime_session_and_bridge_from_document() -> None:
    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=ManualTaskCapability(),
        session_id="session-x",
        run_id="run-x",
    )

    contract = entry.export_step()

    assert entry.session.model.document_id == "doc-1"
    assert entry.session.model.session_id == "session-x"
    assert entry.session.model.run_id == "run-x"
    assert entry.session.model.capability_name == "manual_task"
    assert entry.session.model.adapter_name == "codex"
    assert contract.metadata["session_id"] == "session-x"
    assert contract.metadata["document_id"] == "doc-1"
    assert contract.metadata["current_node_id"] == "node-1"
    assert contract.metadata["capability"] == "manual_task"
    assert contract.metadata["workspace_registry_ready"] is True


def test_codex_entry_uses_capability_guardrails_by_default() -> None:
    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=GuidedReadingCapability(),
    )

    with pytest.raises(GuardrailViolationError):
        entry.execute_tool_call(CodexToolCall(call_id="1", name="advance"))


def test_codex_entry_delegates_usage_snapshot() -> None:
    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=ManualTaskCapability(),
    )

    entry.export_step()
    entry.stream_output_delta(text_delta="abc")
    usage = entry.usage_snapshot()

    assert usage.step_exports == 1
    assert usage.output_deltas == 1
    assert usage.output_delta_chars == 3


def test_codex_entry_from_pdf_uses_document_backend_and_builds_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_payload = {
        "document_id": "paper.pdf",
        "root_id": "root",
        "nodes": {
            "root": {"id": "root", "kind": "document"},
            "node-1": {"id": "node-1", "kind": "paragraph", "parent_id": "root", "text": "alpha"},
        },
        "reading_order": ["node-1"],
    }
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_ir_converter(path: str, **kwargs: object) -> dict[str, object]:
        calls.append((path, dict(kwargs)))
        return fake_payload

    monkeypatch.setattr("docwright.adapters.transport.codex_entry.ir_converter", fake_ir_converter)

    entry = DocWrightCodexEntry.from_pdf(
        "paper.pdf",
        goal="read and structure this document",
        document_backend_kwargs={"mode": "accurate"},
        capability=ManualTaskCapability(),
        session_id="pdf-session",
        run_id="pdf-run",
    )

    contract = entry.export_step()

    assert calls == [("paper.pdf", {"mode": "accurate", "goal": "read and structure this document"})]
    assert entry.session.model.document_id == "paper.pdf"
    assert contract.metadata["session_id"] == "pdf-session"
    assert contract.metadata["document_id"] == "paper.pdf"
    assert contract.metadata["current_node_id"] == "node-1"


def test_codex_entry_from_pdf_surfaces_missing_document_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_ir_converter(path: str, **kwargs: object) -> object:
        raise MissingDocumentBackendError("backend missing")

    monkeypatch.setattr("docwright.adapters.transport.codex_entry.ir_converter", fake_ir_converter)

    with pytest.raises(MissingDocumentBackendError, match="backend missing"):
        DocWrightCodexEntry.from_pdf("paper.pdf")


def test_codex_entry_auto_wires_default_workspace_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = WorkspaceProfileRegistry()
    calls: list[tuple[str, object]] = []

    class FakeCompiler:
        def describe(self) -> dict[str, object]:
            return {
                "name": "latex_workspace",
                "profile": "pdflatex",
                "sandbox_backend": "bubblewrap",
                "available": True,
                "details": {},
            }

        def compile(self, workspace: WorkspaceSessionModel) -> CompileResult:
            return CompileResult(ok=True, backend_name="latex:pdflatex", rendered_content="ok")

    monkeypatch.setattr(
        "docwright.adapters.transport.codex_entry.select_default_latex_compiler_profile",
        lambda: "pdflatex",
    )
    monkeypatch.setattr(
        "docwright.adapters.transport.codex_entry.select_default_workspace_sandbox_profile",
        lambda: "bubblewrap",
    )

    def fake_build_default_workspace_registry(*, compiler_profile: str | None, sandbox_profile: str | None) -> WorkspaceProfileRegistry:
        calls.append(("registry", (compiler_profile, sandbox_profile)))
        return registry

    def fake_build_default_latex_workspace_compiler(*, profile: str | None) -> FakeCompiler:
        calls.append(("compiler", profile))
        return FakeCompiler()

    monkeypatch.setattr(
        "docwright.adapters.transport.codex_entry.build_default_workspace_registry",
        fake_build_default_workspace_registry,
    )
    monkeypatch.setattr(
        "docwright.adapters.transport.codex_entry.build_default_latex_workspace_compiler",
        fake_build_default_latex_workspace_compiler,
    )

    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=ManualTaskCapability(),
    )

    contract = entry.export_step()

    assert calls == [("registry", ("pdflatex", "bubblewrap")), ("compiler", "pdflatex")]
    assert entry.session.workspace_registry is registry
    assert contract.metadata["workspace_registry_ready"] is True
    assert contract.metadata["workspace_compile_ready"] is True
    assert contract.metadata["workspace_compiler"]["profile"] == "pdflatex"


def test_codex_entry_hides_compile_tools_when_default_compiler_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = WorkspaceProfileRegistry()

    monkeypatch.setattr(
        "docwright.adapters.transport.codex_entry.select_default_latex_compiler_profile",
        lambda: None,
    )
    monkeypatch.setattr(
        "docwright.adapters.transport.codex_entry.build_default_workspace_registry",
        lambda **kwargs: registry,
    )

    entry = DocWrightCodexEntry.from_document(
        make_document(),
        capability=ManualTaskCapability(),
    )

    tools = [tool.name for tool in entry.export_step().tools]

    assert "open_workspace" in tools
    assert "compile" not in tools
    assert "submit" not in tools

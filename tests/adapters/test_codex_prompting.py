from pathlib import Path

from docwright.adapters.agent.codex_prompting import CodexPromptAssembler, load_agents_md
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.core.models import RuntimeSessionModel
from docwright.core.session import RuntimeSession
from docwright.document.handles import InMemoryDocument, InMemoryNode


def make_session() -> RuntimeSession:
    return RuntimeSession(
        RuntimeSessionModel(session_id="session-1", run_id="run-1", document_id="doc-1"),
        document=InMemoryDocument.from_nodes(
            document_id="doc-1",
            nodes=[
                InMemoryNode(node_id="node-1", kind="paragraph", text="alpha"),
                InMemoryNode(node_id="node-2", kind="paragraph", text="beta"),
            ],
        ),
    )


def test_load_agents_md_is_optional(tmp_path: Path) -> None:
    assert load_agents_md(None) is None
    path = tmp_path / "AGENTS.md"
    path.write_text("Use tools first.", encoding="utf-8")
    assert load_agents_md(path) == "Use tools first."


def test_prompt_assembler_renders_capability_and_context() -> None:
    assembler = CodexPromptAssembler()
    session = make_session()
    capability = GuidedReadingCapability()

    instructions = assembler.build_instructions(session, capability, agents_md_text="Repo rule.")
    turn_prompt = assembler.build_turn_prompt(session)

    assert "Codex-side agent operating DocWright through tools" in instructions
    assert "Active capability: guided_reading" in instructions
    assert "highlight is required before advance" in instructions
    assert "workspace_editing" in instructions
    assert "session=session-1, run=run-1" in instructions
    assert "Repo rule." in instructions
    assert "Current node: node-1" in turn_prompt
    assert "after: node-2" in turn_prompt

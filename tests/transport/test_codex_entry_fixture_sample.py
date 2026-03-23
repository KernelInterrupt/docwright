from pathlib import Path
import runpy

from docwright.adapters.agent.codex_types import CodexToolCall
from docwright.capabilities.guided_reading import GuidedReadingCapability
from docwright.capabilities.manual_task import ManualTaskCapability

SAMPLE_PATH = Path(__file__).resolve().parents[2] / "codex_entry" / "samples" / "attention_fixture.py"
MODULE = runpy.run_path(str(SAMPLE_PATH))
FIXTURE_PATH = MODULE["FIXTURE_PATH"]
build_attention_fixture_entry = MODULE["build_attention_fixture_entry"]


def test_attention_fixture_sample_builds_optional_entry_without_binding_main_bridge() -> None:
    entry = build_attention_fixture_entry(
        capability=ManualTaskCapability(),
        session_id="fixture-session",
        run_id="fixture-run",
    )

    contract = entry.export_step()

    assert FIXTURE_PATH.exists() is True
    assert entry.session.model.document_id == "attention_is_all_you_need.pdf"
    assert entry.session.model.session_id == "fixture-session"
    assert entry.session.model.capability_name == "manual_task"
    assert contract.metadata["capability"] == "manual_task"
    assert contract.turn_prompt.startswith("Run one DocWright step for session fixture-session.")


def test_attention_fixture_sample_still_respects_selected_capability() -> None:
    entry = build_attention_fixture_entry(capability=GuidedReadingCapability())

    result = entry.execute_tool_call(CodexToolCall(call_id="1", name="highlight", arguments={"level": "important"}))

    assert result.name == "highlight"
    assert entry.session.model.step.highlight_count == 1

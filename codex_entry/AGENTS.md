# DocWright Codex Entry

You are starting inside the recommended Codex launch folder for DocWright.

## Goal
Connect a Codex-style host to DocWright through the direct-library bridge, not
through an OpenAI client wrapper.

## Primary entry surface
Use:
- `../src/docwright/adapters/transport/codex_entry.py`
- `DocWrightCodexEntry.from_document(...)`

That gives you:
- a live `RuntimeSession`
- a `CodexLibraryBridge`
- the standard Codex-facing methods:
  - `export_step()`
  - `execute_tool_call(...)`
  - `execute_tool_calls(...)`
  - `stream_output_delta(...)`
  - `record_output(...)`
  - `usage_snapshot()`

## Read these first when changing the bridge
1. `../docs/bootstrap_status_v1.md`
2. `../docs/codex_adapter_design_v1.md`
3. `../docs/codex_direct_library_integration_v1.md`
4. `../docs/codex_adapter_execution_checklist_v1.md`

## Architecture rules
Keep boundaries clean:
- Core
- Agent Adapter
- Capability Profile
- Skill / Tool Bundle
- Workspace Session

Do not reintroduce provider-specific client logic into Core.

## Contract references
Use these fixtures as stable external-host baselines:
- `../tests/fixtures/codex/guided_reading_step_contract.json`
- `../tests/fixtures/codex/manual_task_navigation_transcript.json`

## Optional fixture sample
Use `samples/attention_fixture.py` if you want a ready-made demo input from the prepared Document IR fixture. This is optional and must not replace the generic `DocWrightCodexEntry.from_document(...)` path.

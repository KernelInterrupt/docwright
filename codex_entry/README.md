# Codex Entry Folder

This folder is the recommended place to **start Codex** when you want a session
focused on connecting Codex to DocWright.

## Why this folder exists
Starting Codex here gives it a local `AGENTS.md` that points directly at the
DocWright direct-library bridge instead of the broader repository surface.

## Recommended runtime entry
Use the launch helper:
- `../src/docwright/adapters/transport/codex_entry.py`
- `DocWrightCodexEntry.from_document(...)`

This is the shortest setup path to:
- create a `RuntimeSession`
- attach a `CodexLibraryBridge`
- export the current step contract
- execute tool calls
- stream output deltas
- record final output
- inspect usage/tracing state

## Typical flow
1. build a document handle
2. create `DocWrightCodexEntry.from_document(...)`
3. call `export_step()`
4. feed the returned tools/instructions to Codex
5. route tool calls back through `execute_tool_call(...)`
6. optionally call `stream_output_delta(...)`
7. call `record_output(...)` when the step ends

## Key docs
- `../docs/codex_direct_library_integration_v1.md`
- `../docs/codex_adapter_design_v1.md`
- `../docs/codex_adapter_execution_checklist_v1.md`

## Optional fixture sample
Use `samples/attention_fixture.py` if you want a ready-made demo input from the prepared Document IR fixture. This is optional and must not replace the generic `DocWrightCodexEntry.from_document(...)` path.

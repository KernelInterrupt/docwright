# Codex Direct-Library Integration v1

This document describes the **Playwright-like direct-library integration** for
DocWright's Codex-compatible bridge.

The important idea is:

- Codex is the caller
- DocWright is the library/runtime being called
- `AGENTS.md` is guidance only
- MCP is optional, not required for the first integration path

---

## 1. Target shape

The intended integration looks like this:

```text
Codex host runtime
    -> import DocWright bridge/library
    -> ask for current step contract
    -> call DocWright tools
    -> send tool results back into Codex reasoning
    -> record final output on the DocWright session
```

This is analogous to how an agent host uses Playwright as a library.

---

## 2. Current public bridge surface

### `CodexAdapter`
Primary bridge object in:
- `src/docwright/adapters/agent/codex.py`

Current responsibilities:
- `describe_step(...)`
- `execute_tool_call(...)`
- `execute_tool_calls(...)`
- `stream_output_delta(...)`
- `record_output(...)`
- `usage_snapshot()`

### `CodexLibraryBridge`
Small host-facing helper in:
- `src/docwright/adapters/transport/codex_library.py`

This wraps a live:
- `RuntimeSession`
- optional `CapabilityProfile`
- `CodexAdapter`

and exposes a direct-library host flow.

### `DocWrightCodexEntry`
Launch-oriented setup helper in:
- `src/docwright/adapters/transport/codex_entry.py`

This is the shortest bootstrap path when a host wants to create a fresh
`RuntimeSession` directly from a `DocumentHandle`.

There is also an optional repo-local sample at:
- `../codex_entry/samples/attention_fixture.py`

That sample loads the prepared Document IR fixture for demos only; it is not the
main integration contract.

---

## 3. Host-side flow

A minimal host loop is:

1. create a `RuntimeSession`
2. choose a `CapabilityProfile`
3. create `DocWrightCodexEntry.from_document(...)` or `CodexLibraryBridge(...)`
4. call `export_step()`
5. give Codex:
   - `instructions`
   - `turn_prompt`
   - `tools` (with skill-provided descriptions where available)
6. when Codex emits a tool call, convert it to `CodexToolCall`
7. call `execute_tool_call(...)`
8. give the `CodexToolResult` back to Codex
9. optionally forward output deltas with `stream_output_delta(...)`
10. when Codex finishes a step, call `record_output(...)`
11. inspect `usage_snapshot()` if the host wants counters/tracing summaries
12. repeat until the DocWright session is terminal

---

## 4. Example

```python
bridge = CodexLibraryBridge(session=session, capability=capability)
contract = bridge.export_step()

# host gives Codex these values
instructions = contract.instructions
turn_prompt = contract.turn_prompt
tools = contract.tools

result = bridge.execute_tool_call(
    CodexToolCall(call_id="1", name="current_node", arguments={})
)

bridge.record_output(output_text="Step complete.", stop_reason="done")
```

The host keeps the Codex model loop.
DocWright keeps runtime state, guardrails, and workspace lifecycle.

---

## 5. What the host must not do

The host must not:
- bypass DocWright guardrails
- mutate runtime/session state directly instead of using tools
- treat `AGENTS.md` as runtime state
- move provider-specific SDK logic into Core modules

---

## 6. `AGENTS.md` role

`AGENTS.md` can help Codex understand repository conventions, but it does not:
- define tools
- replace exported step contracts
- replace workspace state
- replace bridge execution APIs

---

## 7. Streaming / event hooks

The bridge now supports transport-neutral observer hooks for external runtimes.

Current hook categories include:
- `step_exported`
- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`
- `runtime_events_emitted`
- `output_delta`
- `output_recorded`

The adapter also exposes:
- structured trace sinks
- adapter-local usage counters via `usage_snapshot()`

This lets a Codex host:
- observe step exports
- forward streaming text deltas through `stream_output_delta(...)`
- observe structured runtime events emitted by Core after tool execution
- observe final recorded model output

These hooks are for observability and host coordination. They do not move
provider-specific streaming protocols into Core itself.

---

## 8. MCP relation

If later needed, MCP can wrap this direct-library bridge.
But the bridge itself is the stable Core-facing abstraction.

That means the layering stays:

```text
Codex host -> direct DocWright bridge -> DocWright Core
```

and only later optionally:

```text
Codex host -> MCP wrapper -> direct DocWright bridge -> DocWright Core
```

---


## 9. Fixture references

The repository now includes stable Codex-facing fixture exports for external hosts:
- `tests/fixtures/codex/guided_reading_step_contract.json`
- `tests/fixtures/codex/manual_task_navigation_transcript.json`

These fixtures act as regression baselines for hosts that need to understand:
- exported step contract shape
- tool call payload shape
- tool result payload shape
- a minimal direct-library transcript flow

---

## 10. What still remains

This direct-library path is now defined, but future hardening can still add:
- optional MCP exposure

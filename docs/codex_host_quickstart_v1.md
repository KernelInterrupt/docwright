# Codex Host Quickstart v1

This is the shortest **Playwright-like direct-library** recipe for connecting a
Codex-style host to DocWright.

Default sample:
- `tests/fixtures/document_ir/attention_is_all_you_need.document_ir.json`

Canonical entry:
- `DocWrightCodexEntry.from_document(...)`

---

## 1. Bootstrap the runtime

```python
from docwright.document import load_in_memory_document_from_ir_path
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.codex.entry import DocWrightCodexEntry

document = load_in_memory_document_from_ir_path(
    "tests/fixtures/document_ir/attention_is_all_you_need.document_ir.json"
)

entry = DocWrightCodexEntry.from_document(
    document,
    capability=ManualTaskCapability(),
    session_id="attention-demo-session",
    run_id="attention-demo-run",
)
```

For a real PDF-first consumer flow, the shortest shortcut is now:

```python
entry = DocWrightCodexEntry.from_pdf(
    "paper.pdf",
    goal="read and structure this document",
)
```

Internally this still resolves through the optional document facade before
entering the runtime:

```python
from docwright import document
from docwright.document import in_memory_document_from_ir

ir_payload = document.ir_converter("paper.pdf")
document_handle = in_memory_document_from_ir(ir_payload)
entry = DocWrightCodexEntry.from_document(document_handle, ...)
```

---

## 2. Export one step

```python
contract = entry.export_step()
```

Give the host model:
- `contract.instructions`
- `contract.turn_prompt`
- `contract.tools`
- `contract.metadata` (including workspace readiness fields such as `workspace_registry_ready`, `workspace_compile_ready`, and `workspace_compiler`)

---

## 3. Execute tool calls

```python
from docwright.adapters.agent.codex_types import CodexToolCall

current = entry.execute_tool_call(CodexToolCall(call_id="1", name="current_node"))
structure = entry.execute_tool_call(CodexToolCall(call_id="2", name="get_structure"))
search = entry.execute_tool_call(
    CodexToolCall(call_id="3", name="search_text", arguments={"query": "attention", "limit": 5})
)
```

Feed the structured result back into the model loop.

---

## 4. Finish the step

```python
entry.record_output(output_text="Step complete.", stop_reason="done")
```

---

## 5. Stable operating rules

1. Do not read raw IR JSON as the main interaction surface.
2. Use tool schemas exactly.
3. For sequential reading, prefer:
   - `current_node`
   - `get_context` and/or `search_text`
   - `advance`
4. For non-linear documents, prefer:
   - `current_node`
   - `get_structure`
   - `search_headings` and/or scoped `search_text`
   - `jump_to_node` or `follow_internal_link`
5. For workspace edits, prefer:
   - `open_workspace`
   - `describe_workspace`
   - `read_source` and/or `read_body`
   - `write_body` or `patch_body`
   - `compile` / `submit` only when those tools are exported and the workspace reports readiness
6. Let DocWright own state, guardrails, and workspace lifecycle.

Default entry behavior:
- `DocWrightCodexEntry.from_document(...)` auto-provisions the built-in workspace registry
- if a supported built-in LaTeX compiler is detected, compiler-dependent tools are also exported
- otherwise `compile` / `submit` stay off the tool surface by default

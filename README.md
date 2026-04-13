# DocWright

DocWright is a Playwright-like runtime for **structured document interaction**.

It is designed for model-driven agents that need to:
- navigate a document through stable runtime state
- use explicit tools instead of guessing over raw blobs
- open controlled workspaces for annotation/editing tasks
- operate through clean Core / Adapter / Capability / Skill boundaries

It is **not** a chatbot and **not** a one-shot summarizer.

---

## What DocWright is trying to be

Think of DocWright as:
- a **document runtime**
- a **stateful automation kernel** for document agents
- a runtime organized around explicit document targets / node references
- a runtime that supports structure inspection and non-linear targeting first, with traversal strategies layered on top
- a host for multiple agent runtimes such as Codex-like systems

Not as:
- generic chat over PDF text
- a parser dump
- product-specific prompt logic hardcoded into the runtime

---

## Current package shape

This repository currently ships a unified Python package:

```bash
pip install -e .
```

Package name:
- `docwright`

Planned optional install shapes:

```bash
pip install -e '.[document]'
pip install -e '.[latex]'
pip install -e '.[full]'
```

These extras are the forward-compatible user-facing shape for a future split into separately maintained backend repos.

---

## Unified facade direction

The user-facing surface should remain a single package:

```python
import docwright
```

Even if heavier backends move to other repos later, the intended public API stays under `docwright.*`.

### Lazy optional document backend

```python
from docwright import document

status = document.document_backend_status()
# {'available': False, 'provider': None}
```

Optional conversion stays lazy:

```python
from docwright import document

document.ir_converter("paper.pdf")
```

If the optional backend is not installed:
- `import docwright` stays safe
- `import docwright.document` stays safe
- only the actual conversion call raises a clear install hint

Boundary summary:
- `docwright.document` keeps runtime-facing handles, fixture loaders, and the lazy facade
- `docwright-document` owns concrete ingestion, parsing, and IR conversion/enrichment

---

## Official sample baseline

The default professional sample for this repository is always:

- `Attention Is All You Need`
- fixture path: `tests/fixtures/document_ir/attention_is_all_you_need.document_ir.json`

Ad hoc local PDFs may be useful for one-off experiments, but they are **not**
the canonical sample used to explain the API shape.

---

## Quick start

### 1. Canonical host entry: load a document, then create `DocWrightCodexEntry`

```python
from docwright.document import load_in_memory_document_from_ir_path
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.codex.entry import DocWrightCodexEntry

path = "tests/fixtures/document_ir/attention_is_all_you_need.document_ir.json"
document = load_in_memory_document_from_ir_path(path)

entry = DocWrightCodexEntry.from_document(
    document,
    capability=ManualTaskCapability(),
    session_id="demo-session",
    run_id="demo-run",
)
```

This is the primary direct-library bootstrap path.

Hosts should treat:

```python
DocWrightCodexEntry.from_document(document, ...)
```

as the stable integration contract.

For real consumers, there is now also a PDF-first shortcut:

```python
from docwright.codex.entry import DocWrightCodexEntry

entry = DocWrightCodexEntry.from_pdf(
    "paper.pdf",
    goal="read and structure this document",
)
```

Internally, this still follows the same clean layering:

```python
ir_payload = document.ir_converter("paper.pdf")
document_handle = in_memory_document_from_ir(ir_payload)
entry = DocWrightCodexEntry.from_document(document_handle, ...)
```

### 2. Export one step contract for a Codex-like host

```python
contract = entry.export_step()
print(contract.turn_prompt)
print([tool.name for tool in contract.tools])
```

`export_step().metadata` also reports whether the default workspace stack is
ready, including:
- `workspace_registry_ready`
- `workspace_compile_ready`
- `workspace_compiler`

### 3. Execute tool calls against the runtime

```python
from docwright.adapters.agent.codex_types import CodexToolCall

structure = entry.execute_tool_call(CodexToolCall(call_id="2", name="get_structure"))
search = entry.execute_tool_call(
    CodexToolCall(call_id="3", name="search_text", arguments={"query": "attention", "limit": 3})
)
headings = entry.execute_tool_call(
    CodexToolCall(call_id="4", name="search_headings", arguments={"query": "results", "limit": 3})
)
jumped = entry.execute_tool_call(CodexToolCall(call_id="5", name="jump_to_node", arguments={"node_id": "sec_intro"}))
```

### 4. Recommended host loop

The intended host loop is:

1. `export_step()`
2. give Codex:
   - `instructions`
   - `turn_prompt`
   - `tools`
3. receive a structured tool call
4. run `execute_tool_call(...)`
5. send the `CodexToolResult` back into the model loop
6. call `record_output(...)` when the step finishes

This is the Playwright-like direct-library shape for DocWright.

An optional MCP wrapper can sit on top of the same bridge for hosts that prefer
MCP-style tool exposure, but MCP is not the canonical integration path and does
not replace the direct-library contract.

---

## Codex host operating rules

For low-error host usage, keep these rules stable:

1. **Do not read raw IR JSON as the main interaction surface.**
   Use the runtime entry plus exported tools.
2. **Use tool schemas exactly.**
   Do not add extra keys.
3. **Prefer explicit target selection over implicit cursor-style reading.**
   Use `get_structure`, `search_headings`, scoped `search_text`, `jump_to_node`, and `follow_internal_link` to identify the node you intend to inspect or act on.
4. **Treat sequential-reading tools as legacy compatibility paths.**
   If `current_node` or `advance` are still exposed, treat them as older traversal helpers rather than the long-term runtime center.
5. **For workspace edits, prefer this order:**
   - `open_workspace`
   - `describe_workspace`
   - `read_source` and/or `read_body`
   - `write_body` or `patch_body`
   - `compile` and `submit` only when those tools are exported and the workspace reports readiness
6. **Do not bypass runtime guardrails.**
   DocWright owns reading order, workspace lifecycle, and session state.

By default, `DocWrightCodexEntry.from_document(...)` now auto-provisions the
built-in workspace registry. When a supported LaTeX toolchain is available, it
also auto-provisions the built-in compiler; otherwise compiler-dependent tools
stay hidden instead of advertising an unusable compile path.

---

## Optional packaged sample

For demo/test convenience only:

```python
from docwright.capabilities.manual_task import ManualTaskCapability
from docwright.codex.samples.attention_fixture import build_attention_fixture_entry

entry = build_attention_fixture_entry(capability=ManualTaskCapability())
contract = entry.export_step()
```

This sample helper is intentionally thin.
The stable integration contract remains:

```python
DocWrightCodexEntry.from_document(document, ...)
```

---

## Official Attention smoke / demo

The installed package now includes an official Attention-based smoke module:

```python
from docwright.codex.samples.attention_smoke import run_attention_fixture_smoke

result = run_attention_fixture_smoke()
print(result["contract"]["metadata"])
print(result["tool_results"][0]["name"])
```

This demo intentionally uses the canonical path internally:

- load Attention IR fixture as a `DocumentHandle`
- construct `DocWrightCodexEntry.from_document(...)`
- export a step contract
- execute explicit runtime targeting and inspection tools
- demonstrate the baseline direct-library loop before richer locator-backed flows land

---

## What is implemented right now

Current baseline includes:
- runtime sessions with structure inspection, scoped keyword search, heading search, jump/follow-link navigation, highlight, warning, open-workspace, and compatibility-era cursor actions
- action-capable runtime node views over document handles
- workspace sessions with read/write/patch/read-source/compile/submit lifecycle
- executable workspace templates with declarative editable-region rules and assembled-source views
- built-in annotation-first workspace registry plus runtime-level workspace profile/template resolution
- annotation-first LaTeX compiler profiles with structured diagnostics/artifacts
- local-process sandbox backend for workspace compilation plus structured compiler/sandbox metadata
- bubblewrap-backed strong sandbox option for tighter filesystem/process isolation on supported hosts, now preferred by the built-in default compiler path
- structured workspace description via `describe_workspace`
- transport-neutral protocol commands, events, and serialization helpers
- minimal render protocol for externally visible agent tool-call traces
- document interfaces plus in-memory document handles
- lightweight in-repo IR loader
- lazy `docwright.document` facade for optional external document backends
- adapter / capability / skill interfaces
- `guided_reading` and `manual_task` capability scaffolds
- Codex-compatible direct-library bridge and installed entry surface
- smoke, lifecycle, integration, and serialization tests

---

## Architecture snapshot

```text
docwright-document   -> document ingestion + IR + selectors
       |
       v
docwright-core       -> runtime, sessions, guardrails, events, tool API
       |
       v
agent adapters       -> codex, openclaw, custom runtimes, etc.
       |
       v
capability profiles  -> guided reading, review, manual task, etc.
       |
       v
skill/tool bundles   -> navigation, highlighting, warnings, workspace editing
       |
       v
docwright-app        -> UI / frontend / intervention loop
```

### Important boundaries

DocWright distinguishes:
- **Core**
- **Agent Adapter**
- **Capability Profile**
- **Skill / Tool Bundle**
- **Workspace Session**

These should not be collapsed back into one vague “agent profile” abstraction.

---

## Workspace direction

Workspace is currently treated as a **general controlled editing framework**.

Important current decisions:
- workspace is **not** direct `DocumentIR` mutation
- workspace is **not** the same thing as sandbox execution
- annotation is the first strong special case
- workspace rules are now declarative, executable, and visible through workspace metadata
- annotation-first LaTeX compilation can run through an optional local sandbox backend

Relevant docs:
- `docs/workspace_session_contract_v1.md`
- `docs/workspace_sandbox_design_v1.md`
- `docs/workspace_profile_design_v1.md`
- `docs/codex_host_quickstart_v1.md`
- `docs/codex_attention_host_checklist_v1.md`
- `docs/navigation_runtime_requirements_v1.md`
- `docs/navigation_runtime_checklist_v1.md`

---

## What this repo intentionally does not own

This repository does **not** aim to own:
- PDF/OCR/VLM ingestion pipelines
- parser-specific IR generation
- provider-specific integration sprawl
- frontend or API product layers
- large prompt/business logic bundles inside Core modules

---

## Key docs

Read these first when resuming work after context compression:
1. `docs/bootstrap_status_v1.md`
2. `docs/implementation_master_plan_v1.md`
3. `docs/execution_checklist_v1.md`

Other important docs:
- `docs/core_agent_boundary_v1.md`
- `docs/agent_integration_model_v1.md`
- `docs/document_ir_contract_v1.md`
- `docs/docwright_document_boundary_v1.md`
- `docs/node_ref_locator_migration_v1.md`
- `docs/node_ref_compatibility_layer_v1.md`
- `docs/node_ref_locator_execution_checklist_v1.md`
- `docs/runtime_api_contract_v1.md`
- `docs/codex_adapter_design_v1.md`
- `docs/codex_direct_library_integration_v1.md`

Migration note:
- the currently implemented API still exposes `current_node` / `advance`
- the planned public direction is `NodeRef` / `Locator` centered and is tracked in `docs/node_ref_locator_migration_v1.md`

---

## Status

The original R1-R8 execution checklist is complete.

The repository is now a tested, working runtime baseline with:
- Codex-facing direct-library integration
- installable `docwright` package shape
- workspace profile/template groundwork
- unified document facade groundwork

---

## License

Apache License 2.0. See `LICENSE`.

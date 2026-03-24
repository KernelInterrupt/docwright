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

---

## Quick start

### 1. Load a prepared Document IR fixture into the runtime

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

### 2. Export one step contract for an agent host

```python
contract = entry.export_step()
print(contract.turn_prompt)
print([tool.name for tool in contract.tools])
```

### 3. Execute tool calls against the runtime

```python
from docwright.adapters.agent.codex_types import CodexToolCall

result = entry.execute_tool_call(
    CodexToolCall(call_id="1", name="current_node")
)
```

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

## What is implemented right now

Current baseline includes:
- runtime sessions with current-node, context, keyword search, highlight, warning, open-workspace, and advance actions
- action-capable runtime node views over document handles
- workspace sessions with read/write/patch/read-source/compile/submit lifecycle
- executable workspace templates with declarative editable-region rules and assembled-source views
- built-in annotation-first workspace registry plus runtime-level workspace profile/template resolution
- annotation-first LaTeX compiler profiles with structured diagnostics/artifacts
- local-process sandbox backend for workspace compilation plus structured compiler/sandbox metadata
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
- `docs/runtime_api_contract_v1.md`
- `docs/codex_adapter_design_v1.md`
- `docs/codex_direct_library_integration_v1.md`

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

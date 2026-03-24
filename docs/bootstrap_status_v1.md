# Bootstrap Status v1

This document exists so work can continue in this repository **after context compression** with minimal ambiguity.

If you are resuming work with little or no prior context, read this file first.

---

## 1. Repository purpose

This repository is the clean extraction target for **DocWright Core**.

It is **not** the old prototype repo.
It should not be treated as a dump of all legacy code.

Its purpose is to rebuild the core architecture cleanly around:
- Core runtime
- agent adapters
- capability profiles
- skill/tool bundles
- workspace sessions
- protocol/events

---

## 2. Current reality

This repo now contains a **self-contained Core milestone** as an installable Python package with a unified `docwright` facade, not just a contracts-first skeleton.

Implemented baseline capabilities now include:
- runtime sessions with current-node, context, keyword search, highlight, warning, open-workspace, and advance actions
- action-capable runtime node views over document handles
- Core event envelopes and guardrail enforcement
- workspace sessions with read/write/patch/read-source/compile/submit lifecycle
- executable workspace template/profile rules with assembled-source views and locked-shell enforcement
- compile result/error contracts, concrete LaTeX compiler profiles, and artifact-aware compiler boundary
- local-process sandbox backend for workspace compilation
- bubblewrap-backed strong sandbox backend option for supported hosts
- protocol command/event schemas plus serialization helpers
- document handle interfaces plus in-memory fake handles
- lazy `docwright.document` facade for optional document-conversion backends
- adapter/capability/skill interfaces
- reference skill bundles for navigation, highlighting, warnings, and workspace editing
- first `guided_reading` capability with strategy text stored outside Core modules
- headless runner scaffold with single-step and run-until-complete support
- Codex-compatible bridge scaffold with guidance export, a skill-aware tool registry, fake-driver smoke tests, a direct-library host helper, an installable Codex package entry surface, an optional IR-fixture sample input, external-host fixtures, observer hooks, and usage/trace hooks
- smoke, integration, lifecycle, and serialization tests

It is still an **early but usable Core baseline**, not a finished product runtime.

---

## 3. Important terminology

Use these terms consistently:

### Core
The reusable document runtime.

### Agent Adapter
The bridge for a specific external runtime/ecosystem.
Examples:
- Codex-like runtime
- OpenClaw-like runtime

### Capability Profile
Task-mode selection / ruleset.
Examples:
- guided reading
- paper review
- manual task

### Skill / Tool Bundle
Reusable ability package.
Examples:
- highlighting
- warnings
- workspace editing
- research requests

### Workspace Session
The generalized replacement for the old annotation-specific sandbox.

Do **not** collapse these concepts back into one “agent profile” abstraction.

---

## 4. Existing repo contents

### Top-level files
- `README.md`
- `pyproject.toml`
- `setup.py`
- `.gitignore`

### Docs already present
- `docs/bootstrap_status_v1.md`
- `docs/core_agent_boundary_v1.md`
- `docs/agent_integration_model_v1.md`
- `docs/implementation_master_plan_v1.md`
- `docs/execution_checklist_v1.md`
- `docs/migration_checklist_v1.md`
- `docs/prototype_migration_mapping_v1.md`
- `docs/target_repo_structure_v1.md`
- `docs/pdf_ir_fixture_strategy_v1.md`
- `docs/document_ir_contract_v1.md`
- `docs/runtime_api_contract_v1.md`
- `docs/workspace_session_contract_v1.md`
- `docs/workspace_sandbox_design_v1.md`
- `docs/workspace_profile_design_v1.md`
- `docs/workspace_completion_checklist_v1.md`
- `docs/workspace_secure_sandbox_design_v1.md`
- `docs/codex_adapter_design_v1.md`
- `docs/codex_adapter_execution_checklist_v1.md`
- `docs/codex_direct_library_integration_v1.md`
- `src/docwright/codex/entry.py`
- `src/docwright/codex/samples/attention_fixture.py`

### Core/runtime modules now present
- `src/docwright/core/models.py`
- `src/docwright/core/events.py`
- `src/docwright/core/guardrails.py`
- `src/docwright/core/session.py`
- `src/docwright/workspace/models.py`
- `src/docwright/workspace/compiler.py`
- `src/docwright/workspace/templates.py`
- `src/docwright/workspace/profiles.py`
- `src/docwright/workspace/registry.py`
- `src/docwright/workspace/session.py`
- `src/docwright/protocol/commands.py`
- `src/docwright/protocol/events.py`
- `src/docwright/protocol/schemas.py`
- `src/docwright/document/interfaces.py`
- `src/docwright/document/handles.py`
- `src/docwright/document/ir_loader.py`
- `src/docwright/document/facade.py`
- `src/docwright/adapters/agent/base.py`
- `src/docwright/adapters/agent/codex.py`
- `src/docwright/adapters/agent/codex_prompting.py`
- `src/docwright/adapters/agent/codex_tools.py`
- `src/docwright/adapters/agent/codex_types.py`
- `src/docwright/adapters/transport/headless.py`
- `src/docwright/adapters/transport/runtime_host.py`
- `src/docwright/codex/entry.py`
- `src/docwright/adapters/transport/codex_exports.py`
- `src/docwright/capabilities/base.py`
- `src/docwright/capabilities/guided_reading.py`
- `src/docwright/capabilities/manual_task.py`
- `src/docwright/skills/base.py`
- `src/docwright/skills/navigation.py`
- `src/docwright/skills/highlighting.py`
- `src/docwright/skills/warnings.py`
- `src/docwright/skills/workspace_editing.py`

### Test fixtures already present
- `tests/fixtures/document_ir/attention_is_all_you_need.document_ir.json`
- `tests/fixtures/document_ir/attention_is_all_you_need.document_ir.summary.json`
- `tests/fixtures/codex/guided_reading_step_contract.json`
- `tests/fixtures/codex/manual_task_navigation_transcript.json`

---

## 5. What is already decided

The following architectural decisions are already made and should be treated as active unless explicitly revised in a later doc:

1. DocWright Core is a **runtime**, not a chatbot.
2. Guided reading is **not** the definition of Core.
3. Core should be usable behind multiple agent runtimes.
4. The architecture should distinguish:
   - Core
   - Agent Adapter
   - Capability Profile
   - Skill / Tool Bundle
5. The old annotation sandbox should become a **workspace session** abstraction, with annotation-first semantics and a later sandbox backend split.
6. Workspace should remain a general controlled editing framework; annotation is its first strong special case and should evolve through declarative workspace profiles.
7. PDF->IR quality is **not** owned by Core.
8. Real `DocumentIR` fixtures may be consumed by Core tests, but ingest quality remains an upstream concern.

---

## 6. What is implemented now

The following are now implemented as part of the current Core baseline:
- runtime session/state models
- current-node, local-context, and keyword-search queries
- action-capable node views for highlight / warning / open workspace
- runtime event envelopes and run/session payload schemas
- runtime permissions and guardrail policies
- one-workspace-per-step and highlight-before-advance guardrails
- workspace state machine baseline
- compile result + compile error models
- workspace read/write/patch/read-source/compile/submit lifecycle
- declarative workspace template/profile/registry system with executable template assembly
- built-in annotation-first workspace registry
- runtime-level workspace profile/template resolution with structured workspace metadata
- LaTeX compiler profiles with structured diagnostics/artifacts
- local-process sandbox backend and sandbox-aware compiler metadata
- protocol command/event models and serialization helpers
- minimal render protocol for externally visible agent tool-call traces
- document handle protocols/interfaces
- in-memory fake document handles for tests
- agent adapter / capability / skill interfaces
- reference skill bundles for navigation, highlighting, warnings, and workspace editing
- guided-reading capability scaffold with external strategy text
- manual-task capability scaffold for relaxed runtime operation
- headless runner scaffold with completion loop
- workspace lifecycle tests
- runtime guardrail tests
- reference runtime API tests
- guided-reading-through-adapter smoke tests

Still intentionally incomplete / future work:
- richer selector DSLs beyond the current stable lookup/context contracts
- concrete provider-specific adapters
- frontend/service transport layers
- full parser/document package split
- additional compiler/sandbox backends beyond the current local-process + bubblewrap + LaTeX baseline
- broader capability catalog beyond the current guided-reading/manual-task baseline

---

## 6.5 Package install shape

DocWright is now packaged as an installable Python package named `docwright`.

Current install shape:
- `pip install docwright`
- `pip install 'docwright[document]'`
- `pip install 'docwright[latex]'`
- `pip install 'docwright[full]'`

Recommended installed imports:
- `from docwright.codex.entry import DocWrightCodexEntry`
- `from docwright.codex.samples.attention_fixture import build_attention_fixture_entry` (optional sample only)
- `from docwright import document`

The sample helper must remain optional; the stable integration contract is still
`DocWrightCodexEntry.from_document(...)`.

The `docwright.document` package now acts as a unified facade:
- lightweight in-repo IR loading stays available by default
- optional document conversion should be lazy-loaded from a future external backend
- importing `docwright` or `docwright.document` should remain safe when that backend is absent

---

## 7. Immediate coding entry point

The R1-R8 checklist in `docs/execution_checklist_v1.md` is complete.
The focused workspace completion checklist in `docs/workspace_completion_checklist_v1.md` is also complete.

If continuing implementation work, use this order:

1. read `docs/prototype_migration_mapping_v1.md`
2. review `docs/migration_checklist_v1.md`
3. pick the next post-milestone slice without violating the Core / Adapter / Capability / Skill / Workspace boundaries

---

## 8. How to use the Attention fixture

The fixture exists to let Core implementation proceed without rebuilding PDF parsing first.

Use it for:
- document handle tests
- runtime session tests
- relation/evidence traversal tests
- adapter/capability integration tests later

Do **not** use it as proof that DocWright Core guarantees ingest quality.

---

## 9. Safe working rules

When implementing from the checklist:

- complete one item at a time
- prefer small new modules over bulk copies from the old prototype
- if copying from the prototype, first decide whether the destination belongs to Core, Adapter, Capability, Skill, Workspace, or future Document layer
- do not reintroduce old naming if it weakens the current architecture
- keep tests close to the boundary being defined

---

## 10. If uncertainty appears

If a future implementation step feels ambiguous, check the docs in this order:

1. `docs/bootstrap_status_v1.md`
2. `docs/implementation_master_plan_v1.md`
3. `docs/execution_checklist_v1.md`
4. one of the contract docs:
   - `document_ir_contract_v1.md`
   - `runtime_api_contract_v1.md`
   - `workspace_session_contract_v1.md`
5. `docs/agent_integration_model_v1.md`
6. `docs/core_agent_boundary_v1.md`

If ambiguity still remains, prefer the interpretation that preserves:
- Core minimality
- adapter/capability/skill separation
- workspace generality
- document-layer externalizability

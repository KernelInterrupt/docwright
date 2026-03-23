# Prototype Migration Mapping v1

This document maps the old `cognitio` prototype modules to the new DocWright
architecture layers.

The goal is **not** a 1:1 copy.
It is to clarify where each old concern belongs before any migration work.

## Layer mapping overview

| Old prototype area | Representative old modules | New DocWright layer | Notes |
| --- | --- | --- | --- |
| Runtime session / orchestration | `app/runtime/session.py`, `app/runtime/run_controller.py`, `app/runtime/orchestrator.py` | Core | Keep only reusable runtime state/event/step logic. |
| Runtime permissions / tool gating | `app/runtime/permissions.py`, `app/runtime/tool_registry.py`, `app/runtime/tool_executor.py` | Core + Skill / Tool Bundle | Keep generic guardrails in Core; tool-specific exposure belongs in skills. |
| Document handles / navigation | `app/runtime/document_handles.py`, `app/runtime/node_handle.py`, `app/document/navigator.py` | Document layer + Core-facing interfaces | Keep handle contracts parser-neutral. |
| Annotation sandbox / compilation | `app/sandbox/workspace.py`, `app/sandbox/compiler.py`, `app/sandbox/handle.py`, `app/sandbox/templates.py` | Workspace Session | Reframe annotation sandbox as generalized workspace session. |
| Protocol messages / streams | `app/protocol/commands.py`, `app/protocol/events.py`, `app/protocol/stream.py` | Protocol | Keep transport-neutral schemas; avoid provider naming leaks. |
| Provider / runtime integrations | `app/adapters/llm/*`, `app/runtime/local_model_bridge.py`, `app/cli/run_headless.py` | Agent Adapter | Runtime/provider specifics must stay outside Core. |
| Guided reading / prompt strategy | `app/prompts/reading_system.md`, `app/services/annotation_service.py`, `app/services/annotation_session.py` | Capability Profile + Skill / Tool Bundle | Strategy text stays outside Core modules. |
| Research / product-specific flows | `app/services/research_service.py`, `app/prompts/research_system.md` | Future capability / skill layer | Do not fold product workflows back into Core. |
| Ingest / parser logic | `app/ingest/*`, `app/adapters/vlm/*`, `app/domain/document_ir.py` | External document / ingest boundary | Core consumes stable document handles, not parser internals. |

## Immediate migration rule

When lifting code from `cognitio`, first classify it into one of these DocWright
layers:

- Core
- Agent Adapter
- Capability Profile
- Skill / Tool Bundle
- Workspace Session
- Document layer
- Protocol

If the destination layer is unclear, do not copy the code yet.

## Ordered migration notes

### 1. Compile-related types first

The first safe extraction from `cognitio` is the compile-type layer because it is
already relatively reusable and mostly independent from provider/runtime glue.

| Old prototype source | New DocWright destination | Status |
| --- | --- | --- |
| `app/domain/annotation.py::CompileError` | `src/docwright/workspace/models.py::CompileError` | migrated as workspace-owned compile error model |
| `app/domain/annotation.py::CompileResult` | `src/docwright/workspace/models.py::CompileResult` | migrated as workspace-owned compile result model |
| `app/sandbox/compiler.py::CompilerBackend` | `src/docwright/workspace/compiler.py::WorkspaceCompiler` | migrated as transport-neutral compiler boundary |

What was intentionally **not** migrated 1:1:

- annotation-specific names such as `compile_annotation`
- pydantic-based product models tied to annotation workflows
- fake/real compiler implementation details that still belong to future backend work

The new destination keeps only the reusable compile contracts needed by the
workspace session abstraction.

### 2. Workspace lifecycle logic second

After compile-related types, the next safe extraction is the workspace lifecycle.
This keeps the old annotation sandbox logic from leaking back into Core naming.

| Old prototype source | New DocWright destination | Notes |
| --- | --- | --- |
| `app/sandbox/workspace.py::AnnotationWorkspace.initialize` | `src/docwright/workspace/session.py` + `src/docwright/workspace/models.py` | initialize becomes generic workspace opening/state setup rather than annotation-only bootstrapping |
| `app/sandbox/workspace.py::read_editable_region` | `WorkspaceSession.read_body` | migrated under general workspace terminology |
| `app/sandbox/workspace.py::write_editable_region` | `WorkspaceSession.write_body` | migrated as editable-body write operation |
| `app/sandbox/workspace.py::replace_editable_region` | `WorkspaceSession.patch_body` | migrated as controlled patch operation |
| `app/domain/annotation.py::WorkspaceSnapshot` / `WorkspaceActionRecord` | `WorkspaceSessionModel` / `WorkspaceHistoryEntry` | migrated into workspace-owned lifecycle state/history |

Intentionally changed during migration:

- `AnnotationWorkspace` was **not** copied under the same name; it became the more general `WorkspaceSession` boundary.
- lifecycle states now live in `WorkspaceState` instead of annotation-specific/sandbox-specific literals.
- submit/compile constraints are enforced as workspace guardrails instead of prompt-only assumptions.

### 3. Runtime guardrails third

Runtime guardrails in the prototype were split across permission tiers,
controller/session state, and tool-executor checks. In DocWright they move into
explicit Core-owned guardrail models and session enforcement.

| Old prototype source | New DocWright destination | Notes |
| --- | --- | --- |
| `app/runtime/permissions.py::PermissionProfile` | `src/docwright/core/guardrails.py::RuntimePermissions` | migrated as Core-owned permission surface |
| `app/runtime/tool_executor.py` permission checks | `RuntimePermissions.ensure_allowed` + `RuntimeSession` action methods | tool gating no longer lives inside one runtime-specific executor |
| `app/runtime/tool_executor.py` highlight-before-next enforcement | `RuntimeSession.advance` + `RuntimeGuardrailPolicy.require_highlight_before_advance` | guardrail moved into reusable Core session logic |
| `app/runtime/tool_executor.py` one-open-annotation-per-step behavior | `RuntimeSession.record_workspace_opened` + `RuntimeGuardrailPolicy.max_workspaces_per_step` | annotation-specific limit generalized into workspace-per-step policy |
| `app/runtime/session.py` highlight counters / current node state | `RuntimeSessionModel` + `RuntimeStepState` | step-state ownership stays in Core |

Migration rule here:

- keep reusable state/guardrail logic in Core
- do **not** reintroduce prototype-style guardrail checks inside a single adapter executor
- let capabilities choose which guardrails are active via `RuntimeGuardrailPolicy`

### 4. Guided-reading capability logic last

Guided reading is the first capability in DocWright, but it must be migrated
*after* Core, workspace, protocol, and runtime guardrail foundations exist.

| Old prototype source | New DocWright destination | Notes |
| --- | --- | --- |
| `app/prompts/reading_system.md` | `src/docwright/capabilities/resources/guided_reading_strategy.md` | strategy text stays in capability resources, not Core modules |
| `app/services/annotation_service.py` | capability + future workspace skill orchestration | service-level product flow should be decomposed into capability/skill pieces |
| `app/services/annotation_session.py` | `src/docwright/capabilities/guided_reading.py` + workspace subsystem + adapter boundary | no direct carry-over of annotation-session orchestration into Core |
| `app/runtime/node_handle.py` guided actions | `RuntimeSession` action methods + future skill bundles | action semantics belong to Core mechanics plus reusable skills |

Why this migration is last:

- guided reading depends on Core session state already existing
- it depends on workspace lifecycle already being generalized
- it depends on protocol/events already being adapter-neutral
- strategy text must be kept outside Core to avoid redefining Core as a single task mode

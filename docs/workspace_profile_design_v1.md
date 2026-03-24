# Workspace Profile Design v1

This document refines the intended design of DocWright workspace sessions so the
concept stays stable across future context compression.

It should be read together with:
- `docs/workspace_session_contract_v1.md`
- `docs/workspace_sandbox_design_v1.md`

---

## 1. Core conclusion

DocWright workspace should be treated as a **general controlled editing
framework**.

However, the framework's first important concrete use case is still:
- annotation-oriented editing
- often backed by a LaTeX template
- with explicit editable-region boundaries

So the correct framing is:

> workspace is the general mechanism; annotation is the first strong special case.

This replaces two bad framings:
- "workspace is only annotation forever"
- "workspace is just an arbitrary text buffer"

---

## 2. Current decisions that must remain stable

### 2.1 Workspace is not IR mutation

Workspace editing does **not** mean editing `DocumentIR` directly.

Current intended flow:
1. load IR into DocWright runtime
2. navigate runtime state through Core APIs
3. optionally open a workspace derived from the current node
4. edit controlled derived content
5. compile / validate / submit an artifact

If direct IR mutation is ever needed later, it must be designed as a separate
contract with separate guardrails and audit semantics.

### 2.2 Workspace is not the sandbox layer

Workspace is a logical editing abstraction.

Sandbox is an execution-isolation abstraction.

The clean layering remains:

```text
WorkspaceSession
  -> WorkspaceCompiler
  -> SandboxBackend
```

### 2.3 Annotation remains the first concrete profile

Even if workspace stays general, the first serious profile should still model
annotation-oriented editing, especially the original LaTeX-style controlled
editing flow.

---

## 3. Design philosophy

The workspace subsystem should evolve toward:
- declarative configuration
- runtime-loaded profiles
- explicit rule visibility
- low tool-use error rate for agents

The model should not have to guess:
- what kind of workspace it opened
- whether it edits a full file or a region
- whether compile is available
- whether submit requires compile first
- which parts are locked

This is a major product-quality requirement, not optional polish.

---

## 4. The three main concepts

## 4.1 `WorkspaceSession`

`WorkspaceSession` remains the runtime object representing one open controlled
editing session.

It owns:
- lifecycle state
- current editable content
- compile result state
- submission state
- history / audit trail

It should continue to expose operations like:
- `read_body()`
- `write_body(...)`
- `patch_body(...)`
- `compile()`
- `get_compile_errors()`
- `submit()`

This is the stable user-facing editing shell.

---

## 4.2 `WorkspaceTemplate`

A workspace template describes the structured source or shell behind a workspace.

Typical responsibilities:
- template identity
- full source shell or source builder
- body kind
- default editable region
- compile profile hint

Representative shape:

```python
@dataclass(slots=True, frozen=True)
class WorkspaceTemplate:
    template_id: str
    task: str
    body_kind: str
    source: str
    editable_regions: tuple[EditableRegionSpec, ...]
    default_region: str = "body"
    compiler_profile: str | None = None
```

For annotation-first LaTeX usage, the template may include:
- preamble
- fixed macros
- `\begin{document}` / `\end{document}`
- explicit region markers for the editable body

---

## 4.3 `WorkspaceProfile`

A workspace profile is the declarative configuration that tells DocWright which
kind of workspace to create.

A profile should describe:
- profile name
- task
- template choice
- body kind
- compile requirements
- locked-section semantics
- patch scope semantics
- summary text to show the model

Representative shape:

```python
@dataclass(slots=True, frozen=True)
class WorkspaceProfile:
    profile_name: str
    task: str
    template_id: str
    body_kind: str
    compile_required_before_submit: bool = True
    patch_scope: str = "editable_region_only"
    locked_sections: tuple[str, ...] = ()
    model_summary: str = ""
```

Example profile idea:
- `latex_annotation`

That profile would mean:
- annotation task
- LaTeX body editing
- locked template shell
- compile before submit

---

## 5. Editable-region rules

DocWright should support **declarative editable-region rules**.

The immediate goal is not a full DSL.
The immediate goal is a small declarative spec.

Representative shape:

```python
@dataclass(slots=True, frozen=True)
class EditableRegionSpec:
    name: str
    mode: str  # e.g. "marker_range" or "slot"
    start_marker: str | None = None
    end_marker: str | None = None
    required: bool = True
```

Recommended first supported mode:
- `marker_range`

This is enough for annotation-first LaTeX templates, for example using markers
such as:
- `% DOCWRIGHT:BODY_START`
- `% DOCWRIGHT:BODY_END`

The important point is:
- rules become explicit data
- compile/edit logic reads those rules
- the model can be told those rules directly

---

## 6. Reflection and lazy loading

DocWright may use Python reflection features, but only in a controlled way.

Recommended approach:
- explicit registry of workspace profiles
- optional reflection on registered profile objects/classes
- lazy parsing when a profile is actually used

Preferred pattern:

```python
WORKSPACE_PROFILES = {
    "latex_annotation": LatexAnnotationProfile,
}
```

Then on `open_workspace(workspace_profile="latex_annotation")`:
1. resolve profile from registry
2. instantiate or inspect the profile object
3. load template
4. parse editable-region rules
5. build the session
6. expose rule summary to the model

Avoid relying on:
- uncontrolled module scanning
- implicit magic discovery across the repo
- runtime string-eval rule definitions

The goal is predictable extensibility, not cleverness.

---

## 7. What the model must be told

A workspace should expose its rule surface explicitly.

The model should not infer workspace semantics only from prompt prose or by trial
and error.

At minimum, the following should be available in structured metadata:
- `workspace_id`
- `task`
- `workspace_profile`
- `template_id`
- `body_kind`
- `editable_region`
- `locked_sections`
- `compile_ready`
- `compile_backend`
- `submit_ready`
- `compile_required_before_submit`
- `patch_scope`
- short human-readable summary

Representative shape:

```json
{
  "workspace_id": "ws-1",
  "task": "annotation",
  "workspace_profile": "latex_annotation",
  "template_id": "default_annotation_tex",
  "body_kind": "latex_body",
  "editable_region": {"name": "body"},
  "locked_sections": ["preamble", "document_structure"],
  "compile_ready": true,
  "compile_backend": "tectonic",
  "submit_ready": false,
  "compile_required_before_submit": true,
  "patch_scope": "editable_region_only",
  "summary": "Edit only the annotation body. Do not modify LaTeX preamble or document structure."
}
```

This metadata may be returned by:
- `open_workspace(...)`
- `describe_workspace(...)`
- step-export metadata for available profiles

---

## 8. API evolution guidance

The current workspace API can remain mostly stable.

Stable operations to keep:
- `open_workspace(...)`
- `read_body()`
- `write_body(...)`
- `patch_body(...)`
- `compile()`
- `submit()`

What should evolve is not the existence of these operations, but the precision of
workspace creation and description.

Recommended next-step API refinement:

```python
open_workspace(
    task: str,
    capability: str | None = None,
    language: str | None = None,
    initial_body: str | None = None,
    workspace_profile: str | None = None,
    template_id: str | None = None,
)
```

Guidance:
- `task` says what work is being done
- `workspace_profile` says which declarative workspace configuration to use
- `template_id` optionally overrides the profile's default template
- `initial_body` applies to the editable region only, not the whole document shell

Implemented addition:
- `describe_workspace(workspace_id)`

This reduces tool-use ambiguity by letting adapters expose workspace rules and readiness without relying only on the `open_workspace(...)` response.

---

## 9. Annotation as a special case

The annotation use case should become a profile/template/backend combination,
not a separate bottom-layer mechanism.

That means annotation can be modeled as:
- `task="annotation"`
- `workspace_profile="latex_annotation"`
- annotation-specific template
- LaTeX-oriented compiler backend

This preserves a clean general framework while still respecting the original
product need.

---

## 10. Non-goals

This design does **not** imply:
- direct mutation of document IR
- immediate support for arbitrary multi-file build systems
- a heavyweight DSL from day one
- automatic discovery of every profile in the codebase
- hardwiring Core to one host runtime sandbox

---

## 11. Recommended implementation order

1. Add declarative template/profile data structures
2. Add registry-based profile resolution
3. Add structured workspace description metadata
4. Make `open_workspace(...)` return richer metadata
5. Add `describe_workspace(...)`
6. Later connect compiler profiles to sandbox backends
7. Later add optional LaTeX compiler package/backend

---

## 12. Final summary

The intended stable design is:

- workspace is a general controlled editing framework
- annotation is its first strong special case
- editable-region rules should become declarative
- profile rules should be loaded lazily
- rule surfaces should be exposed clearly to the model
- Core should not confuse workspace, sandbox, and IR mutation

# Runtime API Contract v1

This document defines the **minimum runtime API semantics** for DocWright Core.

The design goal is Playwright-like:
- stable object/session model
- explicit query vs action distinction
- runtime-enforced constraints
- reusable across multiple external agent runtimes

---

## 1. Runtime purpose

The runtime hosts stateful document interaction.

It should let an agent runtime:
- resolve explicit node references
- inspect node-local context and structure
- act on explicit node refs
- open controlled workspace sessions
- emit structured events

The runtime itself should not decide policy.

---

## 2. Core objects

Minimum conceptual objects:

- `RuntimeSession`
- `NodeRef`
- `Locator`
- `DocumentHandle`
- `PageHandle`
- `NodeHandle`
- `WorkspaceSession`

The exact implementation can vary, but these semantics must exist.

---

## 3. Query vs action split

### Query operations
Do not change runtime state.

Examples:
- `session.node(node_id)`
- `session.search_text(query)`
- `session.search_headings(query)`
- `locator.first()`
- `node_ref.context(before=1, after=1)`
- `document.page(3)`
- `document.select(node_id)`
- `node_ref.text_content()`
- `node_ref.relations()`

### Action operations
Do change runtime state or produce lifecycle events.

Examples:
- `node_ref.highlight(...)`
- `node_ref.warning(...)`
- `node_ref.open_workspace(...)`

This split must stay explicit.

---

## 4. RuntimeSession contract

A runtime session should support at minimum:

- access to explicit node references
- access to node-local context and structure
- access to emitted events
- enforcement of guardrails

Representative shape:

```python
session.node("sec_intro")
session.search_text("Transformer")
session.search_headings("Introduction")
session.events()
```

---

## 5. Node action contract

`NodeRef` should support at minimum:

### `highlight(level, reason=None)`
Apply an attention marker.

### `warning(kind, severity, message, evidence=None)`
Attach a warning to the referenced node.

### `open_workspace(task, capability=None, language=None)`
Open a controlled editing/session workspace derived from the referenced node.

These actions must emit structured runtime events.

---

## 6. Guardrail contract

Guardrails belong to Core.

Examples of valid runtime guardrails:
- forbid invalid node-targeted actions when policy disallows them
- forbid duplicate highlight for the same targeted node when policy requires uniqueness
- forbid opening more than one workspace for the same targeted node when configured
- forbid invalid workspace state transitions

Guardrails should be configurable enough that Core can host different capabilities later.

---

## 7. Event contract

Every runtime action should be representable as a structured event.

Minimum event families:
- run/session started/completed/failed
- node progress events
- highlight/warning events
- workspace lifecycle events
- guardrail failure/error events

Core events should be capability-neutral where possible.

Examples:
- `runtime.started`
- `node.resolved`
- `highlight.applied`
- `warning.raised`
- `workspace.opened`
- `workspace.compiled`
- `workspace.submitted`
- `runtime.failed`

---

## 8. Integration contract

Core should host external runtimes through an adapter boundary.

Representative idea:

```python
class AgentAdapter(Protocol):
    async def run_step(self, session: RuntimeSession, capability: object) -> None: ...
```

The important part is not the exact signature.
The important part is that:
- adapters consume Core
- adapters do not own runtime state internals
- multiple runtimes can target the same runtime API
- capabilities select task mode without replacing runtime integration

---

## 9. Legacy note

The current implementation still exposes sequential-reading-centered concepts
such as:

- `session.current_node()`
- `session.advance()`

Those remain part of the implemented compatibility surface today, but they
should be treated as legacy public concepts rather than the long-term runtime
center. The migration direction is tracked in:

- `docs/node_ref_locator_migration_v1.md`
- `docs/node_ref_locator_execution_checklist_v1.md`

---

## 10. Degradation rule

Runtime API consumers must tolerate imperfect document structure.

For example:
- a paragraph may be too long
- section hierarchy may be shallow
- figure relations may be sparse

The runtime contract remains valid as long as the structural Core-facing IR contract is satisfied.

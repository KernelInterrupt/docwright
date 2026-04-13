# NodeRef / Locator Migration v1

This document records the planned migration away from the current
**sequential-reading-centered** runtime API toward a **NodeRef-centered**
runtime API.

It is a forward-looking design/migration document.
It does **not** describe the currently implemented public API.

Execution work for this migration is tracked in:

- `docs/node_ref_locator_execution_checklist_v1.md`

---

## 1. Why this migration is needed

The original DocWright runtime shape was optimized for one narrow goal:

- let an LLM read a document incrementally
- keep token usage low
- keep the runtime on a single sequential path

That produced a public API centered on:

- `current_node()`
- `advance()`
- actions applied to the current node

This was useful for early guided-reading experiments, but it is now too narrow
for the broader runtime direction.

DocWright should evolve toward:

- stable node references
- tree/graph navigation
- non-linear targeting as a first-class workflow
- explicit node-level actions that do not depend on a hidden global reading
  cursor

---

## 2. Core design decision

The public runtime should no longer be organized around:

- a single public `current_node`
- a single public `advance` path
- node actions that implicitly mean “act on whatever is current right now”

Instead, the public runtime should be organized around:

- `RuntimeSession` as a runtime service / query surface
- `NodeRef` as the primary node-level runtime object
- `Locator` as a higher-level helper that resolves to one or more `NodeRef`s

In short:

- `NodeRef` is the core object
- `Locator` is a convenience wrapper/resolution surface
- sequential traversal is no longer the runtime worldview

---

## 3. Target object model

### `RuntimeSession`
Owns:

- document/runtime services
- workspace lifecycle ownership
- events/guardrails/protocol integration
- node/ref lookup and query surfaces

It should produce `NodeRef`s rather than force callers through a global current
node.

### `NodeRef`
Represents one concrete runtime-visible document node.

It should become the main node-level object for:

- reading node content
- inspecting context/structure/relations
- opening workspaces
- applying highlights/warnings
- following relations to other nodes

### `Locator`
Represents a reusable node-finding helper.

It is not the core runtime object.
It is a higher-level convenience wrapper that resolves to one or more
`NodeRef`s.

Examples:

- heading-based lookup
- text-based lookup
- section-path lookup
- relation-based lookup

---

## 4. Public API direction

### 4.1 Session-level APIs should return `NodeRef`

Representative target direction:

```python
ref = session.node("sec_intro")
hits = session.search_text("Transformer")
headings = session.search_headings("Introduction")
```

Where:

- `session.node(...) -> NodeRef`
- `session.search_text(...) -> tuple[NodeRef, ...]` or a richer hit type that
  carries/contains `NodeRef`
- `session.search_headings(...) -> tuple[NodeRef, ...]` or a richer hit type
  that carries/contains `NodeRef`

### 4.2 Node-level actions should live on `NodeRef`

Representative target direction:

```python
ref.text_content()
ref.context(before=1, after=1)
ref.structure()
ref.highlight(level="important")
ref.warning(kind="unsupported_claim", severity="medium", message="...")
ref.open_workspace(task="annotation")
```

The important change is:

- actions should be tied to the explicit target ref
- not to an implicit global current node

### 4.3 Locator should wrap `NodeRef` resolution

Representative direction:

```python
locator = session.heading("Introduction")
ref = locator.first()
all_refs = locator.all()
```

Locator should not replace `NodeRef`.
It should help create `NodeRef`s.

---

## 5. What should be removed from the public worldview

The following concepts should be removed from the **public runtime center**:

- `current_node()` as the main runtime entry
- `advance()` as the default navigation primitive
- the idea that node actions must target whichever node is currently selected

This does **not** necessarily mean every internal helper must disappear
immediately.
It means these concepts should stop defining the public contract.

---

## 6. What happens to `jump`

The current `jump_to_node(...)` behavior is tied to the old “move global runtime
focus” model.

Target direction:

- `jump` should no longer be the main public abstraction
- if node selection remains useful internally, it should be an implementation
  detail or a narrower compatibility helper
- public APIs should prefer returning `NodeRef`s directly

If an internal “select/focus this node for a host view” helper still exists, it
should be treated as:

- host/view state management
- not the core node action model

---

## 7. Migration strategy

This migration should be staged rather than performed as a blind rewrite.

### Phase 1: redefine the public center

- add `NodeRef` terminology/documentation
- define `Locator` as a wrapper over `NodeRef` resolution
- stop expanding the public `current_node/advance` API surface

### Phase 2: move node actions onto `NodeRef`

- make explicit node references the target of highlight/warning/workspace
  operations
- update tool descriptions and prompt guidance to stop presenting sequential
  reading as the default worldview

### Phase 3: reduce compatibility surface

- de-emphasize or deprecate public `current_node`
- de-emphasize or deprecate public `advance`
- keep any necessary internal compatibility helpers only as implementation
  details

---

## 8. What likely needs code changes

The main migration pressure is expected in:

- `src/docwright/core/session.py`
- `src/docwright/core/models.py`
- `src/docwright/adapters/agent/codex_tools.py`
- `src/docwright/adapters/agent/codex_prompting.py`
- navigation/tooling tests and smoke tests

The following areas should require much less change at first:

- document handle protocols
- workspace compiler/sandbox internals
- provider compatibility boundaries
- companion boundaries

---

## 9. Compatibility guidance

During migration:

- avoid adding new features that deepen the `current_node/advance` worldview
- prefer APIs that return explicit node references
- treat sequential traversal as an optional strategy, not as the runtime's main
  mental model

---

## 10. Summary

The intended architectural shift is:

- from a sequential-reading runtime with a public current-node cursor
- to a node-reference runtime with optional locator helpers

The important non-goal is:

- this does not require rewriting every class from scratch

The important goal is:

- make `NodeRef` the central public node abstraction
- make `Locator` a wrapper around `NodeRef` resolution
- remove `current_node/advance` from the core public worldview

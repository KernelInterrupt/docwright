# NodeRef Compatibility Layer v1

This document records the temporary compatibility layer that remains while the
runtime migrates from the older `current_node/advance` worldview toward the
newer `NodeRef/Locator` worldview.

It exists to make the migration explicit instead of leaving legacy behavior
implicit.

---

## 1. Compatibility APIs still present

The current implementation still exposes these public compatibility concepts:

- `current_node()`
- `advance()`
- `jump_to_node(...)`

These remain usable for existing tests, adapters, and host flows, but they are
no longer the intended public center.

Their status is:

- `current_node()`: legacy cursor view
- `advance()`: legacy sequential-reading helper
- `jump_to_node(...)`: compatibility helper for updating the legacy runtime
  selection state

---

## 2. Compatibility guardrails

The current guardrail model still contains one legacy sequential-reading rule:

- `require_highlight_before_advance`

This should be understood as:

- a compatibility rule for old sequential flows
- not a long-term truth about all node-targeted actions

The current model also contains one selected-node action limit that still
remains useful during migration:

- `max_workspaces_per_step`

In practice this currently behaves as:

- a limit on workspace opens for the currently selected node/cursor state

That behavior should eventually be renamed more clearly once the compatibility
surface shrinks further.

---

## 3. Event compatibility rule

During migration, runtime action events should expose explicit target semantics
even if older cursor/selection concepts still exist.

That means events such as:

- `highlight.applied`
- `warning.raised`
- `workspace.opened`
- `workspace.session_created`
- `node.jumped`

should expose `target_node_id` in payloads where applicable, rather than
requiring consumers to infer the acted-on node only from older cursor state.

---

## 4. Migration expectation

New code should prefer:

- explicit node refs
- explicit node-targeted tool arguments
- explicit target-bearing event payloads

New code should avoid deepening the compatibility surface by introducing new
features that depend on:

- `current_node` as the public center
- `advance` as the normal navigation strategy
- implicit action targeting through hidden global selection state

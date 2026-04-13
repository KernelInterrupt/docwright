# NodeRef / Locator Execution Checklist v1

This checklist tracks the planned migration described in:

- `docs/node_ref_locator_migration_v1.md`

This checklist is intentionally separate from the already-completed
post-milestone cleanup checklist.

Rules:

- complete one item at a time
- update this checklist immediately after finishing each item
- make one commit per completed checklist item
- do not re-introduce sequential-reading assumptions into the new public API
- prefer migrating existing objects/functions over inventing parallel runtime
  object systems

Scope:

- remove `current_node/advance` from the public runtime center
- make `NodeRef` the main node-level runtime abstraction
- make `Locator` a wrapper around `NodeRef` resolution
- keep document/workspace/provider boundaries intact during migration

---

## L1. Terminology and public contract reset
- [x] define the public `NodeRef` concept explicitly in runtime docs
- [x] define `Locator` explicitly as a `NodeRef` resolution/helper layer rather than the core runtime object
- [x] mark `current_node` and `advance` as legacy sequential-reading concepts in docs without changing code yet
- [x] align top-level integration docs so the runtime is described as target/node-reference-centered rather than cursor-centered

## L2. Core session object migration
- [x] refactor the current node view object into a general `NodeRef`-style runtime object rather than a current-node-only helper
- [x] add session-level APIs that return explicit node refs directly for node lookup and structural targeting
- [x] remove the need for public runtime consumers to act through an implicit global current node
- [x] keep any temporary node-selection helper internal or compatibility-scoped rather than the new public center

## L3. Tool surface migration
- [ ] redesign navigation tools so node-level reads/actions operate on explicit node references or node-targeted arguments
- [ ] remove `advance` from the primary tool worldview
- [ ] reduce `jump` from a public navigation center to a compatibility/helper role or replace it with explicit node-ref-returning flows
- [ ] ensure tool payloads can carry or reconstruct stable node references without inventing provider-specific contracts

## L4. Prompt, capability, and host-loop migration
- [ ] remove the default `current_node -> get_context -> advance` guidance from Codex-facing prompting
- [ ] redefine guided/manual capabilities so sequential traversal is a strategy choice, not a runtime truth
- [ ] update smoke/e2e host-loop expectations to reflect explicit node targeting rather than stepwise sequential progression
- [ ] keep adapter/runtime boundaries clean while changing the public interaction style

## L5. Guardrails, events, and compatibility cleanup
- [ ] identify which existing guardrails are truly node-action guardrails versus sequential-reading-specific guardrails
- [ ] remove or redesign highlight-before-advance style rules once `advance` is no longer public-center API
- [ ] redesign node navigation/action events around explicit target refs where needed
- [ ] document any temporary compatibility layer that preserves old APIs during migration

## L6. Regression and acceptance coverage
- [ ] add tests proving node-level actions can run via explicit node references without `current_node`
- [ ] add tests proving real PDF traversal and non-linear targeting still work after the migration
- [ ] add tests proving workspace operations can be initiated from explicit node refs
- [ ] add docs/tests showing locator helpers resolve into node refs rather than becoming a second runtime object hierarchy

---

## Completion target

This migration phase is complete when all of the following are true:

- the public runtime is no longer centered on `current_node` or `advance`
- node-level runtime work is expressed through explicit `NodeRef`s
- locator helpers resolve to node refs rather than replacing them
- prompt/tool guidance no longer assumes sequential reading as the default worldview
- compatibility with document/workspace/adapter boundaries remains intact

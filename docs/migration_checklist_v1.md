# Migration Checklist v1

This checklist defines the first extraction path from the existing prototype into **DocWright Core**.

## Phase 0 — done now
- [x] create a clean sibling `docwright/` repository scaffold
- [x] write the Core vs Agent boundary document
- [x] write the target repo structure document
- [x] define the migration checklist itself

## Phase 1 — architecture extraction
- [x] define the minimal runtime interfaces that every adapter/capability must use
- [x] define the minimal workspace session interface
- [x] define the event model independent of guided-reading-specific wording
- [x] define protocol schemas for commands/events/tool sessions
- [x] define an agent-adapter interface
- [x] define a capability-profile interface
- [x] define reusable skill/tool bundle boundaries

## Phase 2 — copy only the true Core primitives
- [x] extract session state objects from the prototype
- [x] extract runtime guardrails from the prototype
- [x] extract event emission primitives from the prototype
- [x] extract workspace state machine from the prototype
- [x] extract compile error model from the prototype
- [x] keep guided-reading-specific policy out of these modules

## Phase 3 — first capability migration
- [x] add `guided_reading` as the first capability profile
- [x] move reading-step prompts/tool descriptions into capability/skill layers
- [x] move advice/warning/highlight strategy rules into capability/skill layers
- [x] ensure capability uses Core runtime instead of owning runtime state

## Phase 4 — adapter boundary cleanup
- [x] define agent adapter interfaces in Core-neutral terms
- [x] keep Responses/OpenAI compatibility logic behind adapter interfaces
- [ ] keep local companion logic out of the central runtime loop
- [ ] make headless transport consume protocol/events instead of internal objects directly

## Phase 5 — document boundary preparation
- [x] define which document interfaces stay in `docwright-core`
- [ ] define which concrete ingestion/IR pieces later move to `docwright-document`
- [x] ensure Core depends on stable document handles, not parser internals

## Exit criteria for first useful milestone
- [x] a minimal headless flow can run using the new Core package layout
- [x] a guided-reading capability can highlight, warn, open workspace, and advance
- [x] workspace compile/submit flow works through Core contracts
- [x] tests prove Core can host more than one adapter/capability combination

---

## Follow-up note

The remaining explicit unfinished items after this milestone are tracked in:

- `docs/post_milestone_completion_checklist_v1.md`

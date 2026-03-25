# Navigation Runtime Checklist v1

This checklist implements the navigation redesign described in:

- `docs/navigation_runtime_requirements_v1.md`

Rules:

- keep Core / Agent Adapter / Capability / Skill / Workspace boundaries clean
- do not turn raw IR JSON into the public agent interaction surface
- preserve reading order, but do not keep it as the only navigation axis
- reuse existing `internal_link_to` IR relations instead of re-detecting links in Core
- only export tools that the active runtime/capability can actually support

---

## N1. Repository and boundary cleanup
- [x] remove legacy `src/docwright/agents/` placeholder package
- [x] review host-side package layout and stop mixing generic host concepts with Codex-only concepts ambiguously
- [x] decide and document one of the two directions clearly:
  - [x] make the current host bridge explicitly Codex-scoped
  - [ ] or extract truly host-neutral contract types before keeping generic names
- [x] update affected docs to match the chosen layout

## N2. Tree-aware document contract
- [x] extend the Core-facing `DocumentHandle` contract for hierarchy-aware lookup
- [x] add minimal concepts for:
  - [x] root
  - [x] parent
  - [x] children
  - [x] siblings
  - [x] ancestry / section path
- [x] keep traversal order available alongside structure lookup
- [x] add tests for imperfect-but-valid hierarchy degradation

## N3. Runtime navigation model
- [x] keep `current_node` / `get_context` / `advance` working as today
- [x] add runtime support for structure-aware inspection
- [x] define runtime jump semantics separately from `advance`
- [x] define runtime events emitted by jump/follow-link operations
- [x] ensure focus updates remain runtime-owned and auditable

## N4. Search hardening
- [x] keep `RuntimeSession.search_text(...)` as the public search entrypoint
- [x] enrich search results with structure-aware metadata
- [x] support optional scope constraints such as:
  - [x] whole document
  - [x] current subtree
  - [x] current page
  - [x] selected node kinds
- [x] design heading/section-oriented search surface
- [x] add tests covering manual/reference-style lookup workflows

## N5. Internal-link navigation
- [x] consume existing `internal_link_to` relations from the document layer
- [x] expose runtime queries for outgoing link targets around the current node
- [x] add a runtime action for following an internal link
- [x] define graceful fallback behavior when link alignment is noisy or incomplete
- [x] add tests using real IR fixtures with internal links preserved

## N6. Tool-bundle evolution
- [x] keep current baseline navigation tools stable:
  - [x] `current_node`
  - [x] `get_context`
  - [x] `search_text`
  - [x] `advance`
- [x] design tree-aware tool additions
- [x] design jump-aware tool additions
- [x] design internal-link-aware tool additions
- [x] ensure tool exposure is gated by real readiness, not just aspiration

## N7. Consumer-facing path
- [x] update docs so DocWright is no longer presented as IR-first only
- [x] explain clearly that the runtime supports:
  - [x] sequential traversal
  - [x] structure inspection
  - [x] non-linear targeting
- [x] document the role of internal links in navigation
- [x] document the difference between `advance` and jump/follow-link behavior

## N8. Regression and fixture coverage
- [x] add hierarchy-aware fixture coverage
- [x] add internal-link navigation fixture coverage
- [x] add search+jump integration tests
- [x] add host-level contract tests for newly exposed navigation tools
- [x] keep existing reading-order flows green during the redesign

---

## Completion target

Navigation is complete enough for this phase when all of the following are true:

- reading order is no longer the only navigation axis
- structure-aware inspection is available in Core
- `search_text` remains stable but becomes more useful for real lookup flows
- internal links preserved in IR become actionable runtime navigation inputs
- tool exposure matches actual runtime readiness
- consumer docs describe DocWright as a document runtime, not just a linear reader

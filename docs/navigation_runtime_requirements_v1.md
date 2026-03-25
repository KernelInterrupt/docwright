# Navigation Runtime Requirements v1

This document defines the next-stage navigation requirements for DocWright Core.

The goal is to move from a **reading-order-first MVP** to a **multi-view document
runtime** that still preserves the clean Core / Agent Adapter / Capability /
Skill / Workspace boundaries.

---

## 1. Problem statement

The current runtime already supports:

- `current_node`
- `get_context`
- `search_text`
- `advance`

This is enough for sequential reading flows such as:

- paper walkthrough
- guided reading
- step-by-step annotation

But it is not enough for non-linear documents such as:

- manuals
- technical references
- product documentation
- regulations
- books with internal jumps

In these documents, the normal user flow is often:

1. locate the relevant section
2. jump there
3. inspect local structure
4. only read the relevant subtree

So DocWright must not remain a runtime that only behaves like a linear reader.

---

## 2. Current facts

### 2.1 What already exists in Core

Core already has:

- runtime-owned `search_text(...)`
- reading-order stepping
- nearby context lookup
- node relations visible through `node.relations()`

### 2.2 What already exists in `docwright-document`

The document layer already preserves PDF-native internal links into IR relations.

Current status:

- native PDF internal links are extracted
- they are aligned to parsed blocks
- they survive into `DocumentIR` relations
- the current relation kind is:
  - `internal_link_to`

So the system already has an upstream basis for hyperlink-aware navigation.

### 2.3 What is missing today

What is missing is not link detection itself, but promoting navigation to a
first-class runtime concept:

- tree/section structure is not yet exposed as a first-class runtime view
- jump-style navigation is not yet a first-class runtime action
- search results do not yet provide enough structure-aware context
- internal links are present as relations, but not yet promoted to dedicated
  runtime navigation APIs/tools

---

## 3. Design principles

### 3.1 Keep both structure and reading order

DocWright must support both:

- **structure view**: document tree / section hierarchy
- **traversal view**: reading order

Neither should replace the other.

Reading order remains useful for:

- guided reading
- sequential review
- local context windows

Structure remains necessary for:

- manual lookup
- section-scoped work
- manuals/specifications
- hyperlink-driven movement

### 3.2 Runtime owns navigation semantics

Navigation must remain runtime-owned.

That means:

- the document layer provides stable structure, IDs, and relations
- Core defines navigation behavior and session focus updates
- adapters expose these capabilities as tool surfaces

The public agent-facing contract should stay on runtime APIs/tools, not raw IR.

### 3.3 Do not collapse architecture boundaries

This redesign must not collapse:

- Core
- Agent Adapter
- Capability Profile
- Skill / Tool Bundle
- Workspace Session

In particular:

- tree/query/jump semantics belong in Core
- host-specific tool exposure belongs in adapters
- task-specific restrictions belong in capabilities

### 3.4 Graceful degradation

Navigation must tolerate imperfect structure extraction.

For example:

- heading hierarchy may be shallow
- parent/child links may be incomplete
- internal-link alignment may be noisy

Core should use what exists, degrade gracefully, and avoid hard-failing when
non-essential structure is imperfect.

---

## 4. Required navigation model

DocWright should support three complementary navigation views.

### 4.1 Structure view

The runtime should understand hierarchical placement such as:

- root
- parent
- children
- siblings
- ancestry / section path

Minimum required questions that must become answerable:

- what section does the current node belong to?
- what are the children of this heading/section?
- what are the sibling sections near this node?
- what is the ancestry path from root to current node?

### 4.2 Traversal view

The runtime should keep the existing traversal model:

- `current_node`
- `get_context`
- `advance`
- reading-order-local context windows

Reading order should remain the default sequential traversal, but not the only
navigation strategy.

### 4.3 Targeting view

The runtime should support non-linear targeting:

- keyword search
- heading/section search
- link following
- explicit jumps

This is the view needed for:

- manuals
- references
- API docs
- jump-heavy PDFs with internal links

---

## 5. Search requirements

### 5.1 Existing `search_text` remains

`search_text` already exists and should remain the baseline search surface.

Its ownership stays with `RuntimeSession`, even if the backing document handle
helps implement it internally.

### 5.2 Search results need richer structure

Current search results are too flat for navigation-heavy workflows.

Future search results should be able to carry at least:

- `node_id`
- `node_kind`
- `page_number`
- `text_preview`
- `match_count`
- section/ancestry context
- optional score or ranking metadata

This allows the agent to understand whether the hit is:

- a heading
- a paragraph
- a caption
- part of the relevant section subtree

### 5.3 Search scope must become constrainable

Search should eventually support constrained scopes such as:

- whole document
- current subtree
- current page
- selected node kinds

This is required for practical manual lookup flows.

### 5.4 Heading-oriented search is required

Keyword search alone is not enough.

DocWright should support heading/section-oriented lookup, whether exposed as:

- `search_headings(...)`
- `find_section(...)`
- or an equivalent structured query surface

This is especially important for manuals and specifications.

---

## 6. Jump requirements

### 6.1 Runtime needs explicit jump semantics

Search without jump is incomplete.

DocWright needs explicit focus-changing navigation such as:

- jump to node
- jump to section
- jump to search result

These operations must update runtime focus, not just return data.

### 6.2 Jump is different from advance

`advance()` means:

- move along the default traversal order

Jump means:

- reposition runtime focus to a chosen target

These must remain distinct concepts.

### 6.3 Jump should preserve runtime invariants

When a jump happens, Core must define:

- how the current step focus changes
- what events are emitted
- whether local context is recomputed immediately
- how guardrails interact with repositioning

---

## 7. Internal-link requirements

### 7.1 Internal links must become first-class navigation inputs

Since `docwright-document` already preserves `internal_link_to`, Core should
promote this from passive relation data to actionable navigation.

### 7.2 Minimum required behaviors

The runtime must eventually support:

- listing relevant outgoing internal links for the current node
- identifying the target node of a link relation
- following an internal link as a runtime action

### 7.3 Relation data remains the source of truth

The runtime should not re-detect links.

Instead:

- document/IR relations remain the source of truth
- Core interprets them into runtime navigation behavior

---

## 8. Proposed Core-facing capability surface

The exact method names can evolve, but the runtime must converge on a surface
that can answer and/or perform operations like:

### Query-style

- current node
- local reading-order context
- ancestry path
- children of current node
- sibling nodes/sections
- search text
- search headings
- outgoing internal links

### Action-style

- advance
- jump to node
- jump to section
- follow internal link

These should later be surfaced through skill/tool bundles instead of leaking as
adapter-only hacks.

---

## 9. Tool-surface implications

This redesign implies future navigation tools beyond the MVP set.

The current baseline tools:

- `current_node`
- `get_context`
- `search_text`
- `advance`

should later be complemented by tree-aware and jump-aware tools such as:

- inspect ancestry / section path
- inspect children / siblings
- jump to a node
- follow an internal link
- search headings / sections

Important rule:

- only export tools that the current runtime/capability can actually support

Tool exposure must stay aligned with actual runtime readiness.

---

## 10. Document-handle implications

Core should not parse raw IR directly during agent operation.

But the backing document handle contract will need to grow enough to support:

- stable hierarchy lookup
- relation lookup
- traversal order lookup

This means the runtime should consume a richer `DocumentHandle`, not a richer
raw JSON workflow.

---

## 11. Workspace interaction rule

Workspace remains a separate concept.

Navigation redesign must not:

- merge workspace into document navigation
- make workspace the primary way to inspect structure
- mutate IR structure directly

Navigation selects and repositions runtime focus.
Workspace remains controlled editing anchored to runtime state.

---

## 12. Priority summary

### Immediate priority

1. recognize the runtime must support structure + traversal + targeting
2. preserve reading order, but demote it from sole navigation axis
3. promote internal links from passive relations to navigation inputs

### Next implementation priority

1. tree-aware document/runtime contracts
2. richer search results
3. jump semantics
4. internal-link follow semantics

### Later priority

1. scoped search
2. heading-specific search
3. richer ranking
4. more specialized navigation skill bundles

---

## 13. Final requirement statement

DocWright must evolve from:

- a runtime that can step through a reading order

into:

- a runtime that supports **sequential traversal**, **hierarchical structure
  inspection**, and **non-linear targeting/jump flows**

while keeping:

- runtime-owned state
- clean adapter boundaries
- capability-controlled policy
- workspace separation
- raw IR hidden behind document/runtime handles

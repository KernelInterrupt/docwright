# DocWright Core Implementation Master Plan v1

This document is the **from-zero build guide** for the new `docwright` repository.

It assumes:
- the old `cognitio` repository remains the running prototype
- this repository is the clean extraction target for **DocWright Core**
- we want a Playwright-like **document runtime**, not a chatbot product
- guided reading is the **first capability profile**, not the definition of Core itself
- Core should be able to sit behind arbitrary agent runtimes such as Codex-like and OpenClaw-like systems

---

# 1. Product thesis

DocWright Core is a runtime for **structured document interaction**.

It should let model-driven agents operate on a document through stable APIs and sessions, instead of forcing them to repeatedly:
- reparse raw PDFs
- guess document structure
- manually correlate figures/captions/paragraphs
- generate one-shot answers with no runtime state

The runtime should feel closer to:
- Playwright for browsers
- a stateful document automation kernel
- a host environment for multiple document agents

not closer to:
- generic chat
- single-shot summarization
- freeform RAG over text blobs

---

# 2. Non-goals

DocWright Core should **not** initially own:
- heavy PDF parsing implementations
- every provider-specific trick from day one
- the frontend application
- product-specific guided-reading heuristics hardcoded into runtime internals
- a large compatibility surface for legacy schema-first APIs unless strictly needed

Those can be added later or live in adjacent repos/layers.

---

# 3. Architectural boundary

## 3.1 Core

Core owns reusable runtime mechanics:
- runtime session state
- document-facing handle interfaces
- locator actions
- workspace sessions
- guardrails
- event model
- protocol model
- minimal adapter interfaces

## 3.2 Agent adapters

Agent adapters own runtime integration:
- how Codex-like systems connect
- how OpenClaw-like systems connect
- how tool calls/events are translated
- how streaming/interrupts are handled for that runtime

## 3.3 Capability profiles

Capability profiles own task-mode selection:
- guided reading
- paper review
- manual task execution
- annotation-only mode

They are not runtime integrations.

## 3.4 Skill / tool bundles

Skill / tool bundles own reusable abilities:
- highlighting
- warnings
- workspace editing
- research requests
- document navigation presets

## 3.5 Document layer

The document layer may live inside this repo temporarily, but should be treated as an externalizable dependency.

Core should depend on **document interfaces**, not parser internals.

---

# 4. Target capability surface

The first meaningful version of DocWright Core should support:

## 4.1 Document runtime
- selecting document/page/node handles
- getting current node and local context
- traversing relations/evidence through stable handles

## 4.2 Locator actions
- `highlight`
- `warning`
- `open_workspace`
- `advance`

## 4.3 Workspace session
- single controlled file/body region
- read/write/patch
- compile
- compile error retrieval
- submit

## 4.4 Events
- run/session events
- locator action events
- workspace lifecycle events
- structured error events

## 4.5 Agent hosting
- one agent adapter abstraction
- at least one real capability profile: `guided_reading`
- proof that more adapters and capability combinations could plug in without Core rewrite

---

# 5. Build order

We should build **inside-out**.

That means:
1. define interfaces and state models
2. define event and protocol surfaces
3. implement guardrails
4. implement workspace subsystem
5. implement minimal runtime controller
6. only then add adapter/capability integration points
7. only then add the first guided-reading capability

This avoids rebuilding Core around agent-specific assumptions.

---

# 6. Phase plan

## Phase A — contracts first

Goal: freeze the most important conceptual boundaries before code growth.

Deliverables:
- core/agent boundary doc
- agent integration model doc
- target repo structure doc
- detailed migration checklist
- runtime interface spec
- workspace interface spec
- event/protocol spec

Success condition:
- a new contributor can tell exactly what belongs in Core vs Adapter vs Capability vs Skill

## Phase B — minimal Core primitives

Goal: create reusable runtime primitives with no guided-reading policy baked in.

Deliverables:
- run/session state objects
- event types and envelopes
- guardrail engine
- document handle interfaces
- workspace session state machine
- compile result + compile error models

Success condition:
- the runtime can host actions and enforce constraints without knowing specific agent strategy

## Phase C — adapter and capability hosting

Goal: prove Core can host a real outside runtime + task mode.

Deliverables:
- `AgentAdapter` interface
- `CapabilityProfile` interface
- first skill bundles
- `guided_reading` capability
- adapter-to-core call path

Success condition:
- guided reading works as a capability, not as a special runtime hardcode
- external agent runtimes can be plugged in conceptually without changing Core's contract

## Phase D — concrete integration

Goal: let capability execution be backed by real external runtimes.

Deliverables:
- base adapter interfaces
- tool-session interaction abstraction
- provider/runtime config abstraction
- minimal headless runner

Success condition:
- a headless run can operate through Core contracts

## Phase E — extraction cleanup

Goal: determine what stays in `docwright-core` vs moves later.

Deliverables:
- boundary list for future `docwright-document`
- migration notes from the old prototype
- compatibility notes for CLI/env/service aliases

Success condition:
- future repo split is obvious, not architectural guesswork

---

# 7. Concrete module plan

## 7.1 `src/docwright/core/`

Files to add first:
- `events.py`
- `guardrails.py`
- `models.py`
- `session.py`
- `run_controller.py`

Responsibilities:
- runtime state
- event emission
- permissions / guardrails
- generic session progression

## 7.2 `src/docwright/document/`

Files to add first:
- `interfaces.py`
- `handles.py`
- `selectors.py`

Responsibilities:
- stable abstract document-facing handle API
- minimal in-memory/test implementation support
- no parser-heavy assumptions

## 7.3 `src/docwright/workspace/`

Files to add first:
- `models.py`
- `session.py`
- `compiler.py`
- `templates.py`

Responsibilities:
- controlled editable body/file model
- compile lifecycle
- compile errors
- submission state

## 7.4 `src/docwright/protocol/`

Files to add first:
- `events.py`
- `commands.py`
- `schemas.py`

Responsibilities:
- transport-neutral schemas
- no provider-specific payload weirdness in core model names

## 7.5 `src/docwright/adapters/`

Files to add first:
- `agent/base.py`
- `llm/base.py`
- `transport/headless.py`

Responsibilities:
- runtime integration glue
- do not let adapter details leak into core design

## 7.6 `src/docwright/capabilities/`

Files to add first:
- `guided_reading.py`

Responsibilities:
- task-mode selection
- ruleset selection
- tie together relevant skills/tool bundles

## 7.7 `src/docwright/skills/`

Files to add first:
- `highlighting.py`
- `warnings.py`
- `workspace_editing.py`

Responsibilities:
- reusable ability packages
- composable across capability profiles where possible

---

# 8. Minimal runtime API target

The minimal target should resemble:

```python
session = RuntimeSession(document=document_handle, permissions=permissions)
node = session.current_node()
node.highlight(level="important", reason="...")
node.warning(...)
ws = node.open_workspace(task="annotation", capability="summary_note")
ws.read_body()
ws.write_body("...")
ws.compile()
ws.submit()
session.advance()
```

Even if the internal implementation differs, the semantics should stay close to this.

---

# 9. Workspace design rule

The old prototype's “annotation sandbox” should be generalized into a **workspace session**.

Why:
- annotation is only one type of controlled edit flow
- the runtime concept is broader than annotation
- this keeps Core reusable for more agent types later

The first supported task can still be:
- `task="annotation"`

But the abstraction should not be named as if annotation were the only future possibility.

---

# 10. Guardrail design rule

Guardrails belong in Core, not in prompts alone.

Examples of acceptable core-level guardrails:
- cannot advance before required locator action
- cannot open more than one workspace for a node step if the session forbids it
- cannot submit before compile success
- cannot compile after terminal submission state

Examples of policy that should remain outside Core:
- what counts as “important enough” to highlight
- when reading should stop
- how verbose a note should be
- whether to request research for this node

---

# 11. Testing strategy

We should favor tests that prove boundaries.

## Phase B tests
- session state transitions
- event emission correctness
- guardrail failures
- workspace lifecycle

## Phase C tests
- adapter can drive Core actions
- capability cannot bypass guardrails
- different adapter/capability combinations can share the same session/runtime API

## Phase D tests
- headless runner consumes protocol/events correctly
- adapter result is translated into core actions cleanly

---

# 12. Migration discipline

When copying code from the old prototype:
- do not bulk-copy directories blindly
- copy only after deciding whether a file is Core, Adapter, Capability, Skill, or future Document layer
- rename concepts while migrating if the old name encodes wrong architecture
- prefer small, verified transfers over large dumps

Good migration example:
- move compile error model into `workspace/models.py`
- rewrite imports and names to match Core architecture

Bad migration example:
- copy the entire old runtime tree and promise to clean later

---

# 13. Immediate next implementation tasks

The next coding work in this repo should be:

1. define minimal data models for:
   - runtime events
   - workspace states
   - compile errors/results
   - locator actions
2. define abstract interfaces for:
   - document handle / page handle / node handle
   - runtime session
   - agent adapter
   - capability profile
3. add a tiny in-memory fake document implementation for tests
4. implement workspace state machine with compile/submit guardrails
5. implement runtime guardrails around highlight/open_workspace/advance
6. then attach the first guided-reading capability

---

# 14. Exit condition for v1 skeleton

This repo reaches a valid first milestone when:
- the architecture docs are sufficient to continue after context compression
- the package layout clearly reflects Core vs Adapter vs Capability vs Skill separation
- the first runtime/session/workspace interfaces compile and test
- the first guided-reading capability can be added without changing Core's conceptual boundary

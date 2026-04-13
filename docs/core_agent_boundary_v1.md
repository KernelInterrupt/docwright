# Core vs Agent Boundary v1

## Principle

**DocWright Core is a document runtime.**

It exposes stable objects, sessions, events, and guardrails.
It does **not** decide reading strategy by itself.

What sits after Core is not just “one agent profile”.
DocWright should support:
- multiple external agent runtimes
- multiple capability profiles
- multiple reusable skill/tool bundles

---

## Core owns

### 1. Document runtime API
Examples:
- `document.select_*()`
- `page.*`
- `node.*`
- `node_ref.highlight()`
- `node_ref.warning()`
- `locator.first()`

### 2. Workspace sessions
This is the generalized form of the old annotation sandbox.

Core should expose something like:
- `node_ref.open_workspace(task="annotation", capability="summary_note")`
- `workspace.read_body()`
- `workspace.write_body()`
- `workspace.patch_body()`
- `workspace.compile()`
- `workspace.get_compile_errors()`
- `workspace.submit()`

### 3. Runtime state and guardrails
Core owns:
- explicit node-ref resolution and guardrails around node-level actions
- session lifecycle
- permission checks
- event emission
- tool-call guardrails
- compile / submit lifecycle enforcement

### 4. Protocol surfaces
Core defines:
- commands
- events
- tool schemas
- run/session payloads
- headless/frontend transport contracts

---

## What comes after Core

### 1. Agent adapters
Responsible for integrating external runtimes such as:
- Codex
- OpenClaw
- custom tool-calling runtimes

They translate runtime-specific behavior into DocWright Core calls.

### 2. Capability profiles
Responsible for choosing task mode / policy surface, such as:
- guided reading
- paper review
- manual task execution
- annotation only

### 3. Skill / tool bundles
Responsible for exposing reusable ability packages, such as:
- highlighting
- warnings
- workspace editing
- research requests

---

## Design rule

If a capability should be reusable across multiple agent runtimes, it belongs in Core or a reusable skill/tool bundle.

If a capability is about integrating a specific outside agent ecosystem, it belongs in an agent adapter.

If a capability is about selecting a task mode or ruleset, it belongs in a capability profile.

---

## Anti-patterns to avoid

### Wrong: Core hardcodes guided-reading policy
Examples:
- every paragraph must be interpreted as a sequential reading step forever
- annotation types are hardcoded business logic rather than workspace capabilities
- advice/warning/highlight sequencing is fused into one built-in agent loop

### Wrong: Agent runtime owns Core mechanics
Examples:
- parsing IR directly instead of using handles
- manually editing workspace files outside workspace contracts
- bypassing compile error reporting / submit lifecycle

### Wrong: capability profile is mistaken for runtime integration
Examples:
- treating Codex itself as a “profile” rather than an adapter
- mixing tool bundle selection with runtime transport logic

---

## Immediate implication for migration

The old “annotation sandbox” should be reframed as a **workspace session subsystem** inside Core.

The old “guided reading pipeline” should be reframed as:
- one capability profile (`guided_reading`)
- using reusable tool bundles
- hosted through any compatible agent adapter

Legacy note:
- the current implementation still carries `current_node` / `advance` vocabulary
- that vocabulary should not define future public runtime APIs
- the migration target is recorded in `docs/node_ref_locator_migration_v1.md`

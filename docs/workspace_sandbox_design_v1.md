# Workspace / Sandbox Design v1

This document clarifies the relationship between **workspace sessions** and
**sandbox execution** in DocWright Core.

It exists because the current repository already has a `WorkspaceSession`
abstraction, while the original product idea started from an
annotation-specific sandbox.

The key conclusion is:

> `workspace` and `sandbox` are related, but they are not the same layer.

---

## 1. Design goals

DocWright should support annotation-oriented controlled editing without:
- exposing raw IR mutation as the main path
- binding Core to one host runtime's sandbox implementation
- collapsing logical editing state and process isolation into one abstraction

The architecture should preserve the existing layer boundaries:
- Core
- Agent Adapter
- Capability Profile
- Skill / Tool Bundle
- Workspace Session

---

## 2. What a workspace session is

A `WorkspaceSession` is a **logical controlled editing session**.

It owns:
- workspace lifecycle state
- editable body content
- editable-region rules
- compile / submit semantics
- history / audit events

It does **not** by itself imply:
- a real isolated filesystem
- a process sandbox
- unrestricted shell execution
- direct document IR mutation

For the current product direction, a workspace should be understood as:

> an annotation-first LaTeX work document with a locked template shell and a
> writable body region

That means the intended semantics are:
- template shell contains fixed structure such as `\usepackage` and `\begin{document}`
- the model edits only the allowed body region
- compile validates or renders the full assembled document

Current implementation note:
- today's baseline implementation is still simpler than this target and often
  seeds the editable body from node text
- that is a temporary baseline, not the ideal long-term semantic contract

---

## 3. What a sandbox is

A sandbox is an **execution isolation backend**.

It should own concerns such as:
- command execution
- filesystem isolation
- timeouts
- memory / CPU limits
- network policy
- artifact collection
- backend-specific failure reporting

Examples:
- local subprocess sandbox
- host-provided sandbox from a runtime like Codex
- container-backed sandbox

This belongs below or beside workspace compilation, not inside the workspace
state model itself.

---

## 4. The boundary: workspace != sandbox

The clean split should be:

### WorkspaceSession
Owns:
- what the agent is allowed to edit
- current editable content
- whether compile/submit is valid
- audit history

### WorkspaceCompiler
Owns:
- how editable content is assembled into a compile target
- how validation/rendering is requested
- how structured compile results are produced

### SandboxBackend
Owns:
- where and how commands actually execute
- isolation policy
- artifact paths / output capture

Recommended conceptual flow:

```text
WorkspaceSession
  -> WorkspaceCompiler
  -> SandboxBackend
  -> compile result / artifacts
```

---

## 5. Current policy decisions

### 5.1 No direct IR mutation

Current DocWright should **not** treat workspace editing as document IR editing.

The main path is:
- load IR into the runtime
- navigate document state through runtime APIs
- optionally derive a controlled annotation workspace from the current node
- submit an annotation artifact or related output

If IR mutation is ever added later, it should be a separate contract with:
- explicit patch semantics
- stronger guardrails
- auditability
- capability gating

### 5.2 No Core dependency on one host sandbox

DocWright should **not** directly borrow Codex internals into Core.

If a host runtime offers a sandbox, it should be integrated through an adapter
or backend contract, not by making Core depend on that host.

### 5.3 No mandatory LaTeX engine in the Core package

DocWright Core should not hard-require a system LaTeX toolchain.

Instead:
- keep `WorkspaceCompiler` as the abstraction boundary
- add optional LaTeX compiler backends
- make heavyweight compilation support opt-in

Possible delivery shapes:
- `pip install docwright[latex]`
- or a separate package such as `docwright-latex`

---

## 6. Recommended future contracts

The next sandbox-completion step should introduce explicit backend contracts,
for example:

- `SandboxBackend`
- `SandboxLease`
- `SandboxPolicy`
- `SandboxRunResult`
- `ArtifactRef`

Suggested backend implementations:

### A. `LocalProcessSandboxBackend`
For local development and deterministic tests.

### B. `HostProvidedSandboxBackend`
For external runtimes that already provide an isolated execution environment.

Core should only know the abstract backend contract, not host-specific details.

---

## 7. Capability exposure guidance

Current repository capabilities are:
- `guided_reading`
- `manual_task`

Both currently expose workspace tools, but this should be treated cautiously.

The intended rule is:
- expose workspace tools only when the task truly needs controlled editing
- avoid teaching pure-reading agents that "workspace is always available and normal"

This is mainly a capability/tool-surface issue, not a reason to remove the
workspace abstraction from Core.

---

## 8. Immediate repo follow-ups

Highest-value follow-ups:

1. Make workspace semantics explicitly annotation-first in docs and APIs
2. Improve contract metadata so tool readiness is visible before use
3. Introduce optional compiler readiness / backend metadata
4. Add sandbox backend interfaces without polluting Core runtime state
5. Later, add optional LaTeX compiler backend as an extension rather than a Core dependency

---

## 9. Final conclusion

DocWright should keep `WorkspaceSession`, but define it correctly:

- not as arbitrary text editing
- not as direct IR mutation
- not as a full sandbox by itself

Instead, it should be:

> a controlled annotation-first editing session that can later be backed by a
> separate sandbox execution layer.

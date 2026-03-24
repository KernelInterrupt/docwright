# Codex Adapter Design v1

This document defines the **Codex-compatible `CodexAdapter` bridge** for
DocWright Core.

The key design decision is:

- **Codex calls DocWright tools**
- **DocWright does not own the Codex model loop**

So this adapter is closer to a Playwright-style tool/runtime surface than to an
OpenAI SDK client.

---

## 1. Intended integration shape

The direct stack is:

```text
Codex host / Codex CLI / Codex runtime
    <-> CodexAdapter bridge
    <-> DocWright Core runtime/session/workspace
```

not:

```text
DocWright -> OpenAI Responses API -> Codex model
```

MCP is optional later, but it is not the first target.

---

## 2. What the adapter must provide

### `src/docwright/adapters/agent/codex_types.py`
Shared transport-neutral bridge models for:
- tool schemas
- tool calls
- tool results
- exported step contract
- optional in-process driver harnesses used only for smoke tests/local runners

### `src/docwright/adapters/agent/codex_prompting.py`
Builds Codex-facing guidance from:
- capability profile
- guardrail summary
- skill/tool summary
- current runtime step
- optional `AGENTS.md`

### `src/docwright/adapters/agent/codex_tools.py`
Maps DocWright skill bundles and Core actions into Codex-callable tool schemas,
including skill-provided tool descriptions, and executes tool calls against Core.

### `src/docwright/adapters/agent/codex.py`
Owns the bridge surface:
- export the current step contract
- expose tool execution helpers
- record Codex-side output as adapter events
- emit observer hooks for streaming/runtime lifecycle integration
- optionally run an in-process test harness without hard-coding any provider SDK

### `src/docwright/adapters/transport/runtime_host.py`
Provides a thin direct-library helper for Codex hosts that want a Playwright-like
object surface around one live runtime session, including usage snapshots.

---

## 3. Adapter responsibilities

The adapter owns:
- Codex-facing tool schemas
- step-scoped runtime guidance export
- capability/skill filtering of available tools
- translation from Codex-originated tool calls into Core actions
- adapter-local observability events
- optional generic turn-driver loop for tests and local harnesses
- bridge observer hooks for streaming/output and runtime lifecycle notifications
- usage counters and structured trace records for diagnostics
- adapter-local usage counters and structured trace sinks

The adapter does **not** own:
- runtime session state
- guardrail policy semantics
- workspace lifecycle rules
- document parsing/ingestion
- Codex provider SDK policy
- model selection defaults for any specific API provider

---

## 4. Tool surface

The bridge exposes DocWright actions as Codex-callable tools.

### Runtime tools
- `current_node`
- `get_context`
- `highlight`
- `warning`
- `open_workspace`
- `advance`

### Workspace tools
- `read_body`
- `write_body`
- `patch_body`
- `compile`
- `get_compile_errors`
- `submit`

These come from the active `CapabilityProfile` and its `SkillBundle`s where
possible. Core guardrails remain authoritative.

---

## 5. Guidance assembly rules

The adapter exports instructions from four layers:

1. **DocWright runtime identity**
   - use tools instead of guessing
   - obey runtime/workspace state

2. **Capability instructions**
   - capability descriptor
   - guardrail reminders
   - optional external strategy text

3. **Skill summary**
   - active skill bundles
   - tools exposed by each bundle

4. **Optional `AGENTS.md` text**
   - supplemental repository guidance only
   - never the source of truth for runtime state or tool wiring

---

## 6. Primary bridge flow

For each runtime step, the normal integration flow is:

1. DocWright exports a `CodexRuntimeContract` for the current step.
2. A Codex host reads:
   - instructions
   - current-step prompt
   - available tool schemas
3. Codex decides which tool(s) to call.
4. The host sends tool calls back to `CodexAdapter`.
5. `CodexAdapter` executes them against DocWright Core.
6. Tool results are returned to Codex.
7. Core guardrails decide what is allowed; the adapter only forwards actions.

This keeps the model loop on the Codex side and the runtime rules on the
DocWright side.

---

## 7. Optional in-process harness

For tests and local smoke runs, the adapter may accept a small generic
`CodexTurnDriver` protocol.

That harness exists only to:
- run fake transcripts in tests
- exercise headless flows locally
- prove the bridge works end-to-end without a real Codex integration

It must remain:
- transport-neutral
- provider-neutral
- optional

It is **not** the main product integration contract.

---

## 8. What `AGENTS.md` is and is not

`AGENTS.md` may be loaded into the exported Codex guidance, but it is only:
- supplemental repository guidance
- useful for conventions and coding rules

It is **not**:
- a replacement for tool definitions
- a replacement for capability strategy text
- a replacement for runtime/workspace state
- a replacement for adapter bridge logic

---

## 9. MCP relation

MCP may be added later as another transport surface.

That would look like:

```text
Codex -> MCP surface -> CodexAdapter bridge -> DocWright Core
```

But the bridge should exist first, because the Core-facing contract is the real
abstraction we need to stabilize.

---

## 10. Near-term extension path

After the Codex-compatible bridge is stable, we can add:
- a thin Codex CLI integration example
- additional transcript fixtures for more complex workspace/error flows
- MCP exposure as an additional transport

A provider-specific OpenAI client wrapper, if ever added, should live as an
optional integration layer on top of this bridge rather than defining it.

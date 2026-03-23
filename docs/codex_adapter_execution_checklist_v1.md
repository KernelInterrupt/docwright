# Codex Adapter Execution Checklist v1

This checklist is the implementation order for the **Codex-compatible
`CodexAdapter` bridge**.

Rule:
- keep Codex integration on the adapter side
- keep Core guardrails and workspace rules authoritative
- do not turn the bridge into a provider-specific OpenAI client

## C1. Shared bridge types
- [x] add `src/docwright/adapters/agent/codex_types.py`
- [x] freeze transport-neutral tool/tool-result dataclasses
- [x] define exported step contract dataclasses
- [x] define optional in-process turn-driver protocol
- [x] add import/type tests

## C2. Codex-facing guidance assembly
- [x] add `src/docwright/adapters/agent/codex_prompting.py`
- [x] support capability descriptor + guardrail summary
- [x] support skill/tool summary rendering
- [x] support optional `AGENTS.md` loading
- [x] add guidance assembly tests

## C3. Tool registry
- [x] add `src/docwright/adapters/agent/codex_tools.py`
- [x] map active skill bundles to tool specs
- [x] implement runtime tool handlers
- [x] implement workspace tool handlers
- [x] add tool registry / handler tests

## C4. Bridge surface
- [x] add `src/docwright/adapters/agent/codex.py`
- [x] export current-step contract from runtime session state
- [x] expose tool-call execution helpers
- [x] record Codex-side output events into Core
- [x] add bridge contract/execution tests

## C5. Optional in-process harness
- [x] add transport-neutral turn-driver support for local smoke runs
- [x] keep the harness optional rather than required for integration
- [x] add fake-driver loop tests

## C6. Guided-reading smoke path
- [x] run `GuidedReadingCapability` through `CodexAdapter`
- [x] prove highlight-before-advance still enforced by Core
- [x] prove workspace lifecycle still enforced by Core
- [x] add end-to-end smoke tests with fake driver transcripts

## C7. Post-MVP hardening
- [x] direct-library host helper/example for Codex-style runtimes
- [x] richer skill-provided tool descriptions
- [x] transcript/export fixtures for external hosts
- [x] streaming/event hooks for external runtimes
- [x] usage logging / tracing hooks
- [ ] optional MCP exposure

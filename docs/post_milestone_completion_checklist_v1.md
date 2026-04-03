# Post-Milestone Completion Checklist v1

This checklist tracks the remaining **explicitly unfinished** work after the
current Core / navigation / workspace / Codex baseline.

Rules:
- complete one item at a time
- update this checklist immediately after finishing each item
- make one commit per completed checklist item
- keep Core / Adapter / Capability / Skill / Workspace boundaries clean
- prefer tightening boundaries and contracts over adding ad hoc convenience code

Scope:
- remaining Codex integration surface
- adapter/runtime boundary cleanup
- document-layer boundary clarification

---

## M1. Optional MCP exposure
- [ ] define a minimal MCP-facing export surface for the existing Codex/runtime contract
- [ ] keep MCP optional rather than making it the canonical integration path
- [ ] add tests/docs proving MCP exposure reuses existing adapter/runtime contracts instead of inventing a parallel Core path

## M2. Provider compatibility boundary
- [ ] define an adapter-local provider compatibility module/boundary for future Responses/OpenAI-style integrations
- [ ] keep provider-specific request/response shapes out of Core modules and transport-neutral bridge types
- [ ] add tests/docs proving the compatibility layer stays adapter-scoped

## M3. Local companion boundary
- [ ] define a host-local companion boundary outside the central runtime loop
- [ ] keep companion-style launch/runtime orchestration out of Core session logic
- [ ] add docs/tests proving the runtime can still be embedded without companion assumptions

## M4. Headless transport protocol alignment
- [ ] make headless transport return protocol-safe payloads/events instead of internal event objects
- [ ] keep adapter-driven execution unchanged while tightening transport output contracts
- [ ] update tests/docs to treat headless transport as protocol/event consumer

## M5. `docwright-document` boundary definition
- [ ] document which concrete ingestion / IR conversion responsibilities belong in `docwright-document`
- [ ] document which lightweight handle/loading helpers remain in `docwright`
- [ ] update package/docs to reflect the boundary without making Core import the external backend eagerly

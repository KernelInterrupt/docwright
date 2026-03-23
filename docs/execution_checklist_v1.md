# Execution Checklist v1

Follow `docs/implementation_master_plan_v1.md`.

Rule:
- complete one item at a time
- keep Core / Adapter / Capability / Skill boundaries clean
- do not import large prototype modules until the destination abstraction is clear

---

## R1. Architecture contracts
- [x] R1.1 create `src/docwright/core/models.py`
- [x] R1.2 create `src/docwright/workspace/models.py`
- [x] R1.3 create `src/docwright/protocol/events.py`
- [x] R1.4 create `src/docwright/document/interfaces.py`
- [x] R1.5 create `src/docwright/adapters/agent/base.py`
- [x] R1.6 create `src/docwright/capabilities/base.py`
- [x] R1.7 create `src/docwright/skills/base.py`
- [x] R1.8 add tests for basic model imports and type-level structure

## R2. Workspace subsystem
- [x] R2.1 implement workspace state enum / state model
- [x] R2.2 implement compile error/result models
- [x] R2.3 implement workspace session skeleton
- [x] R2.4 implement read/write/patch operations
- [x] R2.5 implement compile guardrails
- [x] R2.6 implement submit guardrails
- [x] R2.7 add tests for full workspace lifecycle

## R3. Core runtime skeleton
- [x] R3.1 implement runtime event envelope model
- [x] R3.2 implement permission/guardrail model
- [x] R3.3 implement runtime session skeleton
- [x] R3.4 implement current-node / advance state handling
- [x] R3.5 add guardrails for highlight-before-advance
- [x] R3.6 add guardrails for one-workspace-per-step policy
- [x] R3.7 add tests for runtime guardrail enforcement

## R4. Document-facing interfaces
- [x] R4.1 define `DocumentHandle` protocol/interface
- [x] R4.2 define `PageHandle` protocol/interface
- [x] R4.3 define `NodeHandle` protocol/interface
- [x] R4.4 add minimal in-memory fake document for tests
- [x] R4.5 add tests proving Core can use document interfaces without parser internals

## R5. Adapter / capability / skill hosting
- [x] R5.1 define `AgentAdapter` interface
- [x] R5.2 define `CapabilityProfile` interface
- [x] R5.3 define skill/tool bundle interfaces
- [x] R5.4 add `capabilities/guided_reading.py`
- [x] R5.5 keep guided-reading strategy text outside Core modules
- [x] R5.6 add tests proving adapters/capabilities consume Core rather than own Core state

## R6. Protocol / transport skeleton
- [x] R6.1 define command schemas
- [x] R6.2 define run/session event schemas
- [x] R6.3 add transport-neutral serialization helpers if needed
- [x] R6.4 add minimal headless runner scaffold
- [x] R6.5 add tests for protocol/event serialization

## R7. Old prototype migration mapping
- [x] R7.1 document which old modules map to new Core/Adapter/Capability/Skill modules
- [x] R7.2 migrate compile-related types first
- [x] R7.3 migrate workspace lifecycle logic second
- [x] R7.4 migrate runtime guardrails third
- [x] R7.5 migrate guided-reading capability logic last

## R8. First milestone definition
- [x] R8.1 headless smoke test exists in new repo
- [x] R8.2 workspace lifecycle passes end-to-end tests
- [x] R8.3 runtime guardrails pass tests
- [x] R8.4 one guided-reading capability runs through Core via an adapter boundary
- [x] R8.5 docs updated to reflect implemented state

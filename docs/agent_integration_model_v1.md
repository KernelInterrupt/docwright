# Agent Integration Model v1

DocWright Core should be able to sit behind **arbitrary agent runtimes**.

Examples:
- Codex-like runtimes
- OpenClaw-like runtimes
- custom tool-calling runtimes
- local scripted agents

Therefore, Core should not assume a single built-in agent loop.

---

## 1. Four-layer integration model

### 1.1 Core
Reusable runtime mechanics:
- document/session API
- workspace sessions
- events
- guardrails
- protocol objects

### 1.2 Agent Adapter
Bridges an external agent runtime to DocWright Core.

Responsibilities:
- expose tools/events in the shape expected by that runtime
- translate runtime messages/tool calls into Core actions
- handle multi-turn interaction, interrupts, and streaming peculiarities

Examples:
- `CodexAdapter`
- `OpenClawAdapter`
- `ResponsesToolAdapter`

Provider SDK compatibility details should remain one layer lower, inside
adapter-scoped provider helpers, rather than being pushed into Core or the
transport-neutral bridge dataclasses.

Host-local companion/launcher logic should remain separate again, inside
companion/orchestration helpers, rather than being folded into the runtime
session loop.

### 1.3 Capability Profile
Chooses which DocWright capabilities and rules are active for a task.

Examples:
- `guided_reading`
- `paper_review`
- `manual_task`
- `annotation_only`

A capability profile is not an agent runtime.
It is a configuration/policy surface for Core usage.

### 1.4 Skill / Tool Bundle
A reusable ability package exposed through Core.

Examples:
- document navigation
- highlighting
- warning emission
- workspace editing
- research requests

---

## 2. Why `AgentProfile` alone is too narrow

`AgentProfile` suggests a single built-in agent abstraction.
That is too restrictive because:
- different agent runtimes have different execution models
- Core should be reusable behind multiple ecosystems
- capability selection is different from runtime integration
- tool bundles are more granular than a single “profile” concept

---

## 3. Design rule

If the question is:
- “How does Codex/OpenClaw plug in?” -> **Agent Adapter**
- “What task mode are we enabling?” -> **Capability Profile**
- “What concrete abilities are exposed?” -> **Skill / Tool Bundle**

---

## 4. Immediate consequence for this repo

The repo should evolve toward:
- Core abstractions that are agent-runtime-agnostic
- adapter interfaces rather than a single built-in agent host
- capability/profile configs rather than agent-specific hardcoding
- reusable tool bundles rather than one monolithic guided-reading loop

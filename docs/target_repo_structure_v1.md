# Target Repo Structure v1

## Top-level goal

This repository should be the clean home of **DocWright Core**, not a dumping ground for every current prototype subsystem.

## Target layout

```text
docwright/
  README.md
  pyproject.toml
  docs/
    core_agent_boundary_v1.md
    agent_integration_model_v1.md
    migration_checklist_v1.md
    target_repo_structure_v1.md
  src/
    docwright/
      __init__.py
      core/
        session.py
        run_controller.py
        guardrails.py
        events.py
      document/
        interfaces.py
        selectors.py
        handles.py
      workspace/
        session.py
        compiler.py
        templates.py
      protocol/
        commands.py
        events.py
        schemas.py
      adapters/
        agent/
          base.py
          codex.py
          openclaw.py
        provider/
          base.py
        llm/
          base.py
        transport/
          headless.py
          http_api.py
      capabilities/
        guided_reading.py
        paper_review.py
        manual_task.py
      skills/
        highlighting.py
        warnings.py
        workspace_editing.py
        research.py
  tests/
    core/
    workspace/
    protocol/
    adapters/
    capabilities/
    skills/
```

## Notes on each area

### `document/`
This repo should initially contain only the **interfaces needed by Core**.
If `docwright-document` is split separately later, these may become imported abstractions rather than full implementations.

### `core/`
Contains runtime state, run/session control, and guardrails.
This is the heart of DocWright.

### `workspace/`
Generalized controlled-editing session support.
This replaces the narrow idea of an annotation-only sandbox.

### `adapters/agent/`
Contains runtime adapters for external agent ecosystems.
This is where “Codex can plug in” or “OpenClaw can plug in” should live.

### `adapters/provider/`
Contains provider/SDK compatibility shims for request/response formatting.
This is where future Responses/OpenAI-style payload adaptation should live.
It must not redefine Core contracts or replace transport-neutral adapter types.

### `capabilities/`
Contains task-mode policy surfaces.
These are not agent runtimes; they are Core-facing capability selections.

### `skills/`
Contains reusable tool bundles / ability packs.
These should be composable across capabilities where possible.

### `adapters/`
Only keep adapters needed to let Core talk to external runtimes and transports.
Do not let adapter details dominate the architecture.

## What should stay out initially

Avoid copying these wholesale from the prototype at first:
- experimental scripts
- heavy ingest backends
- Windows companion packaging details
- prototype-specific compatibility clutter
- legacy schema-first fallback layers unless needed for migration tests

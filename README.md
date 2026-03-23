# DocWright Core

DocWright is a Playwright-like runtime for guided document reading and controlled document actions.

It is **not** a chatbot and **not** a one-shot summarizer.

The current goal of this repository is to provide the standalone **DocWright Core** layer as an installable Python package:
- stable document-facing runtime API
- workspace/session API for controlled editing
- runtime guardrails and event model
- agent integration boundaries
- capability / skill composition points
- protocol surfaces for headless and frontend integration

## Why this repo exists

The older prototype repository proved the end-to-end path:

```text
PDF -> IR -> runtime -> guided reading agent -> highlights / annotations / advice
```

But that prototype also mixed together:
- document ingestion
- runtime handles
- guided reading policy
- annotation sandbox details
- provider glue
- local companion integration

This repository exists to separate those concerns cleanly.

## Intended layering

```text
docwright-document   -> document ingestion + IR + selectors
       |
       v
docwright-core       -> runtime, sessions, guardrails, events, tool API
       |
       v
agent adapters       -> codex, openclaw, custom runtimes, etc.
       |
       v
capability profiles  -> guided reading, review, manual task, teaching, etc.
       |
       v
skill/tool bundles   -> highlighting, workspace editing, research, warnings, ...
       |
       v
docwright-app        -> UI / frontend / intervention loop
```


## Install

For local development or Codex integration, install the package in editable mode:

```bash
pip install -e .
```

The package now targets Python 3.10+.

## What is implemented now

This repository now contains a **self-contained Core milestone** with:
- runtime sessions with current-node, context, warning/highlight, workspace-open, and advance actions
- action-capable runtime node views over document handles
- workspace sessions with read/write/patch/compile/submit lifecycle
- compile result/error contracts
- transport-neutral protocol commands, events, and serialization helpers
- document handle protocols plus in-memory test handles
- adapter / capability / skill interfaces
- reference skill bundles for navigation, highlighting, warnings, and workspace editing
- `guided_reading` and `manual_task` capability scaffolds
- externalized guided-reading strategy text
- minimal headless runner with single-step and run-until-complete execution
- smoke, integration, lifecycle, and serialization tests
- Codex-compatible bridge scaffold with guidance export, a skill-aware tool registry, fake-driver smoke tests, a direct-library host helper, external-host fixtures, observer hooks, and usage/trace hooks

## What this repo intentionally does not own

This repository does **not** aim to own:
- PDF/OCR/VLM ingestion pipelines
- parser-specific IR generation
- provider-specific integration sprawl
- frontend or API product layers
- large prompt/business-logic bundles inside Core modules

## Initial documents

- `docs/bootstrap_status_v1.md`
- `docs/core_agent_boundary_v1.md`
- `docs/agent_integration_model_v1.md`
- `docs/implementation_master_plan_v1.md`
- `docs/execution_checklist_v1.md`
- `docs/migration_checklist_v1.md`
- `docs/prototype_migration_mapping_v1.md`
- `docs/target_repo_structure_v1.md`
- `docs/pdf_ir_fixture_strategy_v1.md`
- `docs/document_ir_contract_v1.md`
- `docs/runtime_api_contract_v1.md`
- `docs/workspace_session_contract_v1.md`
- `docs/codex_adapter_design_v1.md`
- `docs/codex_adapter_execution_checklist_v1.md`
- `docs/codex_direct_library_integration_v1.md`
- `src/docwright/codex/entry.py`
- `src/docwright/codex/samples/attention_fixture.py`

## Working rule

When continuing work in this repo after context compression, always read these in order:

1. `docs/bootstrap_status_v1.md`
2. `docs/implementation_master_plan_v1.md`
3. `docs/execution_checklist_v1.md`
4. then continue from the next post-milestone gap

## Status

The R1-R8 execution checklist is complete. The repository is now a tested,
minimal working Core runtime baseline rather than a contracts-only scaffold.


## Codex package entry

After installation, the recommended entry surface is:

```python
from docwright.codex.entry import DocWrightCodexEntry
```

Optional packaged sample:

```python
from docwright.codex.samples.attention_fixture import build_attention_fixture_entry
```


## License

Apache License 2.0. See `LICENSE`.

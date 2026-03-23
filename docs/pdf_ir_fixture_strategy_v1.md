# PDF->IR Fixture Strategy v1

DocWright Core should not block on re-running the full PDF->IR pipeline during early runtime development.

Therefore the current strategy is:

1. run the existing PDF->IR pipeline in the older prototype repo
2. export stable `DocumentIR` JSON fixtures
3. place those fixtures inside this repo for runtime / workspace / adapter-capability testing

## Current fixture

The first committed fixture target is:

- `tests/fixtures/document_ir/attention_is_all_you_need.document_ir.json`

Its summary lives at:

- `tests/fixtures/document_ir/attention_is_all_you_need.document_ir.summary.json`

## Why this is useful

This lets DocWright Core development proceed without immediately importing:
- heavy PDF parsing backends
- local model bridge details
- Docling/Ollama runtime assumptions
- ingest-side experimental scripts

Core can instead focus on:
- document handle interfaces
- runtime sessions
- guardrails
- workspace lifecycle
- adapter boundaries
- capability/skill wiring

## Rule

Fixtures are **inputs to Core**, not proof that Core owns the PDF parser.

That boundary must stay clear.

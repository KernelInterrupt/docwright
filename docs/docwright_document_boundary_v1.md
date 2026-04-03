# `docwright-document` Boundary v1

This document defines the intended split between the lightweight
`docwright.document` surface that remains in this repository and the heavier
document-conversion package that may live in `docwright-document`.

The goal is to keep DocWright Core import-safe and runtime-focused while making
future extraction of ingest/IR work obvious rather than implicit.

---

## 1. What stays in `docwright`

The in-repo `docwright.document` package should keep only the pieces Core and
transport helpers need at runtime:

- stable document handle protocols used by `RuntimeSession`
- lightweight in-memory handle implementations for tests, fixtures, and demos
- minimal IR fixture loaders that convert an already-produced Core-facing IR
  payload into in-memory handles
- a lazy facade that checks for an optional document backend without importing
  it eagerly during `import docwright` or `import docwright.document`

These pieces are runtime-facing convenience helpers, not a full ingest stack.

## 2. What belongs in `docwright-document`

The external `docwright-document` package should own concrete document
conversion and enrichment work, including:

- source ingestion from PDF, OCR, VLM, HTML, or other raw formats
- parser-specific extraction pipelines
- IR normalization, cleanup, and repair passes
- selector-enrichment or relation-enrichment logic that depends on ingest-time
  document analysis
- backend-specific configuration, model selection, and conversion policy

In short: if the code is about producing or improving Document IR from source
documents, it belongs in `docwright-document`, not in Core.

## 3. Boundary rule for IR helpers

The local `ir_loader` stays only because it consumes an existing IR fixture and
adapts it into in-memory handles for tests and lightweight demos.

It must not grow into:

- a production ingest pipeline
- a parser wrapper
- an OCR/VLM orchestration layer
- a replacement for backend-owned IR normalization

If a new helper needs to inspect raw PDFs or make backend-specific conversion
choices, it should move to `docwright-document`.

## 4. Import and packaging rule

`docwright` should continue exposing a unified `docwright.document` namespace
for callers, but the heavy backend must remain optional.

That means:

- `import docwright` must remain safe without `docwright-document`
- `import docwright.document` must remain safe without `docwright-document`
- only an actual conversion call such as `document.ir_converter(...)` may load
  the external backend
- Core modules must not eagerly import backend-specific conversion code

## 5. Practical ownership checklist

Use this decision rule when adding document-related code:

- if Core needs it to traverse, inspect, or reference an already-loaded
  document, keep it in `docwright`
- if it exists to create, enrich, normalize, or repair IR from source
  documents, put it in `docwright-document`

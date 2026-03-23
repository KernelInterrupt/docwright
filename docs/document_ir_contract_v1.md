# Document IR Contract v1

This document defines the **minimum DocumentIR contract** expected by DocWright Core.

DocWright Core does **not** own PDF parsing quality.
It consumes a structured IR produced upstream.

Therefore this contract focuses on:
- what Core requires
- what can be missing or imperfect
- what must remain stable enough for runtime use

---

## 1. Principle

Core should depend on a document representation that is:
- stable
- addressable by ID
- ordered for reading
- rich enough for handle traversal

Core should **not** depend on:
- a specific parser backend
- a specific VLM/OCR stack
- perfect hierarchy extraction
- perfect caption/evidence linkage

---

## 2. Required top-level fields

A valid Core-facing IR must provide:

- `document_id`
- `root_id`
- `metadata`
- `nodes`
- `reading_order`

Optional but strongly preferred:
- `localized_evidence`
- `relations`
- `created_at`
- `ir_version`

---

## 3. Node requirements

Each runtime-visible node must have:
- stable `id`
- `kind`
- `order_index`
- `parent_id` or a clear root relationship

Depending on kind, it should also provide:

### Paragraph
- `text`

### Section
- `title`
- `level`

### Figure
- `caption` when available

### Table
- `caption` when available

### Equation
- `latex` or `text_repr` when available

---

## 4. Minimum node kinds

Core should be prepared to consume at least:
- `document`
- `section`
- `paragraph`
- `figure`
- `table`
- `equation`

The first useful runtime milestone can focus on:
- `paragraph`
- `section`
- `figure`
- `table`

---

## 5. Reading order contract

`reading_order` is the most important runtime-facing sequence.

Requirements:
- it must contain stable node IDs
- it should reflect the best available reading sequence
- it may exclude some non-primary nodes if that is how the ingest layer models them

Core assumptions:
- runtime stepping is based on `reading_order`
- node IDs in `reading_order` must resolve in `nodes`
- agent/session logic should tolerate imperfect chunking

---

## 6. Metadata contract

Minimum useful metadata:
- `source_kind`
- `page_count` if applicable

Preferred metadata:
- `title`
- `authors`
- `language`
- evidence/relation counts

Core should treat metadata as supportive context, not as the primary runtime substrate.

---

## 7. Localized evidence contract

Localized evidence is optional for the earliest Core flows, but strongly preferred.

Useful evidence fields:
- `id`
- `kind`
- `text`
- `page_no`
- `bbox`
- `reading_order`
- `provenance`

Core uses localized evidence for:
- visual/document anchoring
- figure/table nearby context
- warning/highlight grounding
- frontend locator display later

---

## 8. Relation contract

Relations are optional for the smallest runtime skeleton, but should be supported by the contract.

Useful relation fields:
- `relation_id`
- `kind`
- `source_id`
- `target_id`
- `score`
- `provenance`

Core should never assume every relation type is present.
It should instead:
- consume what is available
- degrade gracefully when relations are sparse or noisy

---

## 9. Imperfection policy

Core must tolerate IRs that are imperfect in ways such as:
- section hierarchy is incomplete
- paragraph chunks are too coarse
- metadata is missing
- figure/table relations are incomplete
- evidence matching is noisy

These are ingest-quality issues, not Core-failure conditions.

The only hard failures should be structural contract failures such as:
- missing node IDs referenced in reading order
- malformed node objects
- non-resolvable root/node relationships needed for runtime traversal

---

## 10. Fixture policy

Core development may use exported real-world IR fixtures.

Those fixtures should be treated as:
- runtime inputs
- contract examples
- robustness tests against imperfect ingest output

They should **not** be treated as evidence that Core owns or guarantees ingest quality.

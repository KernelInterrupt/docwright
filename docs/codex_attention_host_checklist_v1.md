# Codex Attention Host Checklist v1

This checklist hardens the **Playwright-like direct-library path** for DocWright.

Default rule:
- the official sample document is always **Attention Is All You Need**
- the canonical host path is always:
  - load a `DocumentHandle`
  - construct `DocWrightCodexEntry.from_document(...)`
  - call `export_step()`
  - execute structured tool calls
- external hosts should not treat raw IR JSON as the main interaction surface

---

## A1. Canonical host entry
- [x] keep `DocWrightCodexEntry.from_document(...)` as the primary host bootstrap path
- [x] keep the Attention fixture helper optional rather than making it the main contract
- [x] update README to present the canonical entry flow first
- [x] state explicitly that Attention is the default professional sample

## A2. Playwright-like Codex onboarding
- [x] add a short host-usage guide oriented around direct-library integration
- [x] document the exact host loop: `export_step()` -> tool call -> tool result -> `record_output(...)`
- [x] document the main operating rules for Codex:
  - [x] do not read raw IR directly
  - [x] follow tool schemas exactly
  - [x] use navigation tools before free-form reasoning
  - [x] use workspace tools through the controlled lifecycle only

## A3. Tool-surface hardening for lower error rate
- [x] tighten bridge instructions so the recommended call order is explicit
- [x] improve skill/tool descriptions for navigation and workspace operations
- [x] expose `read_source` on the workspace tool surface so hosts can inspect the assembled template safely
- [x] make workspace-oriented tool results more ergonomic by repeating `workspace_id` at the top level
- [x] refresh bridge/export regression tests for the tightened contract

## A4. Official Attention smoke / demo
- [x] add an official Attention-based smoke/demo module inside the installed package
- [x] make the demo use the canonical entry path rather than binding the main contract to a special bridge
- [x] exercise `current_node`, `get_context`, `search_text`, and `advance`
- [x] add an automated test for the official Attention smoke path

---

## Completion note

The resulting baseline is:
- **one official sample**: Attention Is All You Need
- **one canonical host entry**: `DocWrightCodexEntry.from_document(...)`
- **one recommended Codex mental model**: use DocWright like a direct library, not like a raw JSON blob

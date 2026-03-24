# Workspace Session Contract v1

This document defines the **workspace session** abstraction for DocWright Core.

This is the generalized replacement for the old annotation-specific sandbox idea.

A workspace session is a controlled editing environment derived from a document node.
It should remain general enough for future reuse, but its **first concrete design
target is annotation-oriented LaTeX editing**, not arbitrary raw-text mutation.

---

## 1. Purpose

A workspace session exists so an agent runtime can:
- read editable content
- modify only allowed regions
- compile or validate output
- inspect structured errors
- submit a finalized result

The first practical task is `annotation`.
In that flow, the workspace should behave like a controlled LaTeX work document:
- fixed template shell
- explicit editable body region
- compile against the full assembled document

The abstraction may support future tasks later, but current Core semantics should
stay aligned with this annotation-first model.

---

## 2. Core concepts

Minimum concepts:
- `workspace_id`
- `task`
- `capability` or task-mode hint
- `state`
- `editable_region`
- `template shell` or equivalent locked document structure
- `editable body`
- `compile_result`
- `history`

---

## 3. Minimum operations

A workspace session should support:

- `read_body()`
- `read_source()`
- `write_body(content)`
- `patch_body(old, new)`
- `compile()`
- `get_compile_errors()`
- `submit()`

Implemented current extension:
- `read_source()` returns the assembled locked-shell source view

Optional later:
- multi-file sessions
- non-LaTeX validators

---

## 4. State machine

Minimum useful states:
- `initialized`
- `editing`
- `compiled`
- `compile_failed`
- `submitted`

Allowed high-level flow:

```text
initialized
  -> editing
  -> compiled | compile_failed
  -> editing (repair)
  -> compiled
  -> submitted
```

Core should reject invalid transitions.

---

## 5. Edit boundary rule

The runtime may expose a full file representation, but the editable region must be explicit.

For the current annotation-oriented workflow:
- template shell is locked
- only body region is writable
- `read_body()` / `write_body()` / `patch_body()` operate on that editable body
- the model must not rewrite `\usepackage`, `\begin{document}`, template macros,
  or other protected structure

This prevents the model from rewriting package imports, template structure, or other protected content.

---

## 6. Compile contract

`compile()` should return a structured result, not just raw stdout.

For the annotation-first workflow, compile should conceptually:
1. take the current editable body
2. insert it into the locked template shell
3. compile/validate the assembled LaTeX document
4. return structured success or failure details

Minimum compile result fields:
- `ok`
- `rendered_content` or equivalent preview output
- `errors`
- `backend_name`

Each compile error should ideally include:
- `code`
- `message`
- `line`
- `snippet`
- `terminal` or recoverability hint if available

---

## 7. Submit contract

`submit()` should be allowed only when the workspace is in a valid finalizable state.

Typical rule:
- submit after successful compile

On submission, Core should emit a structured event and freeze the workspace from further mutation unless explicitly reopened by a future policy.

---

## 8. Event contract

Workspace actions should emit lifecycle events such as:
- `workspace.opened`
- `workspace.body_read`
- `workspace.body_written`
- `workspace.compile_started`
- `workspace.compiled`
- `workspace.compile_failed`
- `workspace.submitted`

These are Core events, not prompt-only traces.

---

## 9. Guardrail contract

Workspace guardrails should be enforced in code, not only described in prompts.

Examples:
- cannot submit before successful compile
- cannot compile after submission
- cannot patch outside the editable region
- cannot mutate locked template segments

---

## 10. Generalization rule

Even if the first supported task is annotation, the workspace abstraction should remain named in general terms.

Preferred framing:
- `workspace session`
- `controlled editing session`

Avoid framing it as if all future workspaces are permanently annotation-only.

At the same time, do not over-generalize the current implementation into
"arbitrary editable text buffer" semantics. Current Core should still treat
workspace sessions as annotation-first controlled document editing.

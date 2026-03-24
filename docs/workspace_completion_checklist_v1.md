# Workspace Completion Checklist v1

This checklist continues after the original R1-R8 milestone and focuses only on
making the workspace subsystem production-shaped without violating the existing
architecture boundaries.

Scope for this checklist:
- declarative workspace rules / profile completeness
- annotation-first LaTeX compiler loop
- sandbox backend completion

Rules:
- complete one item at a time
- update this checklist immediately after finishing each item
- keep Core / Adapter / Capability / Skill / Workspace boundaries clean
- do not turn workspace into direct IR mutation
- do not collapse workspace and sandbox into one abstraction

---

## W1. Declarative workspace rule completion
- [x] W1.1 make workspace templates executable as rule objects, not just metadata
- [x] W1.2 persist template shell + editable-region semantics in workspace session state
- [x] W1.3 enforce editable-region / locked-shell mutation rules in `WorkspaceSession`
- [x] W1.4 expose assembled-source and rule-readiness metadata for hosts/adapters
- [x] W1.5 add tests for template assembly, rule enforcement, and runtime integration

## W2. Annotation-first LaTeX compiler loop
- [x] W2.1 add concrete compiler profiles for annotation-first LaTeX workspaces
- [x] W2.2 assemble full LaTeX source from template shell + editable body before compile
- [x] W2.3 return structured compile diagnostics/artifacts from the compiler backend
- [x] W2.4 wire compiler readiness/details into workspace descriptions and tests
- [x] W2.5 add end-to-end tests for successful and failed LaTeX-oriented compile flows

## W3. Sandbox backend completion
- [x] W3.1 add transport-neutral sandbox contracts and local backend implementation
- [x] W3.2 run compiler commands through sandbox execution instead of direct host assumptions
- [x] W3.3 surface sandbox backend readiness/details through workspace/compiler metadata
- [x] W3.4 add tests for sandbox execution, artifact collection, and failure handling
- [x] W3.5 update bootstrap/readme/docs to reflect completed workspace architecture

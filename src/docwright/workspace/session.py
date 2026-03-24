"""Workspace session object."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from docwright.workspace.compiler import WorkspaceCompiler, describe_workspace_compiler
from docwright.workspace.models import CompileError, CompileResult, WorkspaceSessionModel, WorkspaceState
from docwright.workspace.templates import EditableRegionSpec


class WorkspaceGuardrailError(RuntimeError):
    """Raised when workspace lifecycle rules are violated."""


class WorkspaceSession:
    """Controlled editing session bound to a workspace model."""

    def __init__(self, model: WorkspaceSessionModel, *, compiler: WorkspaceCompiler | None = None):
        self._model = model
        self._compiler = compiler
        if not model.history:
            model.record("workspace.opened", workspace_id=model.workspace_id, task=model.task)

    @property
    def model(self) -> WorkspaceSessionModel:
        return self._model

    @property
    def workspace_id(self) -> str:
        return self._model.workspace_id

    @property
    def task(self) -> str:
        return self._model.task

    def get_compile_errors(self) -> tuple[CompileError, ...]:
        result = self._model.current_compile_result
        if result is None:
            return ()
        return result.errors

    def read_body(self) -> str:
        body = self._model.current_body
        self._model.record("workspace.body_read", size=len(body))
        return body

    def read_source(self) -> str:
        source = self.assemble_source()
        self._model.record("workspace.source_read", size=len(source))
        return source

    def assemble_source(self) -> str:
        template_source = self._model.template_source
        if template_source is None:
            return self._model.current_body
        region_spec = self._editable_region_spec()
        return region_spec.render(template_source, self._model.current_body)

    def write_body(self, content: str) -> None:
        self._ensure_mutable()
        self._validate_body(content)
        self._model.current_body = content
        self._model.current_compile_result = None
        self._model.set_state(WorkspaceState.EDITING)
        self._model.record("workspace.body_written", size=len(content))

    def patch_body(self, old: str, new: str) -> None:
        self._ensure_mutable()
        if not old:
            raise ValueError("patch target must be non-empty")
        if old not in self._model.current_body:
            raise ValueError("patch target not found in current body")

        updated_body = self._model.current_body.replace(old, new, 1)
        self._validate_body(updated_body)
        self._model.current_body = updated_body
        self._model.current_compile_result = None
        self._model.set_state(WorkspaceState.EDITING)
        self._model.record("workspace.body_patched", old=old, new=new)

    def compile(self) -> CompileResult:
        if self._compiler is None:
            raise WorkspaceGuardrailError("workspace compiler is not configured")
        if self._model.state is WorkspaceState.SUBMITTED:
            raise WorkspaceGuardrailError("cannot compile a submitted workspace")

        self._model.record("workspace.compile_started")
        result = self._compiler.compile(self._model)
        self._model.current_compile_result = result
        if result.ok:
            self._model.set_state(WorkspaceState.COMPILED)
            self._model.record("workspace.compiled", backend_name=result.backend_name)
        else:
            self._model.set_state(WorkspaceState.COMPILE_FAILED)
            self._model.record(
                "workspace.compile_failed",
                backend_name=result.backend_name,
                error_count=len(result.errors),
            )
        return result

    def submit(self) -> CompileResult:
        if self._model.state is WorkspaceState.SUBMITTED:
            raise WorkspaceGuardrailError("workspace has already been submitted")

        result = self._model.current_compile_result
        if self._model.compile_required_before_submit:
            if self._model.state is not WorkspaceState.COMPILED or result is None or not result.ok:
                raise WorkspaceGuardrailError("cannot submit before a successful compile")
        else:
            if result is not None and not result.ok:
                raise WorkspaceGuardrailError("cannot submit while the latest compile result is failing")

        self._model.set_state(WorkspaceState.SUBMITTED)
        self._model.submitted_at = datetime.now(timezone.utc)
        self._model.record("workspace.submitted")
        return result if result is not None else CompileResult(ok=True, backend_name="workspace.submit")

    def describe(self) -> dict[str, Any]:
        """Return a structured workspace summary for adapters and tooling."""

        compile_result = self._model.current_compile_result
        compiler_info = describe_workspace_compiler(self._compiler)
        return {
            "workspace_id": self.workspace_id,
            "task": self.task,
            "state": self._model.state.value,
            "body": self._model.current_body,
            "assembled_source": self.assemble_source(),
            "workspace_profile": self._model.workspace_profile,
            "template_id": self._model.template_id,
            "template_shell_present": self._model.template_source is not None,
            "body_kind": self._model.body_kind,
            "compiler_profile": self._model.compiler_profile,
            "sandbox_profile": self._model.sandbox_profile,
            "compile_required_before_submit": self._model.compile_required_before_submit,
            "patch_scope": self._model.patch_scope,
            "locked_sections": list(self._model.locked_sections),
            "summary": self._model.model_summary,
            "editable_region": {
                "name": self._model.editable_region.name,
                "mode": self._model.editable_region.mode,
                "start_marker": self._model.editable_region.start_marker,
                "end_marker": self._model.editable_region.end_marker,
            },
            "compile_ready": self._compiler is not None and self._model.state is not WorkspaceState.SUBMITTED,
            "compile_backend": None if compile_result is None else compile_result.backend_name,
            "compiler": compiler_info,
            "submit_ready": self._model.state is WorkspaceState.COMPILED and compile_result is not None and compile_result.ok,
        }

    def _editable_region_spec(self) -> EditableRegionSpec:
        return EditableRegionSpec(
            name=self._model.editable_region.name,
            mode=self._model.editable_region.mode,
            start_marker=self._model.editable_region.start_marker,
            end_marker=self._model.editable_region.end_marker,
        )

    def _validate_body(self, content: str) -> None:
        if self._model.template_source is None:
            return
        region = self._editable_region_spec()
        if region.mode == "marker_range":
            if region.start_marker and region.start_marker in content:
                raise WorkspaceGuardrailError("editable body cannot contain the workspace start marker")
            if region.end_marker and region.end_marker in content:
                raise WorkspaceGuardrailError("editable body cannot contain the workspace end marker")

    def _ensure_mutable(self) -> None:
        if self._model.state is WorkspaceState.SUBMITTED:
            raise WorkspaceGuardrailError("cannot mutate a submitted workspace")

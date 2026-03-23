"""Workspace session object."""

from __future__ import annotations

from datetime import datetime, timezone

from docwright.workspace.compiler import WorkspaceCompiler
from docwright.workspace.models import CompileError, CompileResult, WorkspaceSessionModel, WorkspaceState


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

    def write_body(self, content: str) -> None:
        self._ensure_mutable()
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

        self._model.current_body = self._model.current_body.replace(old, new, 1)
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
        if self._model.state is not WorkspaceState.COMPILED or result is None or not result.ok:
            raise WorkspaceGuardrailError("cannot submit before a successful compile")

        self._model.set_state(WorkspaceState.SUBMITTED)
        self._model.submitted_at = datetime.now(timezone.utc)
        self._model.record("workspace.submitted")
        return result

    def _ensure_mutable(self) -> None:
        if self._model.state is WorkspaceState.SUBMITTED:
            raise WorkspaceGuardrailError("cannot mutate a submitted workspace")

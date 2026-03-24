"""Tool definitions and handlers for the Codex-compatible bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from docwright.adapters.agent.codex_types import CodexToolCall, CodexToolResult, CodexToolSpec

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession
    from docwright.document.interfaces import TextSearchHit
    from docwright.workspace.models import CompileError, CompileResult
    from docwright.workspace.session import WorkspaceSession


@dataclass(slots=True)
class CodexToolRegistry:
    """Translate active DocWright skills into Codex-callable tools."""

    def tools_for(
        self,
        session: RuntimeSession,
        capability: CapabilityProfile | None,
    ) -> tuple[CodexToolSpec, ...]:
        if capability is None:
            tool_names = ("current_node", "get_context", "advance")
        else:
            tool_names = tuple(
                tool_name
                for skill in capability.skill_bundles()
                for tool_name in skill.tool_names()
            )

        unique_names = tuple(dict.fromkeys(tool_names))
        description_overrides = self._tool_description_overrides(capability)
        return tuple(self._tool_spec(name, description=description_overrides.get(name)) for name in unique_names)

    def execute_tool(
        self,
        *,
        session: RuntimeSession,
        capability: CapabilityProfile | None,
        call: CodexToolCall,
    ) -> CodexToolResult:
        handler = getattr(self, f"_handle_{call.name}", None)
        if handler is None:
            raise ValueError(f"Unsupported Codex tool: {call.name}")
        output = handler(session=session, capability=capability, arguments=call.arguments)
        return CodexToolResult(call_id=call.call_id, name=call.name, output=output)

    def _tool_spec(self, name: str, description: str | None = None) -> CodexToolSpec:
        spec_factory = getattr(self, f"_spec_{name}", None)
        if spec_factory is None:
            raise ValueError(f"No tool schema registered for: {name}")
        spec = spec_factory()
        if description is None:
            return spec
        return CodexToolSpec(name=spec.name, description=description, input_schema=spec.input_schema)

    def _tool_description_overrides(self, capability: CapabilityProfile | None) -> dict[str, str]:
        if capability is None:
            return {}

        descriptions: dict[str, str] = {}
        for skill in capability.skill_bundles():
            for tool_name, description in skill.tool_descriptions().items():
                descriptions.setdefault(tool_name, description)
        return descriptions

    def _spec_current_node(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="current_node",
            description="Return the current runtime-visible document node.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        )

    def _spec_get_context(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="get_context",
            description="Return nearby reading-order node IDs around the current node.",
            input_schema={
                "type": "object",
                "properties": {
                    "before": {"type": "integer", "minimum": 0, "default": 1},
                    "after": {"type": "integer", "minimum": 0, "default": 1},
                },
                "additionalProperties": False,
            },
        )

    def _spec_search_text(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="search_text",
            description="Search runtime-visible document text and return matching nodes.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "default": 10},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        )

    def _spec_highlight(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="highlight",
            description="Apply a highlight decision to the current node.",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["level"],
                "additionalProperties": False,
            },
        )

    def _spec_warning(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="warning",
            description="Raise a structured warning on the current node.",
            input_schema={
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "severity": {"type": "string"},
                    "message": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["kind", "severity", "message"],
                "additionalProperties": False,
            },
        )

    def _spec_open_workspace(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="open_workspace",
            description="Open a controlled workspace session for the current node.",
            input_schema={
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "capability": {"type": "string"},
                    "language": {"type": "string"},
                    "initial_body": {"type": "string"},
                    "workspace_profile": {"type": "string"},
                    "template_id": {"type": "string"},
                    "body_kind": {"type": "string"},
                    "compiler_profile": {"type": "string"},
                },
                "required": ["task"],
                "additionalProperties": False,
            },
        )

    def _spec_advance(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="advance",
            description="Advance the runtime session to the next node in reading order.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        )

    def _spec_describe_workspace(self) -> CodexToolSpec:
        return self._workspace_id_only_tool(
            name="describe_workspace",
            description="Return the workspace rules, readiness, and editable-region metadata.",
        )

    def _spec_read_body(self) -> CodexToolSpec:
        return self._workspace_id_only_tool(
            name="read_body",
            description="Read the editable body from an open workspace session.",
        )

    def _spec_compile(self) -> CodexToolSpec:
        return self._workspace_id_only_tool(
            name="compile",
            description="Compile the current workspace body and return structured results.",
        )

    def _spec_get_compile_errors(self) -> CodexToolSpec:
        return self._workspace_id_only_tool(
            name="get_compile_errors",
            description="Return the current compile errors for an open workspace.",
        )

    def _spec_submit(self) -> CodexToolSpec:
        return self._workspace_id_only_tool(
            name="submit",
            description="Submit a successfully compiled workspace session.",
        )

    def _spec_write_body(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="write_body",
            description="Replace the editable body in an open workspace session.",
            input_schema={
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["workspace_id", "content"],
                "additionalProperties": False,
            },
        )

    def _spec_patch_body(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="patch_body",
            description="Replace the first matching body segment in an open workspace session.",
            input_schema={
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["workspace_id", "old", "new"],
                "additionalProperties": False,
            },
        )

    def _workspace_id_only_tool(self, *, name: str, description: str) -> CodexToolSpec:
        return CodexToolSpec(
            name=name,
            description=description,
            input_schema={
                "type": "object",
                "properties": {"workspace_id": {"type": "string"}},
                "required": ["workspace_id"],
                "additionalProperties": False,
            },
        )

    def _handle_current_node(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        node = session.current_node()
        return {"node": None if node is None else self._serialize_node(node)}

    def _handle_get_context(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        context = session.get_context(
            before=int(arguments.get("before", 1)),
            after=int(arguments.get("after", 1)),
        )
        return {
            "focus_node_id": context.focus_node_id,
            "before_node_ids": list(context.before_node_ids),
            "after_node_ids": list(context.after_node_ids),
        }

    def _handle_search_text(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        hits = session.search_text(arguments["query"], limit=int(arguments.get("limit", 10)))
        return {
            "query": arguments["query"],
            "hits": [self._serialize_search_hit(hit) for hit in hits],
        }

    def _handle_highlight(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        event = session.record_highlight(level=arguments["level"], reason=arguments.get("reason"))
        return {"event": event.as_protocol_event().as_dict()}

    def _handle_warning(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        event = session.record_warning(
            kind=arguments["kind"],
            severity=arguments["severity"],
            message=arguments["message"],
            evidence=tuple(arguments.get("evidence", ())),
        )
        return {"event": event.as_protocol_event().as_dict()}

    def _handle_open_workspace(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.open_workspace(
            task=arguments["task"],
            capability=arguments.get("capability"),
            language=arguments.get("language"),
            initial_body=arguments.get("initial_body"),
            workspace_profile=arguments.get("workspace_profile"),
            template_id=arguments.get("template_id"),
            body_kind=arguments.get("body_kind"),
            compiler_profile=arguments.get("compiler_profile"),
        )
        return {"workspace": self._serialize_workspace(workspace)}

    def _handle_advance(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        node = session.advance()
        return {
            "status": session.model.status.value,
            "node": None if node is None else self._serialize_node(node),
        }

    def _handle_describe_workspace(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        return {"workspace": self._serialize_workspace(workspace)}

    def _handle_read_body(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        return {"workspace_id": workspace.workspace_id, "body": workspace.read_body()}

    def _handle_write_body(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        workspace.write_body(arguments["content"])
        return {"workspace": self._serialize_workspace(workspace)}

    def _handle_patch_body(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        workspace.patch_body(arguments["old"], arguments["new"])
        return {"workspace": self._serialize_workspace(workspace)}

    def _handle_compile(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        result = workspace.compile()
        return {"workspace": self._serialize_workspace(workspace), "compile_result": self._serialize_compile_result(result)}

    def _handle_get_compile_errors(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        return {
            "workspace_id": workspace.workspace_id,
            "errors": [self._serialize_compile_error(error) for error in workspace.get_compile_errors()],
        }

    def _handle_submit(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        result = workspace.submit()
        return {"workspace": self._serialize_workspace(workspace), "compile_result": self._serialize_compile_result(result)}

    def _serialize_node(self, node: Any) -> dict[str, Any]:
        text_getter = getattr(node, "text_content", None)
        relation_getter = getattr(node, "relations", None)
        return {
            "node_id": getattr(node, "node_id", None),
            "kind": getattr(node, "kind", None),
            "page_number": getattr(node, "page_number", None),
            "text": text_getter() if callable(text_getter) else None,
            "relations": [
                {
                    "relation_id": relation.relation_id,
                    "kind": relation.kind,
                    "target_id": relation.target_id,
                    "score": relation.score,
                }
                for relation in (tuple(relation_getter()) if callable(relation_getter) else ())
            ],
        }

    def _serialize_workspace(self, workspace: WorkspaceSession) -> dict[str, Any]:
        return workspace.describe()

    def _serialize_search_hit(self, hit: TextSearchHit) -> dict[str, Any]:
        return {
            "node_id": hit.node_id,
            "page_number": hit.page_number,
            "text_preview": hit.text_preview,
            "match_count": hit.match_count,
        }

    def _serialize_compile_result(self, result: CompileResult) -> dict[str, Any]:
        return {
            "ok": result.ok,
            "backend_name": result.backend_name,
            "rendered_content": result.rendered_content,
            "errors": [self._serialize_compile_error(error) for error in result.errors],
        }

    def _serialize_compile_error(self, error: CompileError) -> dict[str, Any]:
        return {
            "code": error.code,
            "message": error.message,
            "line": error.line,
            "snippet": error.snippet,
            "terminal": error.terminal,
        }

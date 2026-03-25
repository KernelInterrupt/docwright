"""Tool definitions and handlers for the Codex-compatible bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from docwright.adapters.agent.codex_types import CodexToolCall, CodexToolResult, CodexToolSpec

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession
    from docwright.document.interfaces import InternalLinkHit, NodeStructureSlice, TextSearchHit
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
            tool_names = (
                "current_node",
                "get_context",
                "search_text",
                "advance",
                "get_structure",
                "search_headings",
                "jump_to_node",
                "list_internal_links",
                "follow_internal_link",
            )
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

    def _spec_get_structure(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="get_structure",
            description="Return hierarchy metadata for the current node or an explicitly requested node.",
            input_schema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
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
                    "scope": {"type": "string", "enum": ["document", "current_subtree", "current_page"], "default": "document"},
                    "node_kinds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        )

    def _spec_search_headings(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="search_headings",
            description="Search heading/section nodes to locate the relevant structural area of the document.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "default": 10},
                    "scope": {"type": "string", "enum": ["document", "current_subtree", "current_page"], "default": "document"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        )

    def _spec_jump_to_node(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="jump_to_node",
            description="Move runtime focus to a target node or to the first focusable descendant of a structural node.",
            input_schema={
                "type": "object",
                "properties": {"node_id": {"type": "string"}},
                "required": ["node_id"],
                "additionalProperties": False,
            },
        )

    def _spec_list_internal_links(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="list_internal_links",
            description="List outgoing internal-link relations for the current node or an explicitly requested node.",
            input_schema={
                "type": "object",
                "properties": {"node_id": {"type": "string"}},
                "additionalProperties": False,
            },
        )

    def _spec_follow_internal_link(self) -> CodexToolSpec:
        return CodexToolSpec(
            name="follow_internal_link",
            description="Follow one internal-link relation and update runtime focus to its resolved target.",
            input_schema={
                "type": "object",
                "properties": {
                    "relation_id": {"type": "string"},
                    "node_id": {"type": "string"},
                },
                "required": ["relation_id"],
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

    def _spec_read_source(self) -> CodexToolSpec:
        return self._workspace_id_only_tool(
            name="read_source",
            description="Read the assembled workspace source, including the locked template shell.",
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

    def _handle_get_structure(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        structure = session.get_structure(node_id=arguments.get("node_id"))
        return {"structure": self._serialize_structure_slice(structure)}

    def _handle_search_text(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        hits = session.search_text(
            arguments["query"],
            limit=int(arguments.get("limit", 10)),
            scope=str(arguments.get("scope", "document")),
            node_kinds=tuple(arguments.get("node_kinds", ())) or None,
        )
        return {
            "query": arguments["query"],
            "scope": str(arguments.get("scope", "document")),
            "hits": [self._serialize_search_hit(hit) for hit in hits],
        }

    def _handle_search_headings(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        hits = session.search_headings(
            arguments["query"],
            limit=int(arguments.get("limit", 10)),
            scope=str(arguments.get("scope", "document")),
        )
        return {
            "query": arguments["query"],
            "scope": str(arguments.get("scope", "document")),
            "hits": [self._serialize_search_hit(hit) for hit in hits],
        }

    def _handle_jump_to_node(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        node = session.jump_to_node(arguments["node_id"])
        return {
            "status": session.model.status.value,
            "node": None if node is None else self._serialize_node(node),
        }

    def _handle_list_internal_links(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        hits = session.list_internal_links(node_id=arguments.get("node_id"))
        return {
            "node_id": arguments.get("node_id") or session.model.step.node_id,
            "links": [self._serialize_internal_link_hit(hit) for hit in hits],
        }

    def _handle_follow_internal_link(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        node = session.follow_internal_link(arguments["relation_id"], node_id=arguments.get("node_id"))
        return {
            "status": session.model.status.value,
            "node": None if node is None else self._serialize_node(node),
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
        return self._workspace_payload(workspace)

    def _handle_advance(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        node = session.advance()
        return {
            "status": session.model.status.value,
            "node": None if node is None else self._serialize_node(node),
        }

    def _handle_describe_workspace(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        return self._workspace_payload(workspace)

    def _handle_read_source(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        return {
            "workspace_id": workspace.workspace_id,
            "source": workspace.read_source(),
        }

    def _handle_read_body(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        return {"workspace_id": workspace.workspace_id, "body": workspace.read_body()}

    def _handle_write_body(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        workspace.write_body(arguments["content"])
        return self._workspace_payload(workspace)

    def _handle_patch_body(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        workspace.patch_body(arguments["old"], arguments["new"])
        return self._workspace_payload(workspace)

    def _handle_compile(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        result = workspace.compile()
        return self._workspace_payload(workspace, compile_result=self._serialize_compile_result(result))

    def _handle_get_compile_errors(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        return {
            "workspace_id": workspace.workspace_id,
            "errors": [self._serialize_compile_error(error) for error in workspace.get_compile_errors()],
        }

    def _handle_submit(self, *, session: RuntimeSession, capability: CapabilityProfile | None, arguments: dict[str, Any]) -> dict[str, Any]:
        workspace = session.workspace(arguments["workspace_id"])
        result = workspace.submit()
        return self._workspace_payload(workspace, compile_result=self._serialize_compile_result(result))

    def _serialize_node(self, node: Any) -> dict[str, Any]:
        text_getter = getattr(node, "text_content", None)
        relation_getter = getattr(node, "relations", None)
        return {
            "node_id": getattr(node, "node_id", None),
            "kind": getattr(node, "kind", None),
            "page_number": getattr(node, "page_number", None),
            "parent_node_id": getattr(node, "parent_node_id", None),
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

    def _serialize_structure_slice(self, structure: NodeStructureSlice) -> dict[str, Any]:
        return {
            "focus_node_id": structure.focus_node_id,
            "root_id": structure.root_id,
            "parent_node_id": structure.parent_node_id,
            "child_node_ids": list(structure.child_node_ids),
            "sibling_node_ids": list(structure.sibling_node_ids),
            "ancestry_node_ids": list(structure.ancestry_node_ids),
            "section_path_node_ids": list(structure.section_path_node_ids),
            "section_path_titles": list(structure.section_path_titles),
        }

    def _serialize_workspace(self, workspace: WorkspaceSession) -> dict[str, Any]:
        return workspace.describe()

    def _workspace_payload(self, workspace: WorkspaceSession, **extra: Any) -> dict[str, Any]:
        return {
            "workspace_id": workspace.workspace_id,
            "workspace": self._serialize_workspace(workspace),
            **extra,
        }

    def _serialize_search_hit(self, hit: TextSearchHit) -> dict[str, Any]:
        return {
            "node_id": hit.node_id,
            "node_kind": hit.node_kind,
            "page_number": hit.page_number,
            "text_preview": hit.text_preview,
            "match_count": hit.match_count,
            "section_path_node_ids": list(hit.section_path_node_ids),
            "section_path_titles": list(hit.section_path_titles),
            "scope": hit.scope,
            "score": hit.score,
        }

    def _serialize_internal_link_hit(self, hit: InternalLinkHit) -> dict[str, Any]:
        return {
            "relation_id": hit.relation_id,
            "source_node_id": hit.source_node_id,
            "target_node_id": hit.target_node_id,
            "target_kind": hit.target_kind,
            "target_page_number": hit.target_page_number,
            "target_text_preview": hit.target_text_preview,
            "score": hit.score,
        }

    def _serialize_compile_result(self, result: CompileResult) -> dict[str, Any]:
        return {
            "ok": result.ok,
            "backend_name": result.backend_name,
            "rendered_content": result.rendered_content,
            "assembled_source": result.assembled_source,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "artifacts": [
                {
                    "name": artifact.name,
                    "path": artifact.path,
                    "media_type": artifact.media_type,
                    "description": artifact.description,
                }
                for artifact in result.artifacts
            ],
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

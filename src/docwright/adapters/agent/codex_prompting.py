"""Guidance assembly helpers for the Codex-compatible bridge."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from docwright.document.interfaces import NodeContextSlice

if TYPE_CHECKING:
    from docwright.capabilities.base import CapabilityProfile
    from docwright.core.session import RuntimeSession


_GUIDED_READING_NAME = "guided_reading"


def load_agents_md(path: Path | None) -> str | None:
    """Load AGENTS.md text when explicitly configured.

    AGENTS.md is supplemental repository guidance. It does not replace runtime
    state, tool schemas, capability policy, or workspace lifecycle rules.
    """

    if path is None or not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip() or None


class CodexPromptAssembler:
    """Build Codex-facing guidance from Core state and capability boundaries."""

    def build_instructions(
        self,
        session: RuntimeSession,
        capability: CapabilityProfile | None,
        *,
        agents_md_text: str | None = None,
    ) -> str:
        parts = [
            "You are a Codex-side agent operating DocWright through tools.",
            "Use the provided tools to inspect runtime state and perform document actions.",
            "Do not invent document structure, workspace contents, or step state.",
            "Do not treat raw IR JSON as the main interaction surface; use exported runtime tools instead.",
            "Tool arguments must match the published schemas exactly and must not include extra keys.",
            "For reading, usually call current_node first, then get_context and/or search_text, then advance.",
            "For non-linear documents, inspect structure, search headings, jump intentionally, and follow preserved internal links instead of forcing sequential traversal.",
            "For workspace edits, use the controlled lifecycle: open_workspace -> describe_workspace -> read_source/read_body -> write_body/patch_body -> compile -> submit. Only use compile/submit when those tools are exported and the workspace reports readiness.",
        ]

        if capability is not None:
            parts.append(
                f"Active capability: {capability.descriptor.name} - {capability.descriptor.description}".strip()
            )
            parts.append(self._format_guardrail_policy(capability))
            parts.append(self._format_skill_summary(capability))
            strategy = self._load_capability_strategy(capability)
            if strategy is not None:
                parts.append("Capability strategy:\n" + strategy.strip())

        parts.append(
            f"Runtime identifiers: session={session.model.session_id}, run={session.model.run_id}."
        )

        if agents_md_text:
            parts.append("Repository AGENTS.md guidance:\n" + agents_md_text.strip())

        parts.append(
            "Work one DocWright step at a time. Prefer structured tool calls over free-form explanation."
        )
        return "\n\n".join(part for part in parts if part)

    def build_turn_prompt(self, session: RuntimeSession) -> str:
        node = session.current_node()
        context = session.get_context(before=1, after=1)
        if node is None:
            return "Runtime session has no current node. Inspect state with tools and finish the step."

        lines = [
            f"Run one DocWright step for session {session.model.session_id}.",
            f"Current node: {node.node_id} ({node.kind}) on page {node.page_number}.",
        ]
        text = node.text_content()
        if text:
            lines.append(f"Node text preview: {text[:400]}")
        lines.append(self._format_context_slice(context))
        return "\n".join(lines)

    def _format_guardrail_policy(self, capability: CapabilityProfile) -> str:
        policy = capability.guardrail_policy()
        rules = []
        if policy.require_highlight_before_advance:
            rules.append("highlight is required before advance")
        if policy.max_workspaces_per_step is not None:
            rules.append(f"max {policy.max_workspaces_per_step} workspace open per step")
        return "Guardrails: " + (", ".join(rules) if rules else "default runtime rules only")

    def _format_skill_summary(self, capability: CapabilityProfile) -> str:
        bundles = capability.skill_bundles()
        if not bundles:
            return "No skill bundles are active."
        rendered = [f"- {skill.descriptor.name}: {', '.join(skill.tool_names())}" for skill in bundles]
        return "Active skill bundles:\n" + "\n".join(rendered)

    def _load_capability_strategy(self, capability: CapabilityProfile) -> str | None:
        if capability.descriptor.name != _GUIDED_READING_NAME:
            return None
        from docwright.capabilities.guided_reading import load_guided_reading_strategy

        return load_guided_reading_strategy()

    def _format_context_slice(self, context: NodeContextSlice) -> str:
        before = ", ".join(context.before_node_ids) if context.before_node_ids else "<none>"
        after = ", ".join(context.after_node_ids) if context.after_node_ids else "<none>"
        return f"Local context -> before: {before}; after: {after}."

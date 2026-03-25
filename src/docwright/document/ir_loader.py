"""Minimal JSON Document IR loader for fixtures and lightweight demos.

This module intentionally provides only a small bridge from the stable
Core-facing Document IR contract into in-memory document handles. It is useful
for tests, demos, and optional launch helpers, but it is not a replacement for
real ingest pipelines.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from docwright.document.handles import InMemoryDocument, InMemoryNode
from docwright.document.interfaces import NodeRelationRef


def load_in_memory_document_from_ir_path(path: str | Path) -> InMemoryDocument:
    """Load a Core-usable in-memory document from a JSON Document IR file."""

    resolved = Path(path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return in_memory_document_from_ir(payload)


def in_memory_document_from_ir(payload: Mapping[str, Any]) -> InMemoryDocument:
    """Convert a minimal Core-facing Document IR payload into in-memory handles."""

    document_id = str(payload["document_id"])
    root_id = payload.get("root_id")
    nodes_payload = payload["nodes"]
    reading_order = tuple(payload["reading_order"])

    if not isinstance(nodes_payload, Mapping):
        raise TypeError("Document IR 'nodes' must be a mapping")

    missing = [node_id for node_id in reading_order if node_id not in nodes_payload]
    if missing:
        raise ValueError(f"reading_order references missing nodes: {missing}")

    relation_refs_by_source = _relation_refs_by_source(payload.get("relations", ()), set(nodes_payload))
    nodes = [
        _node_from_ir_node(node_id, node_payload, relation_refs_by_source.get(node_id, ()))
        for node_id, node_payload in nodes_payload.items()
        if node_id != root_id
    ]
    return InMemoryDocument.from_nodes(
        document_id=document_id,
        nodes=nodes,
        reading_order=reading_order,
        root_id=str(root_id) if isinstance(root_id, str) else None,
    )


def _node_from_ir_node(
    node_id: str,
    node_payload: Any,
    relation_refs: tuple[NodeRelationRef, ...],
) -> InMemoryNode:
    if not isinstance(node_payload, Mapping):
        raise TypeError(f"node '{node_id}' must be a mapping")

    return InMemoryNode(
        node_id=node_id,
        kind=str(node_payload.get("kind", "unknown")),
        page_number=_page_number(node_payload),
        text=_node_text(node_payload),
        parent_node_id=_parent_id(node_payload),
        relation_refs=relation_refs,
    )


def _page_number(node_payload: Mapping[str, Any]) -> int:
    provenance = node_payload.get("provenance")
    if isinstance(provenance, Mapping):
        page = provenance.get("pdf_page")
        if isinstance(page, int) and page > 0:
            return page
    return 1


def _parent_id(node_payload: Mapping[str, Any]) -> str | None:
    parent_id = node_payload.get("parent_id")
    if isinstance(parent_id, str) and parent_id:
        return parent_id
    return None


def _node_text(node_payload: Mapping[str, Any]) -> str | None:
    candidates = (
        node_payload.get("text"),
        node_payload.get("title"),
        node_payload.get("caption"),
        node_payload.get("latex"),
        node_payload.get("text_repr"),
    )
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _relation_refs_by_source(
    relations_payload: Any,
    node_ids: set[str],
) -> dict[str, tuple[NodeRelationRef, ...]]:
    refs: dict[str, list[NodeRelationRef]] = {}
    if not isinstance(relations_payload, list):
        return {}

    for relation in relations_payload:
        if not isinstance(relation, Mapping):
            continue
        source_id = relation.get("source_id")
        target_id = relation.get("target_id")
        if source_id not in node_ids or target_id not in node_ids:
            continue
        refs.setdefault(str(source_id), []).append(
            NodeRelationRef(
                relation_id=str(relation.get("relation_id", "")),
                kind=str(relation.get("kind", "unknown")),
                target_id=str(target_id),
                score=relation.get("score") if isinstance(relation.get("score"), (int, float)) else None,
            )
        )
    return {node_id: tuple(values) for node_id, values in refs.items()}

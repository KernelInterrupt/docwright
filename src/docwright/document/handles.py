"""In-memory document handles for tests and lightweight integrations."""

from __future__ import annotations

from dataclasses import dataclass, field

from docwright.document.interfaces import NodeContextSlice, NodeRelationRef


@dataclass(slots=True, frozen=True)
class InMemoryNode:
    """Minimal node handle backed by in-memory data."""

    node_id: str
    kind: str
    page_number: int = 1
    text: str | None = None
    relation_refs: tuple[NodeRelationRef, ...] = field(default_factory=tuple)

    def text_content(self) -> str | None:
        return self.text

    def relations(self) -> tuple[NodeRelationRef, ...]:
        return self.relation_refs


@dataclass(slots=True)
class InMemoryPage:
    """Minimal page handle backed by an in-memory document."""

    page_number: int
    _nodes: dict[str, InMemoryNode]
    node_ids: tuple[str, ...]

    def get_node(self, node_id: str) -> InMemoryNode:
        if node_id not in self.node_ids:
            raise KeyError(f"node '{node_id}' is not on page {self.page_number}")
        return self._nodes[node_id]


@dataclass(slots=True)
class InMemoryDocument:
    """Minimal document handle suitable for Core tests."""

    document_id: str
    nodes: dict[str, InMemoryNode]
    reading_order: tuple[str, ...]
    _page_index: dict[int, tuple[str, ...]]

    @classmethod
    def from_nodes(
        cls,
        *,
        document_id: str,
        nodes: list[InMemoryNode],
        reading_order: tuple[str, ...] | None = None,
    ) -> InMemoryDocument:
        node_map = {node.node_id: node for node in nodes}
        resolved_reading_order = reading_order or tuple(node.node_id for node in nodes)
        page_index: dict[int, list[str]] = {}
        for node in nodes:
            page_index.setdefault(node.page_number, []).append(node.node_id)
        return cls(
            document_id=document_id,
            nodes=node_map,
            reading_order=resolved_reading_order,
            _page_index={page: tuple(node_ids) for page, node_ids in page_index.items()},
        )

    def get_page(self, page_number: int) -> InMemoryPage:
        node_ids = self._page_index[page_number]
        return InMemoryPage(page_number=page_number, _nodes=self.nodes, node_ids=node_ids)

    def get_node(self, node_id: str) -> InMemoryNode:
        return self.nodes[node_id]

    def get_context(self, node_id: str, *, before: int = 1, after: int = 1) -> NodeContextSlice:
        index = self.reading_order.index(node_id)
        before_node_ids = self.reading_order[max(0, index - before) : index]
        after_node_ids = self.reading_order[index + 1 : index + 1 + after]
        return NodeContextSlice(
            focus_node_id=node_id,
            before_node_ids=tuple(before_node_ids),
            after_node_ids=tuple(after_node_ids),
        )
